# Copyright (c) 2004-2006 gocept gmbh & co. kg
# Some functions in this file are (c) Zope Corporation (tm)
# See also LICENSE-ZPL2_0.txt
# $Id$
""" Some common utilities.
"""

import cgi
import os
import urlparse
import urllib
import time
import random
import logging

import OFS.Application
import zope.schema
from Globals import InitializeClass
from App.Common import package_home
from ExtensionClass import Base
from ComputedAttribute import ComputedAttribute
from AccessControl import ClassSecurityInfo, SpecialUsers
from AccessControl.SecurityManagement import \
    getSecurityManager, newSecurityManager, setSecurityManager
from AccessControl.Role import gather_permissions
from AccessControl.Permission import Permission

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow import config
import Products.AlphaFlow.interfaces
from Products.AlphaFlow.TrustedExpression import getEngine

_www = os.path.join(os.path.dirname(__file__), 'www')
_dtmldir = os.path.join( package_home( globals() ), 'dtml' )


def getPermissionsOfRole(obj, role):
    permissions = obj.permissionsOfRole(role)
    permissions = [ perm['name'] for perm in permissions 
                                if perm['selected'] ]
    return permissions


def removePermissionsFromRoles(obj, roles, permissions):
    for role in roles:
        current_permissions = getPermissionsOfRole(obj, role)

        for permission in permissions:
            try:
                current_permissions.remove(permission)
            except ValueError:
                pass
        obj.manage_role(role, current_permissions)


def addPermissionsToRoles(obj, roles, permissions):
    for role in roles:
        current_permissions = getPermissionsOfRole(obj, role)
        for permission in permissions:
            if permission not in current_permissions:
                current_permissions.append(permission)
        obj.manage_role(role, current_permissions)


def getRolesOfPermission(obj, permission):
    roles = obj.rolesOfPermission(permission)
    roles = [ role['name'] for role in roles 
                                if role['selected'] ]
    return roles


def ac_inherited_permissions(ob, all=0):
    # Get all permissions not defined in ourself that are inherited
    # This will be a sequence of tuples with a name as the first item and
    # an empty tuple as the second.
    d = {}
    perms = getattr(ob, '__ac_permissions__', ())
    for p in perms: d[p[0]] = None
    r = gather_permissions(ob.__class__, [], d)
    if all:
        if hasattr(ob, '_subobject_permissions'):
            for p in ob._subobject_permissions():
                pname=p[0]
                if not d.has_key(pname):
                    d[pname]=1
                    r.append(p)
        r = list(perms) + r
    return r


def modifyRolesForPermission(ob, pname, roles, acquire):
    '''
    Modifies multiple role to permission mappings.

    If acquire is None: roles is a list to acquire, a tuple to not acquire.

    '''
    if acquire:
        roles = list(roles)
    else:
        roles = tuple(roles)

    # This mimics what AccessControl/Role.py does.
    data = ()
    for perm in ac_inherited_permissions(ob, 1):
        name, value = perm[:2]
        if name == pname:
            data = value
            break
    p = Permission(pname, data, ob)
    if p.getRoles() != roles:
        p.setRoles(roles)
        return 1
    return 0


def listMembersWithLocalRoles(context, roles=[]):
    """Return member ids that have one of the given local roles in the
    context.

    Attention: Global roles are not accounted for.

    If no roles are given then no members are returned.

    """
    # Find all users that have a local role on this object.
    local_members = set()
    roles = set(roles)

    acl = getattr(context, '__ac_local_roles__', None)
    if acl is not None:
        for username, user_roles in context.__ac_local_roles__.items():
            user_roles = set(user_roles)
            if roles.intersection(user_roles):
                local_members.add(username)

        # Because this is raw data, we have to expand groups manually...
        groupstool = getToolByName(context, "portal_groups")
        local_members = set(expandGroups(groupstool, local_members))

    # Recursion step: compute the users with local roles from the parent
    # object.
    # Note: We do the recursion at the end to save some CPU cycles by not
    # expanding the groups of the growing list of members over and over
    # again.
    parent = None
    if not isinstance(context, OFS.Application.Application):
        parent = context.getParentNode()

    if parent is not None:
        parent_members = listMembersWithLocalRoles(parent, roles)
    else:
        parent_members = set()
    # The final result is the merge set of the local and parent members.
    return parent_members.union(local_members)


