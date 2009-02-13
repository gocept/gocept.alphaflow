# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Process manager"""

from threading import Lock

import transaction
import BTrees.OOBTree

import zope.interface
import zope.component

import zExceptions
import webdav.NullResource
import OFS.Folder
import AccessControl
import Globals

from Products.CMFCore.ActionProviderBase import ActionProviderBase
from Products.CMFCore.Expression import Expression
from Products.CMFCore.ActionInformation import ActionInformation
from Products.CMFCore.utils import getToolByName, UniqueObject
from Products.PlacelessTranslationService import utranslate
from Products.Archetypes.config import UID_CATALOG

import Products.AlphaFlow.interfaces
import Products.AlphaFlow.config
import Products.AlphaFlow.utils
import Products.AlphaFlow.rolecache


ping_lock = Lock()


class ProcessManager(Products.AlphaFlow.rolecache.RoleCache, UniqueObject,
                     ActionProviderBase, OFS.Folder.Folder):
    """A process management object."""

    zope.interface.implements(Products.AlphaFlow.interfaces.IProcessManager)

    id = 'workflow_manager'
    meta_type = "AlphaFlow Process Manager"
    plone_tool = 1

    manage_options = (
        dict(label='Overview', action='manage_overview'),
        dict(label='Processes', action='manage_definitions'),
        dict(label='Instances', action='manage_instances'),
        dict(label='Tools', action='manage_tools')
        ) + OFS.Folder.Folder.manage_options + \
            ActionProviderBase.manage_options

    manage_options = [ opt for opt in manage_options if opt['label'] not in
                      ['Contents', 'View', 'Properties']]

    security = AccessControl.ClassSecurityInfo()

    # Rolecache security settings
    security.declarePrivate('updateWorkItemCache')
    security.declarePrivate('updateCacheByContent')
    security.declarePrivate('updateCacheByInstance')
    security.declarePrivate('getDynamicRolesForWorkItem')
    security.declarePrivate('getDynamicRolesForInstance')
    security.declarePrivate('getDynamicRolesForContent')
    security.declarePrivate('listRelevantUsersForWorkItem')
    security.declarePrivate('listRelevantUsersForInstance')
    security.declarePrivate('listRelevantUsersForContent')
    security.declarePrivate('_get_role_cache')
    security.declarePrivate('_get_role_cache_entry')
    security.declarePrivate('_build_workitem_cache')
    security.declarePrivate('_aggregate_role_cache')

    processes = None
    instances = None

    def __init__(self, *args, **kwargs):
        ProcessManager.inheritedAttribute("__init__")(self, *args, **kwargs)
        self.portal_process_refs = BTrees.OOBTree.OOTreeSet()

    #########################
    # IProcessManager

    security.declarePublic("initProcess")
    def initProcess(self, definition, obj):
        """Create a new process instance for a content object."""
        # We need to handle the security for this methods ourselves. The user
        # has to have INIT_PROCESS on the content object.
        user = AccessControl.getSecurityManager().getUser()
        if not user.has_permission(Products.AlphaFlow.config.INIT_PROCESS, obj):
            raise zExceptions.Unauthorized(
                "initProcess", obj, Products.AlphaFlow.config.INIT_PROCESS)

        id = Products.AlphaFlow.utils.generateUniqueId(definition.getId())
        instance = zope.component.getMultiAdapter(
            (definition, obj, id),
            Products.AlphaFlow.interfaces.ILifeCycleObject)
        self.instances._setObject(id, instance)
        return self.instances[id]

    security.declareProtected(Products.AlphaFlow.config.MANAGE_WORKFLOW,
                              'listProcessDefinitions')
    def listProcessDefinitions(self):
        """Returns all processes defined in the portal."""
        rc = getToolByName(self, "reference_catalog")
        for uid in self.portal_process_refs:
            obj = rc.lookupObject(uid)
            if obj is None:
                continue
            yield obj

    security.declareProtected(Products.AlphaFlow.config.MANAGE_WORKFLOW,
                              'getStatistics')
    def getStatistics(self):
        """Return a dictionary with various statistical information"""
        cat = getToolByName(self, "workflow_catalog")
        query = dict(meta_type='Instance')

        all_count = len(cat(**query))

        query['state'] = 'active'
        active_count = len(cat(**query))

        query['state'] = 'failed'
        failed_count = len(cat(**query))

        result = {}
        result['all_count'] = all_count
        result['active_count'] = active_count
        result['failed_count'] = failed_count
        return result

    security.declareProtected(Products.AlphaFlow.config.MANAGE_WORKFLOW,
                              'listInstances')
    def listInstances(self, **search):
        """Return a list of instance objects found by the specified search."""
        query = dict(meta_type='Instance',
                     sort_on='modified',
                     sort_order='descending',
                     **search)
        wc = getToolByName(self, 'workflow_catalog')
        instances = wc(query)
        instances = [x.getObject() for x in instances]
        instances = [x for x in instances if x is not None]
        return instances

    security.declareProtected(Products.AlphaFlow.config.MANAGE_WORKFLOW,
                              "replaceInstances")
    def replaceInstances(self, old_version, new_process=None):
        """Terminate instances of old process version and restart with new
        process.

        XXX This method is untested.

        """
        if new_process is None:
            new_process = old_version.aq_inner.aq_parent.current()
        old_instances = self.listInstances(process_uid=old_version.UID())
        new_instances = []
        for instance in old_instances:
            # First terminate the old process ...
            obj = instance.getContentObject()
            Products.AlphaFlow.interfaces.ILifeCycleController(
                instance).terminate(
                    "Replaced with an instance of process %s." %
                    new_process.getId())
            # ... then create a new process.
            obj.assignProcess(new_process)
            new_instance = obj.getInstance()
            Products.AlphaFlow.interfaces.ILifeCycleController(
                new_instance).start(
                    "Replaced an instance of process version %s." %
                    old_version.UID())
            new_instances.append(new_instance)
        return new_instances

    security.declarePrivate('cleanUpInstances')
    def cleanUpInstances(self):
        """Removes garbage process instances."""
        orphans = []
        for id, instance in self.instances.objectItems():
            if (instance.state == "terminated" or
                instance.getContentObject() is None):
                orphans.append(id)
                continue
            if instance.getProcess() is None:
                orphans.append(id)

        self.instances.manage_delObjects(orphans)
        wc = getToolByName(self, 'workflow_catalog')
        wc.refreshCatalog(clear=1)

    security.declareProtected(Products.AlphaFlow.config.WORK_WITH_PROCESS,
                              "queryWorkItems")
    def queryWorkItems(self, user):
        """Return list of work items for the given user."""
        result = []
        wc = getToolByName(self, "workflow_catalog")
        rc = getToolByName(self, "reference_catalog")
        user = AccessControl.getSecurityManager().getUser().getUserName() #XXX

        for wi in wc(listRelevantUsers=user,
                     state="active",
                     showInWorkList=True):
            content = rc.lookupObject(wi.getContentObjectUID)
            if content is None:
                continue
            result.append(dict(
                wi=wi,
                contentTitle=content.Title(),
                getViewUrl=wi.getViewUrl,
                getActivityTitleOrId=wi.getActivityTitleOrId,
                getShortInfo=wi.getShortInfo))
        return result

    security.declarePublic("queryWorkItemsForCurrentUser")
    def queryWorkItemsForCurrentUser(self):
        """Return list of work items for the current user."""
        user = AccessControl.getSecurityManager().getUser()
        return self.queryWorkItems(user)

    security.declareProtected(Products.AlphaFlow.config.MANAGE_WORKFLOW,
                              'pingCronItems')
    def pingCronItems(self):
        """Send a trigger to all time-dependent objects."""
        # - We *lock* to avoid long running pings to run in
        #   parallel doing the same work and ending up with conflicts.
        # - We lock *non-blocking* and return a message when we could not
        #   acquire the lock to avoid subsequent pings to pile up.
        locked = ping_lock.acquire(False)
        if not locked:
            return ("AlphaFlow is already processing another ping. "
                    "This ping was ignored.")
        try:
            zope.event.notify(Products.AlphaFlow.interfaces.CronPing(self))
        finally:
            ping_lock.release()

    security.declarePrivate('restartHelper')
    def restartHelper(self, process, activity):
        """Restarts all work items of the given process and activity
        that are currently fallen out.

        """
        wc = getToolByName(self, "workflow_catalog")
        restarted = 0
        candidates = wc(process_uid=process,
                        activity_id=activity,
                        state="failed")
        for candidate in candidates:
            workitem = candidate.getObject()
            if workitem is None:
                continue
            # Restart it
            controller = \
                Products.AlphaFlow.interfaces.ILifeCycleController(workitem)
            controller.reset("Reset by restart helper.")
            controller.start("Start by restart helper.")
            restarted += 1
            if Products.AlphaFlow.config.ENABLE_ZODB_COMMITS:
                transaction.commit()
        return restarted

    security.declarePrivate('bulkDropin')
    def bulkDropin(self):
        """Recovers all instances that are currently fallen out."""
        candidates = list(self.listInstances(state='failed'))
        dropped_in = 0
        ignored = 0
        for candidate in candidates:
            controller = \
                Products.AlphaFlow.interfaces.ILifeCycleController(candidate)
            if controller.state != 'failed':
                # XXX For some reason I sometimes received instances multiple
                # times from the catalog. 
                continue
            try:
                controller.recover("Bulk dropin via ZMI.")
            except:
                # XXX This happens when a work item is still failed.
                # This should use a dedicated exception.
                ignored += 1
            else:
                dropped_in += 1
        return dropped_in, ignored

    security.declarePrivate('doSanityCheck')
    def doSanityCheck(self):
        """Perform a sanity check and cleanup."""
        issues = []

        def _clean_object(o, path):
            local_roles = o.__ac_local_roles__
            try:
                delattr(o.aq_base, '__ac_local_roles__')
            except:
                # don't care
                pass
            # IAlphaflowed have a class attribute __ac_local_roles__, which is
            # computed, we update this now:
            for user, roles in local_roles.items():
                if 'Assignee' in roles:
                    del roles[roles.index('Assignee')]
                local_roles[user] = roles
            o.__ac_local_roles__.update(local_roles)

        def _check_double_refs(o, path):
            # 1. check instance to content object mapping.
            # geee, this is going to be expensive
            #   a. get a content object (c1)
            #   b. get its instance
            #   c. get instance's content object (c2)
            #   d. see if c1 is c2
            c1 = o
            instance = c1.getInstance()
            if instance is None:
                return
            c2 = instance.getContentObject()

            if c1.aq_base is not c2.aq_base:
                issues.append("Not sane: %r (%r, %r)" % (instance, c1, c2))
                c1.alf_clearInstances()

        def _check(o, path):
            if Products.AlphaFlow.interfaces.IAlphaFlowed.providedBy(o):
                _check_double_refs(o, path)
                _clean_object(o, path)

        portal = getToolByName(self, 'portal_url').getPortalObject()
        cat = getToolByName(self, 'portal_catalog')
        cat.ZopeFindAndApply(portal, search_sub=True,
            apply_func=_check)

        return issues


