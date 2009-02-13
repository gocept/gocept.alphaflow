# Copyright (c) 2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
#
import unittest

from AccessControl import SpecialUsers

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.interfaces import ILifeCycleController
from Products.AlphaFlow.activities.interfaces import \
     INTaskWorkItem, ITerminationActivity, ITerminationWorkItem
from Products.AlphaFlow.activities.termination import \
     TerminationActivity, TerminationWorkItem


class TerminationTest(AlphaFlowTestCase):

    interfaces_to_test = [
        (ITerminationWorkItem, TerminationWorkItem),
        (ITerminationActivity, TerminationActivity),
        ]

    def _init_object(self, wf='workflows/termination.alf'):
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf(wf)

        wftool = getToolByName(portal, 'workflow_manager')

        self.login("author")
        mtool = getToolByName(portal, 'portal_membership')
        home = mtool.getHomeFolder("author")
        # Create object for instanciation of this process
        home.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = home.testdocument
        doc.assignProcess(self.test_process)
        return doc

    def test_termination(self):
        doc = self._init_object('workflows/termination.alf')
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start("testing")

        self.assertEquals('ended', controller.state)
        self.assertEquals(True, controller.completed)

        workitems = instance.getWorkItems(state='ended')
        self.assertEquals(2, len(workitems))
        if INTaskWorkItem.providedBy(workitems[0]):
            task, termination = workitems
        else:
            termination, task = workitems
        self.assertEquals(False, ILifeCycleController(task).completed)
        self.assertEquals(True, ILifeCycleController(termination).completed)

    def test_object_deletion(self):
        doc = self._init_object('workflows/termination_delete.alf')
        instance = doc.getInstance()
        container = doc.getParentNode()
        id = doc.getId()
        assert id in container.objectIds()

        controller = ILifeCycleController(instance)
        controller.start("testing")

        self.assertEquals('ended', controller.state)
        self.assertEquals(True, controller.completed)

        self.assert_(id not in container.objectIds())

    def test_recursive(self):
        doc = self._init_object('workflows/termination_recursive.alf')
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start("testing")

        task = instance.getWorkItems()[0]
        task.complete(exit="complete")
        self.assertEquals('ended', controller.state)
        self.assertEquals(True, controller.completed)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TerminationTest))
    return suite
