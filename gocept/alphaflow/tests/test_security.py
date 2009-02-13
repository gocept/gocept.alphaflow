# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from AccessControl import getSecurityManager
from Products.PluginIndexes.common.PluggableIndex import \
        PluggableIndexInterface

from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase

import Products.AlphaFlow.utils
from Products.AlphaFlow.interfaces import \
    IProcessVersion, IInstance, ILifeCycleController
from Products.AlphaFlow.instance import Instance
from Products.AlphaFlow.process import ProcessVersion
from Products.AlphaFlow import utils
from Products.AlphaFlow.exception import ConfigurationError
from Products.AlphaFlow.eventchannel import EventChannelIndex

from Products.AlphaFlow.utils import getRolesOfPermission


class ContentMock:

    def __init__(self, uid):
        self.uid = uid

    def UID(self):
        return self.uid

    def reindexObject(self, idxs=None):
        pass

    def reindexObjectSecurity(self):
        pass


class InstanceMock:

    def __init__(self, id='instance-id', workitem=None):
        self.id = id
        self.workitem = workitem

    def getId(self):
        return self.id

    def __getitem__(self, key, default=None):
        # Fake for retrieving a work item
        return self.workitem

    def getContentObjectUID(self):
        return 'content-uid'

    def getWorkItemIds(self):
        return ['wi1', 'wi2']


class WorkItemMock:

    def __init__(self, id, relevant):
        self.id = id
        self.relevant = relevant

    def getId(self):
        return self.id

    def listRelevantUsers(self):
        return self.relevant

    def getInstance(self):
        return InstanceMock(workitem=self)

    def getActivity(self):
        return None

    def getContentObjectUID(self):
        return 'content-uid'

    def getContentObject(self):
        return ContentMock('content-uid')


