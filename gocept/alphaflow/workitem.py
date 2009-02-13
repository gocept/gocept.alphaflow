# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Work item base classes"""

import DateTime
import persistent.list
import zope.interface
import zope.component
from AccessControl import ClassSecurityInfo, getSecurityManager
from Globals import InitializeClass
import zope.app.annotation.interfaces
from ZPublisher.mapply import mapply

from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions
from Products.Archetypes import public as atapi

import Products.AlphaFlow.interfaces
from Products.AlphaFlow import config, utils
from Products.AlphaFlow.utils import \
        DynamicLocalRoleSupport, LocalRoleFakeBase, modifyRolesForPermission, \
        ContentObjectRetrieverBase
from Products.AlphaFlow.interfaces import \
    IWorkItem, IWorkItemFactory, IAlphaFlowed, IAutomaticWorkItem, \
    IActivity, IAssignableActivity, IAssignableWorkItem, IFieldGroup, \
    IWorkItemClass, ILifeCycleController, ILifeCycleEvent
from Products.AlphaFlow.lifecycle import LifeCycleObjectBase, CannotComplete


class WorkItemFactory(object):

    zope.component.adapts(IActivity)
    zope.interface.implements(IWorkItemFactory)

    class_suffix = 'Activity'

    def __init__(self, activity):
        self.activity = activity

    def __call__(self, source, content_object=None):
        """Instantiates work items for this activity.
        """
        w_id = utils.generateUniqueId('Workitem')
        class_name = self.activity.__class__.__name__
        assert class_name.endswith(self.class_suffix), \
            "Can only use default WorkItemFactory for classes with a name " \
            "that ends with '%s'." % self.class_suffix
        class_name = class_name.lower()[:-len(self.class_suffix)]

        wi_class = zope.component.getUtility(IWorkItemClass, name=class_name)
        wi = wi_class(w_id, self.activity.getId(), content_object)
        return [wi]


class WorkItemLocalRoleFake(LocalRoleFakeBase):
    """fakes a dictionary for local role support"""

    def _get_rolecache_for_user(self, user):
        alf = self._processmanager
        workitem = self._context
        roles = alf.getDynamicRolesForWorkItem(workitem, user)
        return roles

    def _get_users_with_cached_roles(self):
        return self._processmanager.listRelevantUsersForWorkItem(self._context)


def workflow_action(method):

    def action(self, *args, **kwargs):
        if self.state != "active":
            raise ValueError(
                "Can't perform an action on a work item that isn't active.")
        if self.REQUEST is None:
            kw = kwargs
        else:
            kw = self.REQUEST.form.copy()
            kw.update(kwargs)
        try:
            message = mapply(method, (self,) + args, kw)
        except CannotComplete:
            message = u'Could not complete.'
        self.notifyAssigneesChange()
        self._update_ui_after_action(message, self.REQUEST)

    action.__doc__ = method.__doc__
    return action