def expandGroups(groupstool, usergrouplist):
    """expands groups in a list of user ids recursively"""
    newlist = []
    expanded = False
    for candidate in usergrouplist:
        group = groupstool.getGroupById(candidate)
        if group is not None:
            # It's a group, check transitive groups
            usersofgroup = group.getMemberIds()
            expanded = True
            newlist += usersofgroup
        else:
            newlist.append(candidate)   # It's a user
    if expanded:
        newlist = expandGroups(groupstool, newlist)

    return newlist


def listGroupsWithRoles(context, roles=[]):
    """return groups who have one of the given roles in context

    roles: if empty, no role restriction
    returns: sequence of group data objects
    """
    pm = getToolByName(context, 'portal_groups')
    groups = pm.listGroups()
    return _filter_memberdata(context, groups, roles)


def _filter_memberdata(context, members, roles):
    if roles:
        # make a dict for performance reasons (should avoid O(n**2))
        roles = dict([ (r, True) for r in roles ])
        filtered_members = []
        for member in members:
            member_roles = member.getRolesInContext(context)
            intersection = [ r for r in member_roles if r in roles ]
            if intersection:
                filtered_members.append(member)
    else:
        filtered_members = members
    return filtered_members


class DynamicLocalRoleSupport(Base):

    local_role_fake_class = None
    __ac_local_roles__storage = None

    def __ac_local_roles__method(self):
        if self.local_role_fake_class is None:
            raise NotImplementedError, """%r does not have a proper
                local_role_fake_class attribute""" % self.__class__
        local_roles = self.__ac_local_roles__storage
        if local_roles is None:
            local_roles = {}
            self.__ac_local_roles__storage = local_roles
        return self.local_role_fake_class(self, local_roles)

    __ac_local_roles__ = ComputedAttribute(__ac_local_roles__method, 1)


class LocalRoleFakeBase:
    """fakes a dictionary for local role support"""

    def __init__(self, context, local_roles):
        self._context = context
        self._original = local_roles
        self._processmanager = getToolByName(context, 'workflow_manager')

    def __getitem__(self, user):

        try:
            roles = self._get_rolecache_for_user(user)
        except KeyError:
            roles = []

        # We need to automatically blend in the Owner role,
        # as ObjectManager.py is a bit choicy about when to
        # add it. Actually you can't revoke the Owner role
        # from the Owner anymore ... but who cares.
        if user == self._get_owner():
            roles.append("Owner")

        try:
            roles.extend(self._original[user])
        except KeyError:
            if not roles:
                raise

        roles = list(set(roles))
        return roles

    def __len__(self):
        return len(self.keys())

    def _get_owner(self):
        owner = self._context.getOwnerTuple()
        if owner is None:
            return None
        return owner[1]

    def keys(self):
        dict_keys = self._original.keys()
        relevant_keys = self._get_users_with_cached_roles()

        owner = self._get_owner()
        if owner is not None:
            relevant_keys.append(owner)

        keys = list(set((dict_keys + relevant_keys)))
        return keys

    def items(self):
        for key in self.keys():
            yield (key, self[key])

    def values(self):
        for key, value in self.items():
            yield value

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def _get_rolecache_for_user(self, user): abstract

    def _get_users_with_cached_roles(self): abstract

    def __getattr__(self, name):
        return getattr(self._original, name)


def makeBoolFromUnicode(s):
    mapping = {
        'false': False,
        'no': False,
        'true': True,
        'yes': True,
    }
    try:
        i = int(s)
    except ValueError:
        pass
    else:
        return bool(i)
    lower = s.lower()
    b = mapping.get(lower)
    if b is None:
        raise ValueError, "Do not know how to convert %r to bool" % (s, )
    return b


def killWorkItemRecursively(wi, reason, ignore=[]):
    stack = [wi]
    while stack:
        wi = stack.pop()
        if wi in ignore:
            continue
        stack.extend(wi.getGeneratedWorkItems())
        if wi.state in ['active', 'failed']:
            Products.AlphaFlow.interfaces.ILifeCycleController(wi).terminate(
                reason + " (recursive termination)")


def flexSplit(string):
    string = string.replace(',', ' ')
    result = string.split(' ')
    result = [ x for x in result if x ] # filter out empty
    return result