class SecurityTest(AlphaFlowTestCase):

    interfaces_to_test = [(IInstance, Instance),
                          (IProcessVersion, ProcessVersion),]
    z2_interfaces_to_test = [(PluggableIndexInterface, EventChannelIndex),
                            ]

    def _create_instance(self):
        portal = self.portal
        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        f = instance.getField('write_document_assignees')
        f.set(instance, 'author')
        ILifeCycleController(instance).start('test')
        return instance

    def test_instance(self):
        self._create_test_users()
        self._import_wf()
        uf = self.portal.acl_users
        manager = uf.getUserById('manager')
        instance = self._create_instance()
        doc = instance.getContentObject()
        self.assertEquals(('ProcessUser',),
                            instance.get_local_roles_for_userid('author'))
        doc.manage_addLocalRoles('author', ['Author'])
        self.assertEquals(('Owner',),
                                instance.get_local_roles_for_userid(
                                        manager.getUserName()))
        self.assertEquals(('Writer', 'ProcessUser', 'Author'),
                            doc.get_local_roles_for_userid('author'))

    def test_workitem(self):
        self._create_test_users()
        self._import_wf()
        instance = self._create_instance()
        witems = instance.getWorkItems()
        self.assertEquals(1, len(witems))  # Only write doc is active. Recursion is disabled.
        write_doc = witems[0]
        self.assertEquals(('Assignee', ),
            write_doc.get_local_roles_for_userid('author'))

    def test_alphaflowed(self):
        self._create_test_users()
        self._import_wf('workflows/catalog_security.alf')

        portal = self.portal
        cat = getToolByName(portal, 'portal_catalog')

        self.loginAsPortalOwner()
        logged_in = getSecurityManager().getUser().getUserName()

        instance = self._create_instance()
        f = instance.getField('write_document_assignees')

        witems = instance.getWorkItems()
        write_doc = witems[0]
        doc = portal.doc

        self.assertEquals(('ProcessUser', ),
                          doc.get_local_roles_for_userid('author'))
        self.assertEquals(('Assignee', ),
                          write_doc.get_local_roles_for_userid('author'))
        self.assertEquals(('Owner',),
                          doc.get_local_roles_for_userid(logged_in))
        self.assertEquals(('Owner',),
                          write_doc.get_local_roles_for_userid(logged_in))
        self.assertEquals((),
                          doc.get_local_roles_for_userid('editor1'))
        self.assertEquals((),
                          write_doc.get_local_roles_for_userid('editor1'))

        # let's see what the catalog thinks,
        # we should see the document, we are the assignee because we have the
        # 'View' permission
        self.login('author')
        results = cat(getId='doc')
        self.assertEquals(1, len(results))
        self.assertEquals(1, len(doc.getWorkItemsForCurrentUser()))

        # when we assign somebody else than the author, the author should not
        # have access any longer
        f.set(instance, 'editor1')
        instance.updateWorkitemsAndContentObjects()

        self.assertEquals((),
                          doc.get_local_roles_for_userid('author'))
        self.assertEquals((),
                          write_doc.get_local_roles_for_userid('author'))
        self.assertEquals(('ProcessUser', ),
                          doc.get_local_roles_for_userid('editor1'))
        self.assertEquals(('Assignee', ),
                          write_doc.get_local_roles_for_userid('editor1'))

        results = cat(getId='doc')
        self.assertEquals(0, len(results))
        self.assertEquals(0, len(doc.getWorkItemsForCurrentUser()))

        # let's assign the author again
        f.set(instance, 'author')
        instance.updateWorkitemsAndContentObjects()

        # in review we, as author, may not view the document, complete and
        # check catalog again
        doc.getWorkItemsForCurrentUser()[0].complete('complete')
        results = cat(getId='doc')
        self.assertEquals(0, len(results))
        self.assertEquals((), doc.get_local_roles_for_userid('author'))
        self.assertEquals(0, len(doc.getWorkItemsForCurrentUser()))

    def test_permissions(self):
        mod = utils.modifyRolesForPermission
        portal = self.portal
        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        mod(doc, permissions.ModifyPortalContent, ('ProcessUser',),
            acquire=False)
        roles = doc.rolesOfPermission(permissions.ModifyPortalContent)
        self.assert_(not doc.acquiredRolesAreUsedBy(
            permissions.ModifyPortalContent))
        for role in roles:
            if role['name'] == 'ProcessUser':
                self.assertEquals('SELECTED', role['selected'])
            else:
                self.assertNotEquals('SELECTED', role['selected'])

    def test_memberswithroles(self):
        portal = self.portal

        self._create_test_users()
        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc

        listMembersWithLocalRoles = (
            Products.AlphaFlow.utils.listMembersWithLocalRoles)

        # When asking for no roles we receive no results
        self.assertEquals(set(), listMembersWithLocalRoles(doc, []))

        # Members with global roles are not listed:
        self.assertEquals(
            set(),
            listMembersWithLocalRoles(doc, ['ChiefEditor']))

        # Now we'll assign a local role to the member `editor1`:
        doc.manage_addLocalRoles('editor1', ['ChiefEditor'])
        self.assertEquals(
            set(['editor1']),
            listMembersWithLocalRoles(doc, ['ChiefEditor']))

        # Local roles from hierarchy levels further above are considered as
        # well:
        portal.manage_addLocalRoles('editor2', ['ChiefEditor'])
        self.assertEquals(
            set(['editor1', 'editor2']),
            listMembersWithLocalRoles(doc, ['ChiefEditor']))

    def test_possible_assignees(self):
        self._create_test_users()
        self._import_wf('workflows/possible_assignees.alf')
        self.loginAsPortalOwner()
        portal = self.portal
        portal.invokeFactory('Folder', 'f1')
        f1 = portal.f1
        f1.manage_addLocalRoles('editor1', ['Reviewer'])
        f1.manage_addLocalRoles('author', ['Author'])

        self.login('editor1')
        portal = self.portal
        f1 = portal.f1
        f1.manage_addLocalRoles('editor1', ['Owner'])
        f1.invokeFactory('DummyContent', 'doc')
        doc = f1.doc
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        schema = instance.Schema()

        # Case 1: Possible roles
        voc = list(schema.getField('write_document_assignees').Vocabulary())
        self.assertEquals(['author'], voc)

        # Case 2: Possible groups
        voc = list(schema.getField('review_document_assignees').Vocabulary())
        self.assertEquals(['editor1', 'editor2', 'editor3'], voc)

        # Edge case: neither possible selected
        voc = list(schema.getField('review_document2_assignees').Vocabulary())
        self.assertEquals([], voc)


    def test_actual_assignees(self):
        self._create_test_users()
        self._import_wf('workflows/actual_assignees.alf')
        portal = self.portal
        self.loginAsPortalOwner()
        portal.invokeFactory('Folder', 'f1')
        portal.manage_addLocalRoles('editor3', ['ChiefEditor'])
        f1 = portal.f1
        f1.manage_addLocalRoles('editor2', ['ChiefEditor'])
        f1.invokeFactory('DummyContent', 'doc')
        doc = f1.doc
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start("und ab dafuer")
        wi = instance.getWorkItems()
        self.assertEquals(1, len(wi))
        users = wi[0].listRelevantUsers()
        self.assertEquals(2, len(users))
        self.assert_('editor2' in users)
        self.assert_('editor3' in users)

    def test_fullProcess(self):
        self._create_test_users()
        self._import_wf('workflows/security_fullProcess.alf')
        portal = self.portal

        # Editor creates new document
        self.login('editor1')
        portal = self.portal
        mtool = getToolByName(portal, 'portal_membership')
        wftool = getToolByName(portal, "workflow_manager")
        home = mtool.getHomeFolder("editor1")
        home.manage_addLocalRoles('editor1', ['Member'])
        home.invokeFactory('DummyContent', 'doc')
        doc = home.doc
        doc.assignProcess(self.test_process)
        ILifeCycleController(doc.getInstance()).start("Los gehts")
        wi = wftool.queryWorkItemsForCurrentUser()[0]['wi'].getObject()
        wi.update(write_document_task="Bitte was schreiben",
            write_document_assignees=('author',),
            review_document1_assignees=("editor2",),
            review_document2_assignees=("editor1",))
        wi.configure()

        # Author writes document
        self.login('author')
        portal = self.portal
        wftool = getToolByName(portal, "workflow_manager")
        mtool = getToolByName(portal, 'portal_membership')
        home = mtool.getHomeFolder("editor1")
        doc = home.doc
        doc.update(title="test")
        wi = wftool.queryWorkItemsForCurrentUser()[0]['wi'].getObject()
        wi.update(comment="Habe fertig")
        wi.complete('complete')

        # Editor 2 reviews document
        self.login('editor2')
        portal = self.portal
        wftool = getToolByName(portal, "workflow_manager")
        mtool = getToolByName(portal, 'portal_membership')
        home = mtool.getHomeFolder("editor1")
        doc = home.doc
        doc.update(title="test2")
        wi = wftool.queryWorkItemsForCurrentUser()[0]['wi'].getObject()
        wi.update(comment="Ging so, kleine Aenderungen")
        wi.accept()

    def test_relevant_users_by_expression(self):
        self._import_wf('workflows/expression_assign.alf')
        self._create_test_users()
        portal = self.portal

        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        doc.test_assignees = ['gack']
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start("Los gehts")

        wi = instance.getWorkItems()[0]

        def check_assignees(expected):
            doc.test_assignees = expected
            wi = instance.getWorkItems()[0]
            self.assertEquals(expected, wi.listRelevantUsers())

        check_assignees(['author'])
        check_assignees(['author', 'foobar'])
        check_assignees([])


    def test_relevant_users_by_expression_fail(self):
        self.assertRaises(ConfigurationError, self._import_wf,
                          'workflows/expression_assign_fail.alf')

    def test_relevant_users_by_expression_fail2(self):
        self.assertRaises(ConfigurationError, self._import_wf,
                          'workflows/expression_assign_fail2.alf')

    def test_relevant_users_by_expression_fail3(self):
        self.assertRaises(ConfigurationError, self._import_wf,
                          'workflows/expression_assign_fail3.alf')

    def test_relevant_users_by_group(self):
        self._import_wf('workflows/group_assign.alf')
        self._create_test_users()

        portal = self.portal

        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start("Los gehts")

        wi = instance.getWorkItems()[0]
        self.assertEquals(['editor1', 'editor2', 'editor3'],
                          wi.listRelevantUsers())

    def test_rolecache(self):
        self.loginAsPortalOwner()
        portal = self.portal
        alf = getToolByName(portal, 'workflow_manager')

        wi = WorkItemMock('wi1', ['hans', 'heinrich'])
        wi2 = WorkItemMock('wi2', ['gaack'])
        alf.updateCacheByWorkItem(wi)

        def _check(exp_roles, obj, obj2, method):

            # relevant users should have the exp_role roles
            self.assertEquals(exp_roles, method(obj, 'hans'))
            self.assertEquals(exp_roles, method(obj, 'heinrich'))

            # wrong keys raise KeyError
            self.assertRaises(KeyError, method, obj, 'gaack')
            self.assertRaises(KeyError, method, obj2, 'heinrich')

        def _check_afterupdate(exp_roles, obj, method):

            # relevant users should have the exp_role roles
            self.assertEquals(exp_roles, method(obj, 'hans'))
            self.assertEquals(exp_roles, method(obj, 'heinrich'))

            # wrong keys raise KeyError
            self.assertRaises(KeyError, method, obj, 'foobar')

        content = ContentMock('content-uid')
        content2 = ContentMock('wuuuuuha')

        _check(['Assignee'], wi, wi2, alf.getDynamicRolesForWorkItem)
        _check(['ProcessUser'], wi.getInstance(), InstanceMock('wuuut'),
               alf.getDynamicRolesForInstance)
        _check(['ProcessUser'], content, content2,
               alf.getDynamicRolesForContent)
        #test listRelevantUsersFor*
        def _checkrelevant(got):
            got.sort()
            self.assertEquals(['hans','heinrich'], got)

        got = alf.listRelevantUsersForWorkItem(wi)
        _checkrelevant(got)
        got = alf.listRelevantUsersForInstance(wi.getInstance())
        _checkrelevant(got)
        got = alf.listRelevantUsersForContent(content)
        _checkrelevant(got)

        alf.updateCacheByWorkItem(wi2)
        _check(['Assignee'], wi, wi2, alf.getDynamicRolesForWorkItem)
        _check_afterupdate(['ProcessUser'], wi.getInstance(),
               alf.getDynamicRolesForInstance)
        _check_afterupdate(['ProcessUser'], content,
                           alf.getDynamicRolesForContent)

        # This test checks that I can delete the content object and still have
        # the work item sit around but not make the cache-update fail.

        # This covers a bug we found at a customer installation. 
        # The deletion of the content object is simulated by letting the work
        # item return None as its content object.
        # We simply don't update the object security when updating the cache for
        # the work item. This appears to be a valid work around for the given
        # inconsistency.
        wi.getContentObject = lambda:None
        alf.updateCacheByWorkItem(wi)


    def test_notifyAssigneesChange(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/cachetest.alf')
        self._create_test_users()
        portal = self.portal

        alf = getToolByName(portal, 'workflow_manager')

        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        doc.test_assignees = ['hans']
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start("Los gehts")
        wi = instance.getWorkItems()[0]

        self.assertEquals(['Assignee'],
                          alf.getDynamicRolesForWorkItem(wi, 'hans'))
        self.assertEquals(['ProcessUser'],
                          alf.getDynamicRolesForInstance(instance, 'hans'))

        doc.test_assignees = ['heinrich']
        wi.notifyAssigneesChange()

        self.assertRaises(KeyError,
                          alf.getDynamicRolesForWorkItem, wi, 'hans')
        self.assertEquals(['Assignee'],
                          alf.getDynamicRolesForWorkItem(wi, 'heinrich'))
        self.assertEquals(['ProcessUser'],
                          alf.getDynamicRolesForInstance(instance, 'heinrich'))

        wi_old = wi
        assignees = ['Ernie', 'Bert']
        doc.test_assignees = assignees
        wi.complete('complete')
        wi = instance.getWorkItems()[0]

        self.assertRaises(KeyError,
                          alf.getDynamicRolesForWorkItem, wi_old, 'heinrich')

        for assignee in assignees:
            self.assertEquals(['Assignee'],
                              alf.getDynamicRolesForWorkItem(wi, assignee))
            self.assertEquals(['ProcessUser'],
                              alf.getDynamicRolesForInstance(instance, assignee))

        self.assertRaises(KeyError,
                          alf.getDynamicRolesForInstance, instance, 'hans')
        self.assertRaises(KeyError,
                          alf.getDynamicRolesForInstance, instance, 'heinrich')

        doc.test_assignees = []
        wi.complete('complete')
        wi = instance.getWorkItems()[0]
        self.assertEquals({}, dict(alf._workitem_role_cache))

    def test_notifyAssigneesChange_content(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/cachetest_multi.alf')
        self._create_test_users()
        portal = self.portal

        alf = getToolByName(portal, 'workflow_manager')

        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        doc.test_assignees = ['hans']
        doc.test_assignees2 = ['hubert']
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start("Los gehts")

        self.assertEquals(['ProcessUser'],
                          alf.getDynamicRolesForContent(doc, 'hans'))
        self.assertEquals(['ProcessUser'],
                          alf.getDynamicRolesForContent(doc, 'hubert'))

        doc.test_assignees2 = ['karlheinz']
        alf.updateCacheByContent(doc)

        self.assertEquals(['ProcessUser'],
                          alf.getDynamicRolesForContent(doc, 'hans'))
        self.assertEquals(['ProcessUser'],
                          alf.getDynamicRolesForContent(doc, 'karlheinz'))
        self.assertRaises(KeyError,
                          alf.getDynamicRolesForContent, doc, 'hubert')

    def test_incrementalpermissions(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/permission.alf')
        self._create_test_users()
        portal = self.portal

        alf = getToolByName(portal, 'workflow_manager')

        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc

        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start("Los gehts")

        # step 1
        expected_roles = ["Manager", "Owner"]
        got_roles = getRolesOfPermission(doc, "Modify portal content")
        got_roles.sort()
        self.assertEquals(expected_roles, got_roles)

        # step 2
        self.login("author")
        wi = instance.getWorkItems()[0]
        wi.complete('complete')

        expected_roles = ["Manager", "Owner", "Reviewer"]
        got_roles = getRolesOfPermission(doc, "Modify portal content")
        got_roles.sort()
        self.assertEquals(expected_roles, got_roles)

        # step 3
        self.login("editor3")
        wi = instance.getWorkItems()[0]
        wi.complete('complete')

        expected_roles = ["Manager", "Reviewer"]
        got_roles = getRolesOfPermission(doc, "Modify portal content")
        got_roles.sort()
        self.assertEquals(expected_roles, got_roles)

        # step 4
        wi = instance.getWorkItems()[0]
        wi.complete('complete')

        expected_roles = []
        got_roles = getRolesOfPermission(doc, "Modify portal content")
        self.assertEquals(expected_roles, got_roles)

    def test_group_assignees(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/task_group.alf')
        self._create_test_users()
        portal = self.portal

        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start("Los gehts")

        wi = instance.getWorkItems()[0]
        got_users = wi.listRelevantUsers()
        got_users.sort()
        self.assertEquals(['editor1', 'editor2', 'editor3'], got_users)

    def test_expression_member(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/expression_member.alf')
        self._create_test_users()
        portal = self.portal

        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()

        self.login("author")
        ILifeCycleController(instance).start("Los gehts")

        self.assertEquals("author", doc.member)

    

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SecurityTest))
    return suite