class BaseWorkItem(DynamicLocalRoleSupport,
                   ContentObjectRetrieverBase, LifeCycleObjectBase):

    zope.interface.implements(
        IWorkItem, zope.app.annotation.interfaces.IAttributeAnnotatable)

    alphaflow_type = "workitem"

    security = ClassSecurityInfo()

    global_allow = False
    content_object = None

    activity_type = ""
    activity_id = ""

    generated_by = None
    generated_workitems = ()

    completed_by = None

    log_name = "work item"
    log_children_name = "checkpoints"

    schema = LifeCycleObjectBase.schema.copy() + atapi.Schema((
        atapi.TextField("comment",
            widget=atapi.TextAreaWidget(
                description="Please enter any comments you "
                    "have for this work item.")
            ),
        atapi.StringField("action",
            vocabulary="getActionVocabulary",
            widget=atapi.SelectionWidget(label="Workflow action",
                description="Select an action to perform after saving this "
                    "form.")
            )
        ))

    schema["id"].widget.visible = \
    schema["title"].widget.visible = {
        'edit':'hidden',
        'view':'hidden'
        }
    schema["id"].write_permission = permissions.ManagePortal
    schema["title"].required = False
    schema["title"].write_permission = permissions.ManagePortal

    manage_options = \
        ({'label' : 'Overview', 'action' : 'manage_overview'},) + \
        LifeCycleObjectBase.manage_options

    local_role_fake_class = WorkItemLocalRoleFake
    _af_notified = True

    security.declareProtected(config.WORK_WITH_PROCESS, '__init__')
    def __init__(self, id, activity_id, content_object=None):
        BaseWorkItem.inheritedAttribute('__init__')(self, id)
        self.activity_id = activity_id
        self.content_object = content_object
        self.checkpoints_passed = persistent.list.PersistentList()

    def __repr__(self):
        try:
            state = ILifeCycleController(self).state
        except TypeError:
            state = 'n/a'
        return '<%s for %r (%s)>' % (self.__class__.__name__,
                                     self.activity_id, state)

    security.declarePrivate("getWorkItem")
    def getWorkItem(self):
        return self.aq_inner

    security.declarePublic('getCharset')
    def getCharset(self):
        """this is a skin method of archetypes returning the site encoding
        """
        return config.SITE_ENCODING

    security.declarePublic('reindexObject')
    def reindexObject(self, idxs=[]):
        """workitems are very explicitly indexed"""
        pass

    security.declarePrivate('reindexWorkitem')
    def reindexWorkitem(self):
        BaseWorkItem.inheritedAttribute('reindexObject')(self)

    security.declarePrivate("beforeCreationItems")
    def beforeCreationItems(self, items, parent):
        """Trigger that gets called before new work items get active.

           Other work items can veto on the creation of those items and
           return a list of ids as a veto.

           After all work items have been triggered, the vetoed work items
           get removed again and never become active.
        """
        return []

    #########################
    # ZMI convenience methods

    security.declareProtected(config.MANAGE_WORKFLOW, 'manage_userAction')
    def manage_userAction(self, actionId, REQUEST):
        """Performs an action defined by the activity."""
        action = self.getActionById(actionId)
        action()
        REQUEST.RESPONSE.redirect(self.absolute_url() + "/manage_overview",
                                  lock=True)

    # IWorkItem

    security.declareProtected(config.WORK_WITH_PROCESS, 'getActions')
    def getActions(self):
        "Return a list of actions the user may perform on this work item."
        return []

    security.declareProtected(config.WORK_WITH_PROCESS, 'getActionById')
    def getActionById(self, id):
        for action in self.getActions():
            if action.id == id:
                return action
        raise KeyError(id)

    security.declareProtected(config.WORK_WITH_PROCESS, 'getGeneratedWorkItems')
    def getGeneratedWorkItems(self): 
        inst = self.getInstance()
        wis = [inst[x] for x in self.generated_workitems]
        return wis

    security.declareProtected(config.WORK_WITH_PROCESS, 'isRelevant')
    def isRelevant(self, user):
        return user in self.listRelevantUsers()

    security.declareProtected(config.WORK_WITH_PROCESS, 'listRelevantUsers')
    def listRelevantUsers(self):
        return []

    security.declareProtected(config.WORK_WITH_PROCESS, 'isChildOf')
    def isChildOf(self, workitem_id=None, workitem=None):
        """Returns True if the given work item is a predecessor of this work 
        item (in regard to 'was generated by').

        You only may give either workitem_id or workitem.
        """
        if workitem_id is None:
            workitem_id = workitem.getId()

        if self.id == workitem_id:
            return False
        if self.generated_by == workitem_id:
            return True
        if self.generated_by == None:
            return False
        parent = self.getParent()
        if hasattr(parent, 'isChildOf'):
            return parent.isChildOf(workitem_id)
        return False

    security.declareProtected(config.WORK_WITH_PROCESS, 'getParent')
    def getParent(self):
        """Returns the parent WorkItem or None if this is a root workitem.
        """
        if self.generated_by is None:
            return None
        parent = self.getInstance()[self.generated_by]
        # XXX This is a work-around; generated_by should never contain
        # the id of an instance.
        if not IWorkItem.providedBy(parent):
            return None
        else:
            return parent

    security.declareProtected(config.WORK_WITH_PROCESS, 'getShortInfo')
    def getShortInfo(self):
        """Returns a short information text."""
        return "%s is in %s state" % (self.getId(),
                                      ILifeCycleController(self).state)

    security.declareProtected(config.WORK_WITH_PROCESS, 'getStatusInfo')
    def getStatusInfo(self):
        """Returns a short status information text."""
        return ("WorkItems current status: %s" %
                ILifeCycleController(self).state)

    def onStart(self):
        self.passCheckpoint(config.CHECKPOINT_START)

    def onCompletion(self):
        self.passCheckpoint(config.CHECKPOINT_COMPLETE)
        self.completed_by = getSecurityManager().getUser().getUserName()

    security.declarePublic("getActivity")   # XXX .... yurks
    def getActivity(self):
        activity = getattr(self, '_v_my_activity', None)
        if activity is None:
            process = self.getInstance().getProcess()
            if not hasattr(process, self.activity_id):
                ILifeCycleController(self).fail(
                    "Could not find activity definition `%s` for workitem." %
                    self.activity_id)
                raise AttributeError(self.activity_id)
            activity = getattr(process, self.activity_id)
            self._v_my_activity = activity
            activity = self._v_my_activity  # wrapping magic
        return activity

    security.declarePublic("getActivityTitleOrId")
    def getActivityTitleOrId(self):
        try:
            activity = self.getActivity()
        except AttributeError:
            title = 'n/a'
        else:
            title = activity.title_or_id()
        return title

    security.declareProtected(config.WORK_WITH_PROCESS, "getDetailStatus")
    def getDetailStatus(self):
        """Return a (single line) string that describes the current status a
        bit more verbose."""
        return ILifeCycleController(self).state

    security.declareProtected(config.WORK_WITH_PROCESS, 'getActionVocabulary')
    def getActionVocabulary(self):
        actions = [(action.id, action.title)
                   for action in self.getActions()
                   if action.enabled]
        # XXX This seems junk:
        actions.append(("", "No action"))
        return actions

    def absolute_url(self, inner=False):
       """A hackish way to use content objects as views.

           If this object is (directly) wrapped into an IAlphaFlowed,
           it will return the url of the IAlphaFlowed object"""
       absurl = BaseWorkItem.inheritedAttribute("absolute_url")
       if inner:
           return absurl(self)

       if not hasattr(self, 'aq_chain'):
           return absurl(self)

       if len(self.aq_chain) < 2:
           return absurl(self)

       if IAlphaFlowed.providedBy(self.aq_chain[1]):
           return self.aq_chain[1].absolute_url()

       return absurl(self)

    security.declareProtected(config.WORK_WITH_PROCESS,
                              "getActivityConfiguration")
    def getActivityConfiguration(self, field, default=None):
        """Retrieves the configuration for this activity in the context of
           this instance.
        """
        instance = self.getInstance()
        return instance.getActivityConfiguration(field, self.activity_id,
            default=default)

    security.declarePrivate("createWorkItems")
    def createWorkItems(self, activity_ids, content_object=None):
        """Creates a new workitem for the activity with the given name.

           Raises KeyError if any activity with the names is not known.
        """
        instance = self.getInstance()
        return instance.createWorkItems(activity_ids, self,
                                        content_object=content_object)

    security.declarePrivate("notifyWorkItemStateChange")
    def notifyWorkItemStateChange(self, workitem):
        """Receives a notification that the 
           work item <workitem> has changed it's state
        """
        pass

    security.declarePrivate("notifyAssigneesChange")
    def notifyAssigneesChange(self):
        """notifies the workitem that the assignees might have changed
        """
        alf = getToolByName(self, 'workflow_manager')
        alf.updateCacheByWorkItem(self)

    security.declarePrivate('passCheckpoint')
    def passCheckpoint(self, name):
        checkpoint = self.createChild(self.getActivity()[name])
        self.checkpoints_passed.append(name)
        ILifeCycleController(checkpoint).start("Started by work item.")
        return checkpoint.generated_workitems

    #########################
    # IContentObjectRetriever

    # Force acquisition of getContentObject by context instead of containment
    security.declareProtected(config.WORK_WITH_PROCESS, 'getContentObject')
    def getContentObject(self):
        if self.content_object is None:
            instance = self.getInstance()
            ob = instance.getContentObject()
        else:
            rc = getToolByName(self, "reference_catalog")
            ob = rc.lookupObject(self.content_object)
        return ob

    security.declareProtected(config.WORK_WITH_PROCESS, 'getContentObjectUID')
    def getContentObjectUID(self):
        if self.content_object is None:
            instance = self.getInstance()
            uid = instance.getContentObjectUID()
        else:
            uid = self.content_object
        return uid