def evaluateTales(expression, **context):
    "Evaluate the TALES-Expression as SuperUser"
    return evaluateTalesAs(expression, SpecialUsers.system, **context)

def evaluateTalesAs(expression, run_as, **context):
    "Evaluate the TALES-Expression a s a given user"
    expression_compiled = getEngine().compile(expression)
    tales_context = getTalesContext(**context)
    return runAs(run_as, tales_context.evaluate,
                 expression_compiled)


def getTalesContext(workitem=None, activity=None, instance=None, content=None,
                    process=None, portal=None):
    """Create the context for the expression evaluation.
    """

    if not instance and workitem:
        instance = workitem.getInstance()

    if not content and instance:
        content = instance.getContentObject()

    if not activity and workitem:
        activity = workitem.getActivity()

    if not process:
        if instance:
            process = instance.getProcess()
        elif activity:
            process = activity.acquireProcess()

    if process:
        object_name = process.object_name
        if not portal:
            portal = getToolByName(process, "portal_url").getPortalObject()
    else:
        object_name = "object"

    # Try to guess the request *really* hard
    for context in [instance, workitem, content, activity, process, portal]:
        if context is None:
            continue
        request = context.REQUEST
        break
    else:
        request = None

    pm = getToolByName(portal, "portal_membership")
    member = pm.getAuthenticatedMember()

    alphaflow = {
        'currentMember': member,
        'currentUser': member.getUser(),
        'systemUser': SpecialUsers.system,
    }

    engine = getEngine()
    variables = {'request': request,
                 'content': content,
                 object_name: content,
                 'here': content,
                 'workitem': workitem,
                 'portal': portal,
                 'activity': activity,
                 'member': member,
                 'alphaflow': alphaflow,
                 }

    context = engine.getContext(variables)
    return context


def urlAppendToQueryString(url, extension):
    """Append a query string to a URL (which may already have a query string).
    """
    schema, netloc, path, parameters, query, fragment = urlparse.urlparse(url)
    query = cgi.parse_qsl(query)
    extension = cgi.parse_qsl(extension)
    query = query + extension
    query = urllib.urlencode(query)
    return urlparse.urlunparse((schema, netloc, path, parameters, query, fragment))


def generateUniqueId(prefix=None):
    """generate unique id like plone does

        we do not care about readability, but about speed

        preifx: optional string, not containing whitespace or strange
                characters
    """ 
    now = time.time()
    if not prefix:
        prefix = 'Item'
    id = str(now) + str(random.randint(0, 100000))
    return prefix + '.' + id


class ContentObjectRetrieverBase:
    """stub for implementing IContentObjectRetriever"""

    security = ClassSecurityInfo()

    security.declareProtected(config.WORK_WITH_PROCESS,
                              'getContentObjectUIDBrain')
    def getContentObjectUIDBrain(self):
        """return brain from uid catalog for content object of self

        returns catalog brain or None
        """
        uid_catalog = getToolByName(self, 'uid_catalog')
        uid = self.getContentObjectUID()
        brain = None
        if uid is not None:
            brains = uid_catalog(UID=uid)
            if brains:
                brain = brains[0]
        return brain

    security.declareProtected(config.WORK_WITH_PROCESS, 'getUrl')
    def getUrl(self):
        """Returns the relevant url for this workitem."""
        brain = self.getContentObjectUIDBrain()
        if brain is None:
            return '#'
        # the getURL() method of those brains is broken, so we work around it
        portal = getToolByName(self, 'portal_url').getPortalObject()
        ob_path = brain.getPath()
        path = '%s/%s' % (portal.absolute_url(), ob_path)
        return path

    security.declareProtected(config.WORK_WITH_PROCESS, 'getContentObjectPath')
    def getContentObjectPath(self):
        brain = self.getContentObjectUIDBrain()
        if brain is None:
            return ''
        portal = getToolByName(self, 'portal_url').getPortalObject()
        ob_path = tuple(brain.getPath().split('/'))
        path = portal.getPhysicalPath() + ob_path
        return path


    security.declareProtected(config.WORK_WITH_PROCESS,
                              'getContentObjectPortalCatalogBrain')
    def getContentObjectPortalCatalogBrain(self):
        path = self.getContentObjectPath()
        brain = None
        if path is not None:
            path = '/'.join(path)
            catalog = getToolByName(self, 'portal_catalog')
            brains = catalog(path=path)
            if brains:
                brain = brains[0]
        return brain

