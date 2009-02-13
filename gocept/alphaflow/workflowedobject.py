# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Base workflowed object"""

import zope.interface
import Globals
from AccessControl import getSecurityManager, ClassSecurityInfo

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.Expression import Expression, createExprContext

from Products.AlphaFlow.interfaces import IAlphaFlowed, ILifeCycleController
from Products.AlphaFlow import config, utils


class AlphaFlowedLocalRoleFake(utils.LocalRoleFakeBase):

    def _get_rolecache_for_user(self, user):
        alf = self._processmanager
        content = self._context
        roles = alf.getDynamicRolesForContent(content, user)
        return roles

    def _get_users_with_cached_roles(self):
        return self._processmanager.listRelevantUsersForContent(self._context)


class AlphaFlowed(utils.DynamicLocalRoleSupport):
    """Mixin for 'AlphaFlowed' content"""

    zope.interface.implements(IAlphaFlowed)

    instance_id = None
    __at_defaults_set = False   # Flag for working against AT bug
    alf_old_instances = []      # XXX this is currently updated
                                # from outside when the instance completes
                                # i think we should signal the content
                                # object instead of doing this monolithically
    security = ClassSecurityInfo()

    local_role_fake_class = AlphaFlowedLocalRoleFake

    #########################
    # ZMI convenience methods

    security.declarePublic('isAlphaFlowable')
    def isAlphaFlowable(self):
        """Is this a AlphaFlow-Object?"""
        return True

    ############
    # Zope hooks

    security.declareProtected(config.MANAGE_WORKFLOW, 'manage_afterClone')
    def manage_afterClone(self, item):
        # we are copied, drop instance (but do not terminate)
        self.alf_clearInstances()

    def manage_afterAdd(self, item, container):
        super(AlphaFlowed, self).manage_afterAdd(item, container)
        # We need to initialize AT objects (and their defaults) earlier
        # than AT usually does. It seems to be OK to just call the
        # initialization multiple times.
        if hasattr(self, 'initializeArchetype'):
            self.initializeArchetype()

    def setDefaults(self):
        # As initializeArchetype() might be called multipled times, especially
        # after manage_afterAdd has run we need to avoid setting the defaults
        # of an AT multiple times.
        if self.__at_defaults_set:
            return
        super(AlphaFlowed, self).setDefaults()
        self.__at_defaults_set = True

    ###################
    # IWorkflowedObject

    security.declareProtected(config.INIT_PROCESS, "getSuitableProcesses")
    def getSuitableProcesses(self):
        """Returns a list of suitable processes."""
        # acquire expression text; if none can be found return all processes
        expr_text = getattr(self, 'alf_suitable_processes', None)
        if expr_text is None:
            pm = getToolByName(self, "workflow_manager")
            user = getSecurityManager().getUser()
            user_roles = set(user.getRolesInContext(self))
            processes = [p.current() for p in pm.processes.objectValues()]

            return [process.aq_parent for process in processes
                    if not process.roles
                    or user_roles.intersection(process.roles)]

        folder = self.getParentNode()
        portal = getToolByName(self, 'portal_url').getPortalObject()
        context = createExprContext(folder, portal, self)
        expr = Expression(expr_text)
        return expr(context)

    security.declarePublic('getWorkItemsForCurrentUser')
    def getWorkItemsForCurrentUser(self):
        """Returns a list of work items for this object."""
        workflow_catalog = getToolByName(self, "workflow_catalog")
        if not self.hasInstanceAssigned():
            return []

        instance = self.getInstance()
        if ILifeCycleController(instance).state == 'failed':
            return []
        user = getSecurityManager().getUser().getUserName()
        workitems = workflow_catalog(alphaflow_type="workitem",
                                     state="active",
                                     listRelevantUsers=user,
                                     getContentObjectUID=self.UID())
        wi = [ x.getObject() for x in workitems ]
        return wi

    security.declareProtected(config.INIT_PROCESS, "assignProcess")
    def assignProcess(self, process_version):
        """Assigns a new instance of the workflow with the given
           id to this object.
        """
        if self.hasInstanceAssigned():
            raise Exception("Object already has an instance assigned.")
        wftool = getToolByName(self, "workflow_manager")
        instance = wftool.initProcess(process_version, self)
        self.instance_id = instance.getId()

    security.declarePublic('hasInstanceAssigned')
    def hasInstanceAssigned(self):
        """Has this an instance assigned?"""
        if not bool(self.instance_id):
            return False
        try:
            instance = self.getInstance()
        except KeyError:
            return False
        if instance is None:
            return False
        return True

    security.declareProtected(config.WORK_WITH_PROCESS, "getInstance")
    def getInstance(self, wrapped=False):
        """Return the currently assigned process instance."""
        try:
            wftool = getToolByName(self, "workflow_manager")
        except AttributeError:
            return None

        try:
            inst = wftool.instances[self.instance_id]
        except KeyError:
            return None

        if wrapped:
            inst = inst.__of__(self)
        return inst

    security.declareProtected(config.WORK_WITH_PROCESS, "getAllInstances")
    def getAllInstances(self):
        """Return a list of all instances (completed or running)."""
        wftool = getToolByName(self, "workflow_manager")
        instances = []
        for old_inst in self.alf_old_instances:
            try:
                inst = wftool.instances[old_inst]
            except KeyError:
                continue
            if inst is not None:
                instances.append(inst)
        inst = self.getInstance()
        if inst is not None:
            instances.insert(0, inst)
        return instances

    security.declarePublic('getWorkItem')
    def getWorkItem(self, id):
        """Return the workitem with the given id from the currently to this
           content object attached process instance.
        """
        instance = self.getInstance()
        if instance is None:
            raise ValueError, "No instance attached"
        return self.getInstance().getWorkItem(id).__of__(self)

    security.declareProtected(config.MANAGE_WORKFLOW, 'alf_clearInstances')
    def alf_clearInstances(self):
        self.instance_id = None
        self.alf_old_instances = []

    # View support
    security.declarePublic('af_redirect_to_workitem_view')
    def af_redirect_to_workitem_view(self, message=''):
        request = self.REQUEST
        response = request.RESPONSE

        workitems = self.getWorkItemsForCurrentUser()

        if workitems:
            next_wi = workitems[0]
            action = next_wi.getActivity()
            message = "%s (Next work item: %s)" % (message, action.title_or_id())
            url = next_wi.getViewUrl()
        else:
            if not message:
                message = request.get('portal_status_message', '')

            # If the user doesn't have the `View` permission on the context object,
            # we redirect to the portal root.
            user = getSecurityManager().getUser()
            url = getToolByName(self, "portal_url")()
            if user.has_permission("View", self):
                url = '%s/view' % self.absolute_url()

        url = utils.urlAppendToQueryString(
            url, "portal_status_message=%s" % message.encode('utf-8'))
        return response.redirect(url)


Globals.InitializeClass(AlphaFlowed)


class AlfDetails:

    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, **kw):
        self.__dict__.update(kw)
