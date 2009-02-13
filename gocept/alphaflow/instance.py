# -*- coding: iso-8859-1 -*-
# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Process instances"""

import logging

import zope.app.annotation.interfaces
import zope.interface
import zExceptions
from Globals import InitializeClass
from AccessControl import getSecurityManager, ClassSecurityInfo
from Acquisition import ImplicitAcquisitionWrapper, aq_base

from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions
from Products.Archetypes.public import registerType

from Products.AlphaFlow.interfaces import \
    IInstance, IAlphaFlowed, IDaemonActivity, IWorkItemFactory, \
    ILifeCycleController, ILifeCycleEvent
from Products.AlphaFlow import config, utils
from Products.AlphaFlow.exception import UnknownActivityError
from Products.AlphaFlow.lifecycle import LifeCycleObjectBase


class InstanceLocalRoleFake(utils.LocalRoleFakeBase):
    """fakes a dictionary for local role support"""

    def _get_rolecache_for_user(self, user):
        alf = self._processmanager
        instance = self._context
        roles = alf.getDynamicRolesForInstance(instance, user)
        return roles

    def _get_users_with_cached_roles(self):
        return self._processmanager.listRelevantUsersForInstance(self._context)


class Instance(utils.DynamicLocalRoleSupport,
               utils.ContentObjectRetrieverBase, LifeCycleObjectBase):

    zope.interface.implements(
        IInstance,
        zope.app.annotation.interfaces.IAttributeAnnotatable)

    security = ClassSecurityInfo()

    alphaflow_type = "instance"

    object = None
    process_ref = None
    generated_workitems = ()

    log_name = "instance"
    log_children_name = "work items"

    # This variable monitors the stack of createWorkitem calls within one
    # request. We need this to defer the check whether the instance is
    # complete until we're back on the initial stack.
    _creating = 0

    schema = LifeCycleObjectBase.schema.copy()
    schema["id"].write_permission = permissions.ManagePortal
    schema['title'].required = False
    schema["title"].write_permission = permissions.ManagePortal

    global_allow = False

    manage_options = \
         ({'label' : 'Overview', 'action' : 'manage_overview'},
         ) + \
         LifeCycleObjectBase.manage_options

    local_role_fake_class = InstanceLocalRoleFake

    security.declareProtected(config.INIT_PROCESS, '__init__')
    def __init__(self, process, object, id):
        """Initialize a new process instance."""
        LifeCycleObjectBase.__init__(self, id)
        self.object = object.UID()
        self.process_uid = process.UID()

    security.declarePrivate('__repr__')
    def __repr__(self):
        try:
            state = ILifeCycleController(self).state
        except TypeError:
            state = 'n/a'
        return '<Instance (%s) on %s>' % (state, self.object)

    security.declarePublic('getCharset')
    def getCharset(self):
        """this is a skin method of archetypes returning the site encoding
        """
        return config.SITE_ENCODING

    # XXX security declaration?
    def absolute_url(self, inner=False):
       """A hackish way to use content objects as views.

           If this object is (directly) wrapped into an IAlphaFlowed,
           it will return the url of the IAlphaFlowed object"""
       absurl = Instance.inheritedAttribute("absolute_url")
       if inner:
           return absurl(self)

       if not hasattr(self, 'aq_chain'):
           return absurl(self)

       if len(self.aq_chain) < 2:
           return absurl(self)

       if IAlphaFlowed.providedBy(self.aq_chain[1]):
           return self.aq_chain[1].absolute_url()

       return absurl(self)

    ###########
    # IInstance

    def onStart(self):
        Instance.inheritedAttribute("onStart")(self)
        start_activities = self.getProcess().startActivity
        self.createWorkItems(start_activities, self)

    def onRecovery(self):
        Instance.inheritedAttribute("onRecovery")(self)
        self.notifyWorkItemStateChange()

    def onTermination(self):
        Instance.inheritedAttribute("onTermination")(self)
        self._unlink_content_instance()

    def onCompletion(self):
        Instance.inheritedAttribute("onCompletion")(self)
        self._unlink_content_instance()

    def _unlink_content_instance(self):
        """A helper method that moves an ended alphaflow instances away
        from the content object.

        """
        content = self.getContentObject()
        if content is not None:
            content.alf_old_instances = content.alf_old_instances + \
                    [self.getId()]
            content.instance_id = None

    security.declarePublic("getWorkItem")
    def getWorkItem(self, id):
        """IInstance'"""
        security = getSecurityManager()
        user = security.getUser()
        wi = getattr(self, id)
        if not user.has_permission(config.WORK_WITH_PROCESS, wi):
            raise zExceptions.Unauthorized, "You are not allowed to access " \
                                            "the workitem %r" % id
        return wi

    security.declarePrivate('unrestrictedGetWorkItem')
    def unrestrictedGetWorkItem(self, id):
        """Return the workitem with the given id"""
        wi = getattr(self, id)
        return wi

    security.declareProtected(config.WORK_WITH_PROCESS, "getWorkItems")
    def getWorkItems(self, state="active", activity_id=None):
        """Returns a list of work items in the given state."""
        ids = self.getWorkItemIds(state)
        unwrapped_self = aq_base(self)
        # The filter below avoids implicit acquisition when
        # our caches are stale.
        workitems = [getattr(self, id) for id in ids
                     if hasattr(unwrapped_self, id)]

        if activity_id is not None:
            workitems = [wi for wi in workitems
                         if wi.activity_id == activity_id]
        return workitems

    security.declareProtected(config.WORK_WITH_PROCESS, "getWorkItemIds")
    def getWorkItemIds(self, state="active"):
        if state is None:
            ids = self.objectIds()
        else:
            id_cache = getattr(self, '_cache_state_to_id', {})
            ids = list(id_cache.get(state, []))
        return ids

    security.declarePrivate("createWorkItems")
    def createWorkItems(self, activity_ids, source, content_object=None):
        """Creates a new workitem for the activity with the given name.

           Raises UnknownActivityError if one or more of the given activities
           do not exist.
        """
        if not activity_ids:
            return ()

        utils.logger.log(logging.DEBUG,
                  'Creating workitems %r in %r' % (activity_ids, source))

        self._creating += 1
        try:
            passed_activities = self._veto_workitem_creation(activity_ids,
                                                            source)
            new_ids, new = self._create_workitems_helper(passed_activities,
                                                         source,
                                                         content_object)
            source.generated_workitems += tuple(new_ids)
            for wi in new:
                controller = ILifeCycleController(wi)
                controller.start(
                    "Work item was created and automatically started.")
            self.notifyWorkItemStateChange()
        finally:
            self._creating -= 1

        # We need to explicitly check for completeness here again, because we
        # blocked the checks during creation.
        self._check_complete(self.getWorkItems('active'))
        return new_ids

    security.declarePrivate("notifyWorkItemStateChange")
    def notifyWorkItemStateChange(self, workitem=None):
        """Notifies the process instance, that at least one workitem changed
        it's state.

        The process instance then checks if either all workitems are completed
        or terminated, or a workitem fell out.

        """
        if workitem is not None:
            self._update_cache(workitem)

        self._index_workitems()

        if workitem is None:
            to_notify_about = [ x for x in self.getWorkItems(state=None)
                                if not x._af_notified ]
        else:
            to_notify_about = [workitem]

        failed = self._check_failed()
        if not failed:
            # Check if no active items are left
            workitems = self.getWorkItems(state="active")

            # Notify all active work items about the change
            for wi in workitems:
                for notify in to_notify_about:
                    wi.notifyWorkItemStateChange(notify)

            # Update that those work item state changes have propagated
            # to notifications
            for notified in to_notify_about:
                notified._af_notified = True

            self._check_complete(workitems)

    security.declareProtected(config.WORK_WITH_PROCESS,
                              "getActivityConfiguration")
    def getActivityConfiguration(self, field, activity_id, default=None):
        """Retrieves the configuration for this activity in the context of
           this instance.
        """
        field = "%s_%s" % (activity_id, field)
        try:
            value = self.Schema()[field].get(self)
        except KeyError:
            value = default
        return value

    ##########################
    # AT configuration support

    # XXX security declaration?
    def getObjSize(self):
        """This is a replacement to make AT not barf."""
        return 0

    # XXX security declaration?
    def get_size(self):
        """This is a replacement to make AT not barf."""
        return 0

    # XXX security declaration?
    def Schema(self):
        """Generate a schema to configure this instance."""
        # Get schemas from all the activities
        if hasattr(aq_base(self), "_v_cached_schema"):
            config_schema = self._v_cached_schema
        else:
            config_schema = self._get_schema()
            if self is not aq_base(self):
                # wrapped
                self._v_cached_schema = config_schema
        return self._wrap_schema(config_schema)

    security.declareProtected(config.WORK_WITH_PROCESS, 'getProcess')
    def getProcess(self):
        'IInstance'
        rc = getToolByName(self, "reference_catalog")
        return rc.lookupObject(self.process_uid)

    security.declareProtected(config.WORK_WITH_PROCESS, 'getInstance')
    def getInstance(self):
        "IInstance"
        return self.aq_inner

    security.declareProtected(config.WORK_WITH_PROCESS,
                              'updateWorkitemsAndContentObjects')
    def updateWorkitemsAndContentObjects(self):
        # called if the instance configuration has changed or alike.
        # I guess we only need to look at active workitems here.
        to_index = getattr(aq_base(self), '_v_workitems_to_index', None)
        if to_index is None:
            to_index = self._v_workitems_to_index = {}
        workitems = self.getWorkItems()
        for workitem in workitems:
            to_index[workitem.getId()] = 1
        self._index_workitems()

    security.declareProtected(config.WORK_WITH_PROCESS, 'updateWorkItems')
    def updateWorkItems(self):
        to_index = getattr(aq_base(self), '_v_workitems_to_index', None)
        if to_index is None:
            to_index = self._v_workitems_to_index = {}
        workitems = self.getWorkItems()
        for workitem in workitems:
            to_index[workitem.getId()] = 1
        self._index_workitems(update_content_security=False)

    #########################
    # IContentObjectRetriever

    security.declareProtected(config.WORK_WITH_PROCESS, 'getContentObject')
    def getContentObject(self):
        'IInstance'
        rc = getToolByName(self, "reference_catalog")
        ob = rc.lookupObject(self.object)
        return ob

    security.declareProtected(config.WORK_WITH_PROCESS, 'getContentObjectUID')
    def getContentObjectUID(self):
        return self.object

    ###################
    # private methods

    security.declarePrivate('_get_schema')
    def _get_schema(self, full=False):
        try:
            process = self.getProcess()
        except AttributeError:
            # Not yet in context. Ignore this
            return self.schema

        activities = process.objectValues()

        config_schema = self.schema.copy()
        content = self.getContentObject()

        if content is not None:
            for act in activities:
                schema = act.getConfigurationSchema(content)
                if schema is None:
                    continue
                # Rename and wrap fields for multiplexing
                for field in schema.fields():
                    if not full and field.__name__ in act.nonEditableFields:
                        # hide non edtiable fields
                        continue

                    field.group = act.getId()
                    # The following replace is a little hack to support
                    # using the activity's object id as a javascript identifier.
                    field.__name__ = act.getId().replace('.', '_') + "_" + field.__name__
                    act = act.__of__(self)
                    wfield = utils.FieldMultiplexWrapper(act, self, field)

                    try:
                        value = wfield.get(self)
                    except:
                        wfield.set(self, wfield.default)

                    config_schema.addField(wfield)
        return config_schema

    security.declarePrivate('_wrap_schema')
    def _wrap_schema(self, schema):
        return ImplicitAcquisitionWrapper(schema, self)

    security.declarePrivate('_update_cache')
    def _update_cache(self, workitem):
        """update internal state/workitem cache"""
        state_to_id = getattr(aq_base(self), '_cache_state_to_id', None)
        if state_to_id is None:
            state_to_id = self._cache_state_to_id = {}

        id_to_state = getattr(aq_base(self), '_cache_id_to_state', None)
        if id_to_state is None:
            id_to_state = self._cache_id_to_state = {}

        to_index = getattr(aq_base(self), '_v_workitems_to_index', None)
        if to_index is None:
            to_index = self._v_workitems_to_index = {}

        id = workitem.getId()
        new_state = ILifeCycleController(workitem).state
        old_state = id_to_state.get(id)

        if new_state != old_state:
            # remove old state from state_to_id,
            # NOTE: id_to_state will be overwritten implicitly
            ids_in_old_state = state_to_id.setdefault(old_state, {})
            try:
                del ids_in_old_state[id]
            except KeyError:
                pass

            # set new state
            state_to_id.setdefault(new_state, {})[id] = True
            id_to_state[id] = new_state
            to_index[id] = 1

            self._p_changed = 1

    security.declarePrivate('_index_workitems')
    def _index_workitems(self, update_content_security=True):
        """reindex the remembered workitems"""
        to_index = getattr(aq_base(self),
                           '_v_workitems_to_index', {})
        content_objects = {}
        for wi_id in to_index.keys()[:]:
            del to_index[wi_id]
            workitem = self.unrestrictedGetWorkItem(wi_id)
            workitem.reindexWorkitem()
            content = workitem.getContentObjectUID()
            content_objects[content] = 1

        if update_content_security:
            rc = getToolByName(self, 'reference_catalog')
            for content_uid in content_objects:
                content = rc.lookupObject(content_uid)
                if content is not None:
                    content.reindexObjectSecurity()

    security.declarePrivate('_rebuild_cache')
    def _rebuild_cache(self):
        for wi in self.objectValues():
            self._update_cache(wi)
        self._v_workitems_to_index = {}

    security.declarePrivate('_check_failed')
    def _check_failed(self):
        """Perform a check whether this instance is failed.

        This method returns True in two cases:

          1. The state of the process instance is `failed`
          2. At least one of the work items is failed.
        """
        items_failed = len(self.getWorkItemIds(state="failed"))
        controller = ILifeCycleController(self)
        if controller.state == 'failed':
            return True
        if items_failed > 0:
            controller.fail(
                "Automatically failed because %s work items failed." %
                items_failed)
            return True
        return False

    security.declarePrivate('_check_complete')
    def _check_complete(self, workitems):
        """End instance if only daemons are left.

        workitems -- list of active workitems (passed for performance reasons)

        This method is a bit weird, but works. There are two cases:

            1. If no active work items are left, we complete the instance.

            2. If only daemons are left, we complete those. As a side effect,
            when the last daemon is completed, we get another trigger for
            _check_complete and the instance will be completed by case 1.

        """
        if self._creating:
            # Do not check for completeness while we are still creating work
            # items.
            return

        controller = ILifeCycleController(self)
        daemons = [wi for wi in workitems
                   if IDaemonActivity.providedBy(wi.getActivity())]
        items_active = len(workitems)
        daemons_active = len(daemons)

        if controller.state != "active":
            # XXX Missing test
            # We don't have to check further as we are not active.
            return

        if not items_active:
            # Case 1: No active work items
            controller.complete(
                "Automatically completed instance as all work items ended.")

        if (controller.state == "active" and items_active == daemons_active):
            # Case 2: Only daemons are active
            for daemon in daemons:
                ILifeCycleController(daemon).complete(
                    "Automatically completed daemon.")

    #########################################
    # Helper methods for creating work items.

    security.declarePrivate('_veto_workitem_creation')
    def _veto_workitem_creation(self, activity_ids, source):
        vetoed = []
        for wi in self.getWorkItems():
            try:
                vetoed.extend(wi.beforeCreationItems(activity_ids, source))
            except Exception, m:
                ILifeCycleController(wi).fail("Vetoing failed.", m)
                return []

        create_activites = [ act_id for act_id in activity_ids
                             if act_id not in vetoed ]
        return create_activites

    security.declarePrivate('_create_workitems_helper')
    def _create_workitems_helper(self, activity_ids, source, content_object):
        if content_object is None:
            # If the workitem that spawns this WI has it's own overriden
            # content object, we stick to that if not requested otherwise.
            content_object = getattr(source, 'content_object', None)

        new = []
        new_wrapped = []
        new_ids = []
        process = self.getProcess()

        for activity_id in activity_ids:
            try:
                activity = process[activity_id]
            except KeyError:
                raise UnknownActivityError(
                    "Activity '%s' does not exist." % activity_id)
            new.extend(IWorkItemFactory(activity)(source, content_object))

        for wi in new:
            wi_id = wi.getId()
            new_ids.append(wi_id)
            wi.generated_by = source.getId()
            self._setObject(wi_id, wi)
            new_wrapped.append(getattr(self, wi_id))

        return new_ids, new_wrapped


InitializeClass(Instance)
registerType(Instance, config.PROJECTNAME)


@zope.component.adapter(IInstance, ILifeCycleEvent)
def update_after_event(instance, event):
    instance.reindexObject()
    instance.updateWorkitemsAndContentObjects()