@zope.component.adapter(ProcessManager,
                        zope.app.container.interfaces.IObjectAddedEvent)
def added_process_manager(ob, event):
    oids = ob.objectIds()
    if 'instances' not in oids:
        ob.manage_addProduct["BTreeFolder2"]. \
            manage_addBTreeFolder("instances")
    if "processes" not in oids:
        ob["processes"] = GlobalProcessContainer("processes")
    if 'email_templates' not in oids:
        ob.manage_addProduct['OFSP'].manage_addFolder('email_templates')
        ob.email_templates.manage_addProduct['OFSP'].manage_addDTMLMethod(
            'default_email', file='Default AlphaFlow Email')
    ob.initializeRoleCache()


Globals.InitializeClass(ProcessManager)


class GlobalProcessContainer(OFS.Folder.Folder):

    manage_options = (
        dict(label='Processes', action='manage_processes'),
        ) + OFS.Folder.Folder.manage_options

Globals.InitializeClass(GlobalProcessContainer)


@zope.component.adapter(Products.AlphaFlow.interfaces.IProcess,
                        zope.app.container.interfaces.IObjectAddedEvent)
def added_process_to_portal(process, event):
    pm = getToolByName(process, "workflow_manager")
    if process.UID() is None:
        # Workaround for bad interaction with other products that mess around
        # with manage_afterAdd patching and events. We really really need a
        # UID.
        process.manage_afterAdd(process, process.aq_parent)
    assert process.UID() is not None, "No UID assigned to process."
    pm.portal_process_refs.insert(process.UID())


@zope.component.adapter(Products.AlphaFlow.interfaces.IProcess,
                        zope.app.container.interfaces.IObjectRemovedEvent)
def removed_process_from_portal(process, event):
    if isinstance(event.object, ProcessManager):
        # The process manager is being deleted. We can forget about cleaning
        # up the references now.
        return
    pm = getToolByName(process, "workflow_manager")
    try:
        pm.portal_process_refs.remove(process.UID())
    except KeyError:
        pass