@zope.component.adapter(BaseWorkItem,
                        zope.app.container.interfaces.IObjectAddedEvent)
def added_base_workitem(ob, event):
    modifyRolesForPermission(ob, permissions.ModifyPortalContent,
                             ['Assignee', 'Manager'],
                             acquire=True)
    ob.setTitle('Workitem')


InitializeClass(BaseWorkItem)


class BaseAssignableWorkItem(BaseWorkItem):
    """workitems which are assignable to users subclass this"""

    zope.interface.implements(IAssignableWorkItem)

    security = ClassSecurityInfo()

    @property
    def showInWorkList(self):
        return self.getActivity().showInWorkList

    security.declareProtected(config.WORK_WITH_PROCESS, "listRelevantUsers")
    def listRelevantUsers(self):
        if ILifeCycleController(self).state != "active":
            return []
        activity = self.getActivity()
        assert IAssignableActivity.providedBy(activity)
        if activity.assigneesKind == 'possible':
            relevant = self.getActivityConfiguration("assignees")
            if not isinstance(relevant, (list, tuple)):
                relevant = []
        else:
            if activity.assigneesExpression is not None:
                relevant = utils.evaluateTales(activity.assigneesExpression,
                                               workitem=self)
                groupstool = getToolByName(self, "portal_groups")
                relevant = utils.expandGroups(groupstool, relevant)
            elif activity.roles:
                # we have roles
                roles = activity.roles
                relevant = self.listMembersWithRolesOnContentObject(roles)
            else:
                # we have groups
                gt = getToolByName(self, 'portal_groups')
                relevant = utils.expandGroups(gt, activity.groups)
        return list(relevant)

    security.declareProtected(config.WORK_WITH_PROCESS, "Schema")
    def Schema(self):
        schema = self.schema.copy()
        try:
            activity = self.getActivity()
        except AttributeError:
            # Not yet in context or reference to activity is broken.
            # Ignore this.
            pass
        else:
            comment_field = schema['comment']
            comment_expr = activity.commentfield

            # just make sure that the commentfield is set to default
            # behavior
            #if comment_expr:
            #    widget = comment_field.widget
            #    widget.visible = {'edit': True, 'view': 1}
            if comment_expr == "hidden":
                widget = comment_field.widget
                widget.visible = {'edit': -1, 'view': -1}
                comment_field.required = False

            if comment_expr == "required":
                comment_field.required = True

        return schema


    security.declareProtected(config.WORK_WITH_PROCESS, "getGroupedSchema")
    def getGroupedSchema(self):
        """returns sequence of IFieldGroup instances

        Aggregates configuration schemas from all activities which are
        configured by this workitem + own schema and returns a 
        schema, grouped by activity
        
        Every group returned contains at least one field.
        """
        return [Group(self.getInstance(),
                      self.activity_id,
                      self.schema.fields())]

    security.declareProtected(config.WORK_WITH_PROCESS, 'getViewUrl')
    def getViewUrl(self):
        """return url to view appropriate the page to handle the workitem
        """
        try:
            activity = self.getActivity()
        except AttributeError:
            # The activity doesn't exist.
            return ''
        else:
            return utils.evaluateTales(activity.viewUrlExpression, workitem=self)

    security.declareProtected(config.WORK_WITH_PROCESS,
                              'listMembersWithRolesOnContentObject')
    def listMembersWithRolesOnContentObject(self, roles):
        """get members who have one of the given roles on the content object
        """
        contentObject = self.getContentObject()
        if contentObject is None:
            member_ids = []
        else:
            member_ids = utils.listMembersWithLocalRoles(contentObject, roles)
        return member_ids

    security.declarePrivate('_update_ui_after_action')
    def _update_ui_after_action(self, default_message, REQUEST):
        if not REQUEST:
            return None
        response = getattr(REQUEST, 'RESPONSE', None)
        if not response or response.status == 302:
            return None

        message = REQUEST.get('alphaflow_status_message', default_message)

        activity = self.getActivity()
        if activity.completionUrlExpression:
            url = utils.evaluateTales(activity.completionUrlExpression,
                                      workitem=self)
            response.redirect(url)
        else:
            content = self.getContentObject()
            content.af_redirect_after_action(message)

    security.declareProtected(config.HANDLE_WORKITEM, 'needs_data')
    def needs_data(self):
        """Indicates whether the work item edit form needs to be displayed
        before performing an action.
        """
        return len(self.getGroupedSchema()) > 1


