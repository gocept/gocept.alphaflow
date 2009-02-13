# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.interfaces import \
     IDecisionWorkItem, ISimpleDecisionActivity, ILifeCycleController
from Products.AlphaFlow.activities.simpledecision import SimpleDecisionWorkItem, SimpleDecisionActivity


class SimpleDecisionTest(AlphaFlowTestCase):

    interfaces_to_test = [
        (IDecisionWorkItem, SimpleDecisionWorkItem),
        (ISimpleDecisionActivity, SimpleDecisionActivity)
        ]

    def _init_object(self):
        # Creates a simple workflow
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf('workflows/simpledecision.alf')

        wftool = getToolByName(portal, 'workflow_manager')

        self.login("author")
        mtool = getToolByName(portal, 'portal_membership')
        home = mtool.getHomeFolder("author")
        # Create object for instanciation of this process
        home.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = home.testdocument
        doc.manage_addLocalRoles('editor1', ['Reviewer'])
        doc.manage_addLocalRoles('editor2', ['Reviewer'])
        doc.manage_addLocalRoles('editor3', ['Reviewer'])
        doc.assignProcess(self.test_process)
        return doc

    def _get_object(self):
        portal = self.portal
        mtool = getToolByName(portal, 'portal_membership')
        home = mtool.getHomeFolder("author")
        return home.testdocument

    def _decide(self, doc, action):
        instance = doc.getInstance()
        wi = instance.getWorkItems()[0]
        wi.getActionById(action)()

    def test_simpledecision(self):
        doc = self._init_object()
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start("testing")
        self.assertEqual(controller.state, "active")

        wis = instance.getWorkItems(state='active')
        self.assertEqual(1, len(wis)) # configuration
        self.assertEqual('config_deci_1', wis[0].getActivity().getId())
        instance.deci_1_assignees = ["editor1", "editor3"]
        wis[0].configure()

        wis = instance.getWorkItems(state='active')
        self.assertEqual(2, len(wis))
        wis[0].reject()
        wis[1].accept()

        wis = instance.getWorkItems(state='active')
        self.assertEqual(3, len(wis))
        wis[0].accept()
        wis[1].accept()
        wis[2].reject()

        wis = instance.getWorkItems(state='active')
        self.assertEqual(2, len(wis))
        wis[0].accept()
        wis[1].accept()

        wis = instance.getWorkItems(state='active')
        self.assertEqual(0, len(wis))
        self.assertEqual('ended', controller.state)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SimpleDecisionTest))
    return suite 
