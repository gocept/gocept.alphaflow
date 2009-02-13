# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

import zope.component

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase

from Products.AlphaFlow.interfaces import \
        IProcessManager, ILifeCycleController, IWorkItemClass
from Products.AlphaFlow.processmanager import ProcessManager


class ProcessManagerTest(AlphaFlowTestCase):

    interfaces_to_test = [(IProcessManager, ProcessManager),
                          ]

    def test_workitems_no_dcworkflow(self):
        dc_workflow = self.portal.portal_workflow
        for name, workitem in zope.component.getUtilitiesFor(IWorkItemClass):
            self.assertEquals((),
                              dc_workflow.getChainFor(workitem.portal_type))

    def test_getInstance(self):
        self._import_wf('workflows/permission.alf')
        portal = self.portal
        pm = portal.workflow_manager
        doc = self.create(portal, 'DummyContent', 'doc',)
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()

        self.failUnless(instance.aq_base is pm.instances[instance.getId()].aq_base)

    def test_someUI(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/permission.alf')
        portal = self.portal
        pm = portal.workflow_manager
        doc = self.create(portal, 'DummyContent', 'doc',)
        doc.assignProcess(self.test_process)

        instance = doc.getInstance()
        self.publish(instance.absolute_url()+"/manage_overview")

        ILifeCycleController(instance).start('Test')

        wi = instance.getWorkItems(None)[0]
        self.publish(wi.absolute_url()+"/manage_overview")

    def test_central_definitions(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/permission.alf')
        self.assertPublish('manage_definitions', self.portal.workflow_manager)

    def test_tools(self):
        self.loginAsPortalOwner()
        self.publish(self.portal.workflow_manager.absolute_url()+'/manage_tools')

    def test_clean(self):
        self._import_wf('workflows/permission.alf')
        portal = self.portal
        pm = portal.workflow_manager
        doc = self.create(portal, 'DummyContent', 'doc',)
        doc.assignProcess(self.test_process)

        # We delete the definition and check that the instance is removed by the cleanup script
        del pm.processes['test']
        pm.cleanUpInstances()
        self.assertEquals(False, doc.hasInstanceAssigned())

    def test_replaceInstances(self):
        self._import_wf('workflows/permission.alf', id="old")
        self._import_wf('workflows/ntask.alf', id="new")
        portal = self.portal
        pm = portal.workflow_manager
        old_version = pm.processes['old'].current()
        new_version = pm.processes['new'].current()
        doc = self.create(portal, 'DummyContent', 'doc',)
        doc.assignProcess(old_version)
        self.assert_(old_version.aq_base is
                     doc.getInstance().getProcess().aq_base)
        new = pm.replaceInstances(old_version, new_version)
        self.assert_(doc.hasInstanceAssigned())
        new_instance = doc.getInstance()
        self.assert_(new_version.aq_base is new_instance.getProcess().aq_base)
        self.assert_(ILifeCycleController(new_instance).state != "new")
        self.assertEquals(1, len(new))
        self.assert_(new[0].aq_base is new_instance.aq_base)

    def test_delete_process_manager(self):
        # Verifies that the process manager object can be deleted.
        # This verifies a bug where some event handlers would crash
        # when deleting the PM while processes still existed.
        self._import_wf('workflows/permission.alf', id="old")
        self._import_wf('workflows/ntask.alf', id="new")
        self.portal.manage_delObjects(['workflow_manager'])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessManagerTest))
    return suite