InitializeClass(BaseAssignableWorkItem)


class BaseAutomaticWorkItem(BaseWorkItem):
    """A base class for work items that work automatically."""

    security = ClassSecurityInfo()

    zope.interface.implements(IAutomaticWorkItem)

    _automatic_continue = True

    security.declareProtected(config.WORK_WITH_PROCESS, "getActions")
    def getActions(self):
        """Determine all possible actions."""
        return []  # Automatic

    security.declarePrivate("isRelevant")
    def isRelevant(self, user):
        """Checks if this workitem is relevant to this user."""
        return False # Automatic


    security.declarePrivate("notifyAssigneesChange")
    def notifyAssigneesChange(self):
        """notifies the workitem that the assignees might have changed
        """
        # we are automatic. The assignees never ever change. Thus we do nothing
        pass

    security.declarePrivate("onStart")
    def onStart(self):
        """Runs the automatic procedure, handles exceptions and moves on."""
        try:
            BaseWorkItem.onStart(self)
            self.run()
        except Exception, m:
            ILifeCycleController(self).fail("Automatic activity failed.", m)
        else:
            if self._automatic_continue:
                self.passCheckpoint("continue")
            ILifeCycleController(self).complete(
                "Automatic activity `%s` was successfully executed." % 
                self.getActivity().title_or_id())

    security.declareProtected(config.WORK_WITH_PROCESS, 'getShortInfo')
    def getShortInfo(self):
        """Short information"""
        return "automatic activity"

    security.declareProtected(config.WORK_WITH_PROCESS, 'getStatusInfo')
    def getStatusInfo(self):
        """Short status information"""
        return "Success"

    security.declarePrivate("run")
    def run(self):
        """Performs the actual automatic activity"""
        pass

