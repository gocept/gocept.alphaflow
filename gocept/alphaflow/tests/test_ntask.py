# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# test_ntask.py,v 1.6.2.1 2005/04/28 13:31:32 mac Exp

import unittest

from Products.Archetypes.tests.utils import *
from Products.Archetypes.tests.common import *

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.interfaces import IExitDefinition
from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.interfaces import \
     INTaskWorkItem, INTaskActivity, ILifeCycleController
from Products.AlphaFlow.activities.ntask import \
     NTaskWorkItem, NTaskActivity
from Products.AlphaFlow.exception import ConfigurationError

class NTaskTest(AlphaFlowTestCase):

    interfaces_to_test = [
       (INTaskWorkItem, NTaskWorkItem),
       (INTaskActivity, NTaskActivity),
        ] 

    def _init_object(self, workflow="workflows/ntask.alf"):
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf(path=workflow)

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

    def test_definition(self):
        portal = self.portal
        wftool = getToolByName(portal, 'workflow_manager')
        doc = self._init_object()

        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start("testing")
        self.assertEquals("active", controller.state)

        wis = instance.getWorkItems()
        self.assertEquals(1, len(wis))

        ntaskitem = wis[0]
        self.assert_(INTaskWorkItem.providedBy(ntaskitem))

        actions = ntaskitem.getActions()
        self.assertEquals(5, len(actions))

        self.assertEquals([True, True, True, False, False],
                          [action.enabled for action in actions])

        expected_titles = ["Freigeben", "Mach alles kaputt",
                           "Privat schalten", "Prufen lassen",
                           "Wirf nen KeyError"]
        titles_got = sorted(x.title for x in actions)
        self.assertEquals(expected_titles, titles_got)
        controller.terminate("peng!")

        def checkExit(action, result_state):
            doc.assignProcess(self.test_process)
            instance = doc.getInstance()
            ILifeCycleController(instance).start("wuff")
            ntaskitem = instance.getWorkItems()[0]
            try:
                ntaskitem.complete(exit=action)
            except:
                ILifeCycleController(instance).terminate('error')
                raise

            result = ntaskitem.getGeneratedWorkItems()
            self.assertEquals(0, len(result))

            result_exits = [cp for cp in ntaskitem.objectValues()
                            if IExitDefinition.providedBy(cp.getDefinition())]
            self.assertEquals(1, len(result_exits))
            self.assertEquals(1, len(result_exits[0].objectValues()))

            result_aspect = result_exits[0].objectValues()[0].getDefinition()
            self.assertEquals(result_aspect.aspect_type, "dcworkflow")
            self.assertEquals(result_aspect.status, result_state)
            self.assertEquals(ILifeCycleController(ntaskitem).state, "ended")
            self.assertEquals(ILifeCycleController(ntaskitem).completed, True)

        # Check all exits
        checkExit("make_public", "published")
        checkExit("make_pending", "pending")
        checkExit("make_private", "private")
        self.assertRaises(RuntimeError, checkExit, "explode", "")
        self.assertRaises(RuntimeError, checkExit, "broken", "")

    def test_config_fail(self):
        # test failing of configuration
        self.assertRaises(ConfigurationError,
                          self._import_wf,
                          path="workflows/ntask_fail.alf")


    def test_task(self):
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        portal = self.portal
        self._import_wf(path="workflows/task.alf")

        portal.invokeFactory('DummyContent', 'doc1')
        doc = portal.doc1
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()

        ILifeCycleController(instance).start('testing')
        wi = instance.getWorkItems()

        # we expect 1 workitem due to wf defintion
        self.assertEquals(1, len(wi))

        # XXX This test should live somewhere else.
        self.assertEquals(None, wi[0].completed_by)

        # tasks should have one action
        actions = wi[0].getActions()
        self.assertEquals(1, len(actions))
        actions[0]()

        controller = ILifeCycleController(wi[0])
        self.assertEquals('ended', controller.state)
        self.assertEquals(True, controller.completed)

        # XXX This test should live somewhere else.
        self.assertEquals('portal_owner', wi[0].completed_by)

    def test_show(self):
        doc = self._init_object(workflow="workflows/task_show.alf")
        instance = doc.getInstance()

        process = instance.getProcess()
        self.assertEquals(True, process['visible'].showInWorkList)
        self.assertEquals(False, process['hidden'].showInWorkList)

        controller = ILifeCycleController(instance)
        controller.start("testing")
        self.assertEquals(2, len(instance.getWorkItems()))

        wftool = getToolByName(self.portal, 'workflow_manager')
        worklist = wftool.queryWorkItemsForCurrentUser()
        self.assertEquals(1, len(worklist))
        wi = worklist[0]['wi'].getObject()
        self.assertEquals('visible', wi.getActivity().getId())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(NTaskTest))
    return suite 