InitializeClass(ContentObjectRetrieverBase)


from types import FunctionType, ClassType
from ExtensionClass import Base

class FieldMultiplexWrapper(object):
    """Multiplexer for field requests."""

    def __new__(cls, activity, model, field):
        attrs = dict(FieldMultiplexWrapper.__dict__)
        del attrs['__new__']
        mod_cls = ClassType('FieldMultiplexWrapperMod', (field.__class__, ),
                            attrs)
        return mod_cls(activity, model, field)

    def __init__(self, activity, model, field):
        self.activity = activity
        self.model = model
        self.field = field
        self.field_class  = field.__class__

    def copy(self):
        """Return a copy."""
        return self.field.copy()

    def __getattr__(self, name, default=None):
        # proxy all methods and attributes, in case of methods copy methods to
        # here and call those
        attr = getattr(self.field, name)
        if isinstance(attr, FunctionType):
            installmethod(attr, self, name)
            attr = getattr(self, name)
        return attr

    def __repr__(self):
        """Return string repr"""
        return "<MultiplexedField %s>" % repr(self.field)

    def Vocabulary(self, content_instance=None):
        return self.field_class.Vocabulary(self,
                                           content_instance=self.activity)

    # we don't have generated accessors on the instance (because we're
    # working around class generation), therefore we need to return our
    # own accessors and mutators: 

    def getAccessor(self, instance):
        return self.accessor

    def getEditAccessor(self, instance):
        return self.editaccessor

    def getMutator(self, instance):
        return self.mutator

    def editaccessor(self, *args, **kw):
        return self.accessor(*args, **kw)

    def accessor(self, *args, **kw):
        return self.field_class.get(self, self.model, **kw)

    def mutator(self, value, *args, **kw):
        self.field_class.set(self, self.model, value, **kw)


def installmethod(function, object, name = None):
    """Add a bound method to an instance

    If name is ommited it defaults to the name of the given function.
    """
    from types import ClassType, MethodType, InstanceType
    if name == None:
        name = function.func_name
    else:
        function = renamefunction(function, name)
    setattr(object, name, MethodType(function, object, object.__class__))


def renamefunction(function, name):
    """
    This function returns a function identical to the given one, but
    with the given name.
    """
    from types import FunctionType, CodeType

    c = function.func_code
    if c.co_name != name:
        # rename the code object.
        c = CodeType(c.co_argcount, c.co_nlocals, c.co_stacksize,
                     c.co_flags, c.co_code, c.co_consts,
                     c.co_names, c.co_varnames, c.co_filename,
                     name, c.co_firstlineno, c.co_lnotab)
    if function.func_defaults != None:
        return FunctionType(c, function.func_globals, name,
                            function.func_defaults)
    return FunctionType(c, function.func_globals, name)


def runAs(user, call, *args, **kw):
    """Switch security manager (safely) to a manager user and back"""
    old_security_manager = getSecurityManager()
    newSecurityManager(None, user)
    try:
        return call(*args, **kw)
    finally:
        setSecurityManager(old_security_manager)


def mailhostTestingModePatch():
    """Patch mailhost to prevent sending mails, save them in attribute 
    'outbox' (a list)"""
    def _send(self, mfrom, mto, messageText, debug=False):
        outbox = getattr(self, 'outbox', [])
        outbox.append(( mfrom, mto, messageText ))
        setattr(self, 'outbox', outbox)

    from Products.SecureMailHost.SecureMailHost import SecureMailBase
    SecureMailBase._send = _send


logger = logging.getLogger('AlphaFlow')


def validateFields(schema, obj, errors=None):
    if errors is None:
        errors = []
    for field in zope.schema.getFields(schema).values():
        value = field.get(obj)
        try:
            field.bind(obj).validate(value)
        except zope.schema.ValidationError, e:
            errors.append(
                (obj, "Field &quot;%s&quot;: %s" % (field.title, e.doc())))
    return errors


def log_validation_errors(obj, errors):
    setattr(obj, "validation_errors",
            ["%r %s" % (obj, msg) for obj, msg in errors])