InitializeClass(BaseAutomaticWorkItem)


@zope.component.adapter(IWorkItem, ILifeCycleEvent)
def update_after_event(work_item, event):
    work_item.notifyAssigneesChange()
    work_item.getInstance().notifyWorkItemStateChange(work_item)


################
# Helper classes

class Group:
    """Helper class to support a specific sort order when 
       grouping multiple schemas into a single schema.
    """

    zope.interface.implements(IFieldGroup)

    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, instance, activity_id, fields):
        self.instance = instance
        self.activity_id = activity_id
        self.fields = fields

    def __cmp__(self, other):
        return cmp(self.getSortPriority(), other.getSortPriority())

    def Title(self):
        return self.getActivity().title_or_id()

    def getProcess(self):
        return self.instance.getProcess()

    def getActivity(self):
        return self.getProcess()[self.activity_id]

    def getSortPriority(self):
        return self.getActivity().sortPriority


class GenericLogEntry(object):

    zope.interface.implements(Products.AlphaFlow.interfaces.IWorkItemLogEntry)
    zope.component.adapts(Products.AlphaFlow.interfaces.IWorkItem)

    def __init__(self, context):
        self.context = context
        self.controller = \
            Products.AlphaFlow.interfaces.ILifeCycleController(context)

    @property
    def state(self):
        return self.controller.state

    @property
    def users(self):
        pm = getToolByName(self.context, 'portal_membership')
        if self.controller.completed:
            users = [self.controller.completed_by]
        else:
            users = self.context.listRelevantUsers()
        return [pm.getMemberById(user) for user in users]

    @property
    def task(self):
        try:
            activity = self.context.getActivity()
        except AttributeError:
            return 'n/a'
        else:
            return activity.title

    @property
    def results(self):
        """Titles of the checkpoints that were passed, except start and end."""
        checkpoints = [x for x in self.context.checkpoints_passed 
                       if x not in [Products.AlphaFlow.config.CHECKPOINT_START,
                                    Products.AlphaFlow.config.CHECKPOINT_COMPLETE]]
        try:
            activity = self.context.getActivity()
        except AttributeError:
            titles = ""
        else:
            titles = [activity[x].title for x in checkpoints]
            titles = ", ".join(titles)
        return titles

    @property
    def date(self):
        if self.controller.completed:
            return self.controller.end
        return DateTime.DateTime()

    @property
    def comment(self):
        return self.context.getComment()

    @property
    def annotation(self):
        return ''
