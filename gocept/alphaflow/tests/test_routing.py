# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.Archetypes.tests.utils import *
from Products.Archetypes.tests.common import *

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.routing import RouteWorkItem, RouteActivity
from Products.AlphaFlow.activities.interfaces import \
     IRouteWorkItem, IRouteActivity, ILifeCycleController

class RouteTest(AlphaFlowTestCase):

    interfaces_to_test = [
       (IRouteWorkItem, RouteWorkItem),
       (IRouteActivity, RouteActivity)
        ]
    
    def test_definition(self):
        # Creates a simple workflow
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf('workflows/routing_example.alf')

        wftool = getToolByName(portal, 'workflow_manager')

        # Create object for instanciation of this process
        portal.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = portal.testdocument
        doc.assignProcess(self.test_process)

        process = doc.getInstance()
        controller = ILifeCycleController(process)
        controller.start("testing")
        self.assertEquals(controller.state, "active")

        self.login("author")
        doc.getWorkItemsForCurrentUser()[0].accept()
        doc.getWorkItemsForCurrentUser()[0].accept()
        doc.getWorkItemsForCurrentUser()[0].accept()

        self.assertEquals(controller.state, "ended")
        self.assertEquals(controller.completed, True)

        wis = process.getWorkItems(state=None)
        for wi in wis:
            self.failIfEqual(wi.state, "failed")

        # Do the same process but reject this time
        self.loginAsPortalOwner()
        doc.assignProcess(self.test_process)

        process = doc.getInstance()
        controller = ILifeCycleController(process)
        controller.start("testing")
        self.assertEquals(controller.state, "active")

        self.login("author")
        doc.getWorkItemsForCurrentUser()[0].accept()
        doc.getWorkItemsForCurrentUser()[0].reject()

        self.assertEquals(controller.state, "ended")
        self.assertEquals(controller.completed, True)

        wis = process.getWorkItems(state=None)
        for wi in wis:
            self.failIfEqual(wi.state, "failed")

    def test_routing_with_decision(self):
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf('workflows/routing_simpledec.alf')

        wftool = getToolByName(portal, 'workflow_manager')

        # Create object for instanciation of this process
        portal.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = portal.testdocument
        doc.assignProcess(self.test_process)

        process = doc.getInstance()
        controller = ILifeCycleController(process)
        controller.start("testing")
        self.assertEquals(controller.state, "active")

        self.login("editor1")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "active")

        self.login("author")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "active")

        self.login("editor3")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "active")

        self.login("editor2")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "ended")

        wis = process.getWorkItems(state=None)
        for wi in wis:
            self.failIfEqual(ILifeCycleController(wi).state, "failed")

        # Do the same process but reject this time
        self.loginAsPortalOwner()
        doc.assignProcess(self.test_process)

        process = doc.getInstance()
        controller = ILifeCycleController(process)
        controller = ILifeCycleController(process)
        controller.start("testing")
        self.assertEquals(controller.state, "active")

        self.login("author")
        doc.getWorkItemsForCurrentUser()[0].reject()
        self.assertEquals(controller.state, "active")

        self.login("editor1")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "active")

        self.login("editor2")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "active")

        self.login("editor3")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "ended")
        self.assertEquals(controller.completed, True)

        wis = process.getWorkItems(state=None)
        for wi in wis:
            self.failIfEqual(wi.state, "failed")

        # Do the same process but editor2 rejects this time
        self.loginAsPortalOwner()
        doc.assignProcess(self.test_process)

        process = doc.getInstance()
        controller = ILifeCycleController(process)
        controller.start("testing")
        self.assertEquals(controller.state, "active")

        self.login("author")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "active")

        self.login("editor1")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "active")

        self.login("editor2")
        doc.getWorkItemsForCurrentUser()[0].reject()
        self.assertEquals(controller.state, "active")

        self.login("editor3")
        doc.getWorkItemsForCurrentUser()[0].accept()
        self.assertEquals(controller.state, "ended")
        self.assertEquals(controller.completed, True)

        wis = process.getWorkItems(state=None)
        for wi in wis:
            self.failIfEqual(wi.state, "failed")


    def test_delayed_discriminator(self):
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf('workflows/routing_delayed_discriminator.alf')

        wftool = getToolByName(portal, 'workflow_manager')

        # Create object for instanciation of this process
        portal.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = portal.testdocument
        doc.assignProcess(self.test_process)

        process = doc.getInstance()
        controller = ILifeCycleController(process)
        controller.start("testing")
        self.assertEquals(controller.state, "active")

        self.login("author")
        doc.getWorkItemsForCurrentUser()[0].accept()
        doc.getWorkItemsForCurrentUser()[0].accept()
        doc.getWorkItemsForCurrentUser()[0].accept()

        self.assertEquals(controller.state, "ended")
        self.assertEquals(controller.completed, True)

        wis = process.getWorkItems(state=None)
        for wi in wis:
            self.failIfEqual(wi.state, "failed")

        # Do the same process but reject this time
        self.loginAsPortalOwner()
        doc.assignProcess(self.test_process)

        process = doc.getInstance()
        controller = ILifeCycleController(process)
        controller.start("testing")
        self.assertEquals(controller.state, "active")

        self.login("author")
        doc.getWorkItemsForCurrentUser()[0].reject()
        self.assertEquals(controller.state, "active")
        doc.getWorkItemsForCurrentUser()[0].accept()
        doc.getWorkItemsForCurrentUser()[0].accept()

        self.assertEquals(controller.state, "ended")
        self.assertEquals(controller.completed, True)

        wis = process.getWorkItems(state=None)
        for wi in wis:
            self.failIfEqual(wi.state, "failed")
    
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RouteTest))
    return suite 

if __name__ == '__main__':
    framework()

