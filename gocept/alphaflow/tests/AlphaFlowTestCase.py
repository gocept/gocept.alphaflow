# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# AlphaFlowTestCase.py,v 1.12 2005/04/19 22:08:37 thomas Exp

import os

from AccessControl.SecurityManagement import newSecurityManager

import zope.component

from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.tests import PloneTestCase
from Testing import ZopeTestCase

# Import dummy content to enable registration for tests
import Products.AlphaFlow.tests.content

import zope.interface.verify

ZopeTestCase.installProduct("PlacelessTranslationService")
ZopeTestCase.installProduct("SiteAccess")
ZopeTestCase.installProduct("BTreeFolder2")
ZopeTestCase.installProduct("ZCatalog")
ZopeTestCase.installProduct("AlphaFlow")
ZopeTestCase.installProduct("PloneTestCase")
ZopeTestCase.installProduct("Five")

PloneTestCase.setupPloneSite(products=('AlphaFlow',))

from Products.AlphaFlow.interfaces import IWorkflowImporter
from Products.AlphaFlow.process import Process

from Products.AlphaFlow.utils import mailhostTestingModePatch
mailhostTestingModePatch()

from Products.AlphaFlow import config
config.ENABLE_ZODB_COMMITS = False


class AlphaFlowTestCase(PloneTestCase.FunctionalTestCase):
    '''AlphaFlow testcase'''

    _add_members = [
        ('author', (), 'Hans Wurst'),
        ('editor1', (), 'Hans von der Wurst'),
        ('editor2', (), 'Hans'),
        ('editor3', ('ChiefEditor',), 'Chef')
    ]

    _add_groups = [
        ('group1', ['editor1', 'editor2', 'editor3']),
    ]

    interfaces_to_test = []
    z2_interfaces_to_test = []

    def afterSetUp(self):
        super(AlphaFlowTestCase, self).afterSetUp()
        uf = self.portal.acl_users
        uf._doAddUser('manager', 'secret', ['Manager'], [])
        user = uf.getUser('manager').__of__(uf)
        newSecurityManager(None, user)

    def _import_wf(self, path="workflows/multi_review.alf", id="test",
                   valid=False):
        wftool = getToolByName(self.portal, "workflow_manager")
        f = open(os.path.join(os.path.dirname(__file__), path))
        importer = zope.component.getUtility(IWorkflowImporter, name='xml')
        version = importer(f)
        if id in wftool.processes.objectIds():
            wftool.processes.manage_delObjects([id])
        wftool.processes[id] = Process(id)
        process = wftool.processes[id]
        process.editable(version)
        process.update()
        self.test_process = process.current()
        f.close()
        if valid:
            process_ = wftool.processes[id].current()
            self.failIf(process_.validation_errors)

    def _init_object(self, workflow='workflows/switch.alf', attach=True,
                     make_users=True, id='testdocument'):
        portal = self.portal
        if make_users:
            self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf(workflow)

        # patch DummyContent
        def nextStep(self):
            return True
        from Products.AlphaFlow.tests.content import DummyContent
        DummyContent.nextStep = nextStep

        wftool = getToolByName(portal, 'workflow_manager')

        self.login("author")
        mtool = getToolByName(portal, 'portal_membership')
        home = mtool.getHomeFolder("author")
        # Create object for instanciation of this process
        home.createObject(id, "DummyContent")

        # Initialize the process
        doc = home.testdocument
        if attach:
            doc.assignProcess(self.test_process)
        return doc


    def _create_test_users(self):
        portal = self.portal
        pr = getToolByName(portal, 'portal_registration')
        pm = getToolByName(portal, 'portal_membership')

        portal.acl_users.addRole('Author')
        portal._addRole('Author')
        portal.acl_users.addRole('Editor')
        portal._addRole('Editor')
        portal.acl_users.addRole('ChiefEditor')
        portal._addRole('ChiefEditor')

        for name, roles, fullname in self._add_members:
            roles = ('Member',) + roles
            properties = {
                'username': name,
                'email': '%s@mailtest.gocept.com' % name,
                'fullname': fullname,
            }
            pr.addMember(name, 'password', roles=roles, properties=properties)
            pm.createMemberarea(member_id=name, minimal=0)

        # add groups
        gtool = getToolByName(portal, 'portal_groups')
        for group, users in self._add_groups:
            gtool.addGroup(group)
            group = gtool.getGroupById(group)
            for member in users:
                group.addMember(member)

    def create(self, context, type, id):
        context.invokeFactory(type, id)
        return getattr(context, id)

    def test_z2interface(self):
        failed = []
        for i, c in self.z2_interfaces_to_test:
            self.failUnless(i.isImplementedByInstancesOf(c),
                            "%r is not implemented by %r" % (i,c))
            methlist = i.namesAndDescriptions(all=True)
            for meth in methlist:
                if not hasattr(c, meth[0]):
                    failed.append('Method %r not implemented by %s' % (
                        meth[0], c))
        self.assertEquals(failed, [], 'Interface tests failed:\n%s' % (
            '\n'.join(failed), ))

    def test_interface(self):
        failed = []
        for i, c in self.interfaces_to_test:
            self.failUnless(zope.interface.verify.verifyClass(i, c),
                            "%r is not implemented by %r" % (i,c))

    # Additional assertion helpers

    def _get_path(self, obj):
        return '/'.join(obj.getPhysicalPath())

    def assertPublish(self, path, obj=None, basic='manager:secret'):
        if obj:
            path = self._get_path(obj) + '/' + path
        response = self.publish(path, basic=basic)
        self.assertEquals(200, response.status)
