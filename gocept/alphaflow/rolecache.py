# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Process manager"""

from BTrees.OOBTree import OOBTree

import zope.interface

from Products.AlphaFlow.interfaces import IRoleCache


class RoleCache:
    """support for caching roles in a fast efficient manner"""

    zope.interface.implements(IRoleCache)

    cache_names = ['_workitem_role_cache', '_content_role_cache',
                   '_instance_workitem_cache', '_instance_role_cache']

    def initializeRoleCache(self):
        for name in self.cache_names:
            if hasattr(self, name):
                continue
            setattr(self, name, OOBTree())

    def updateCacheByWorkItem(self, workitem):
        """updates cache for workitem"""
        instance = workitem.getInstance()
        self._build_workitem_cache(workitem, instance)
        self._aggregate_role_cache(instance)
        content = workitem.getContentObject()
        if content is not None:
            # XXX Log a warning because this indicates an inconsistent state?
            content.reindexObjectSecurity()

    def updateCacheByContent(self, content):
        if not hasattr(content.aq_base, 'getInstance'):
            return
        instance = content.getInstance()
        if instance is not None:
            self.updateCacheByInstance(instance, index_content=False)
            instance.updateWorkItems()

    def updateCacheByInstance(self, instance, index_content=True):
        for workitem in instance.getWorkItems():
            self._build_workitem_cache(workitem, instance)
        self._aggregate_role_cache(instance)
        content = instance.getContentObject()
        if index_content:
            content.reindexObjectSecurity()

    def getDynamicRolesForWorkItem(self, workitem, user):
        return self._workitem_role_cache[workitem.getId()][user]

    def getDynamicRolesForInstance(self, instance, user):
        return self._instance_role_cache[instance.getId()][user]

    def getDynamicRolesForContent(self, content, user):
        return self._content_role_cache[content.UID()][user]

    def listRelevantUsersForWorkItem(self, workitem):
        """return a list with all relevant users for a workitem
        relevant are all assigned users
        """
        cache = self._workitem_role_cache
        workitem_user_roles = cache.get(workitem.getId(), {})
        return list(workitem_user_roles.keys())


    def listRelevantUsersForInstance(self, instance):
        """return a list with all relevant users for instance
        """
        cache = self._instance_role_cache
        instance_cache = cache.get(instance.getId(), {})
        return list(instance_cache.keys())


    def listRelevantUsersForContent(self, content):
        """return a list with all relevant users for content
        """
        cache = self._content_role_cache
        content_cache = cache.get(content.UID(), {})
        return list(content_cache.keys())

    #########
    # private

    def _build_workitem_cache(self, workitem, instance):
        """update workitem_role_cache and instance_workitem_cache with
        relevant users for workitem
        """
        workitem_role_cache = self._workitem_role_cache
        instance_workitem_cache = self._instance_workitem_cache

        workitem_id = workitem.getId()
        instance_id = instance.getId()
        relevant_users = workitem.listRelevantUsers()

        if relevant_users:
            iwc = instance_workitem_cache.get(instance_id)
            if iwc is None:
                instance_workitem_cache[instance_id] = iwc = OOBTree()
            iwc[workitem_id] = True

            workitem_role_cache[workitem_id] = workitem_user_roles = {}
            for user in relevant_users:
                workitem_user_roles[user] = ['Assignee']
        else:
            try:
                del instance_workitem_cache[instance_id][workitem_id]
            except KeyError:
                pass
            else:
                if not instance_workitem_cache[instance_id]:
                    del instance_workitem_cache[instance_id]

            try:
                del workitem_role_cache[workitem_id]
            except KeyError:
                pass

    def _aggregate_role_cache(self, instance):
        """update instance_role_cache and content_role_cache from
        workitem_role_cache and instance_workitem_cache
        """
        workitem_role_cache = self._workitem_role_cache

        instance_id = instance.getId()
        content_uid = instance.getContentObjectUID()

        # XXX Design issue: A workitem/activity wants to dynamically include
        # a role on the content object. This is possible by setting the attribute
        # 'contentRoles' on the activity. Every user assigned to a workitem of that
        # activity will get these roles while the workitem is active and he is assigned.
        # XXX This implementation might also be a bottleneck regarding speed. I don't
        # finally understand the whole local role cache architecture.

        content_user_roles = {}
        for wi in self._instance_workitem_cache.get(instance_id, {}).keys():
            if not workitem_role_cache.has_key(wi):
                continue

            activity = instance[wi].getActivity()
            cRoles = getattr(activity, "contentRoles", None)

            for user in workitem_role_cache[wi]:
                if user not in content_user_roles:
                    content_user_roles[user] = ["ProcessUser"]
                if cRoles:
                    content_user_roles[user].extend(cRoles)

        if content_user_roles:
            self._instance_role_cache[instance_id] = instance_user_roles = {}
            for user in content_user_roles:
                instance_user_roles[user] = ["ProcessUser"]

            self._content_role_cache[content_uid] = content_user_roles
        else:
            try:
                del self._instance_role_cache[instance_id]
            except KeyError:
                pass

            try:
                del self._content_role_cache[content_uid]
            except KeyError:
                pass
