# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.CMFCore.utils import getToolByName

import Products.AlphaFlow.activities.decision
from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.interfaces import \
     IDecisionWorkItem, IDecisionActivity, ILifeCycleController
from Products.AlphaFlow.activities.decision import DecisionWorkItem, DecisionActivity
from Products.AlphaFlow.exception import ConfigurationError

class DecisionTest(AlphaFlowTestCase):

    interfaces_to_test = [
        (IDecisionWorkItem, DecisionWorkItem),
        (IDecisionActivity, DecisionActivity)
        ]

    def _init_object(self):
        # Creates a simple workflow
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf('workflows/decision.alf')

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
        doc.manage_addLocalRoles('editor3', ['Editor'])
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

    def test_1yes_part(self):
        doc = self._init_object()
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start("testing")
        self.assertEqual(controller.state, "active")
        wis = instance.getWorkItems(state='active')
        self.assertEqual(len(wis), 1) # deci_1
        self.assertEqual(wis[0].getActivity().getId(), "deci_1")

        # test what happened to the commentfield
        # should be not required, but hidden
        wischema = wis[0].Schema()
        expected = {'edit':-1, 'view':-1}
        self.assertEqual(wischema['comment'].required, False)
        self.assertEqual(wischema['comment'].widget.visible, expected)

        # test first yes
        self.login('editor2')
        doc = self._get_object()
        self._decide(doc, 'accept')
        instance = doc.getInstance()
        wis = instance.getWorkItems(state='active')
        self.assertEqual(len(wis), 1) # deci_n
        self.assertEqual(wis[0].getActivity().getId(), "deci_n")

        # test what happened to the commentfield
        # should be not required, but hidden
        wischema = wis[0].Schema()
        expected = {'edit':'visible', 'view':'visible'}
        self.assertEqual(wischema['comment'].required, True)
        self.assertEqual(wischema['comment'].widget.visible, expected)

        # test all yes
        self.login('editor1')
        doc = self._get_object()
        self._decide(doc, 'accept')
        instance = doc.getInstance()
        wis = instance.getWorkItems(state='active')
        self.assertEqual(len(wis), 1) # deci_n
        self.assertEqual(wis[0].getActivity().getId(), "deci_n")

        self.login('editor3')
        doc = self._get_object()
        self._decide(doc, 'accept')
        instance = doc.getInstance()
        wis = instance.getWorkItems(state='active')
        self.assertEqual(len(wis), 1) # deci_n
        self.assertEqual(wis[0].getActivity().getId(), "deci_n")

        # Log entry support
        entry = Products.AlphaFlow.activities.decision.DecisionLogEntry(wis[0])
        self.assertEquals(3, len(entry.users))
        self.assertEquals('editor3: accepted<br/>editor1: accepted',
                          entry.annotation)

        self.login('editor2')
        doc = self._get_object()
        self._decide(doc, 'accept')
        instance = doc.getInstance()
        self.failUnless(instance is None)

    def test_2no_part1(self):
        doc = self._init_object()
        instance = doc.getInstance()
        ILifeCycleController(instance).start("testing")

        # test first no
        self.login('editor1')
        doc = self._get_object()
        self._decide(doc, 'reject')
        instance = doc.getInstance()
        self.failUnless(instance is None)

    def test_3no_part2(self):
        doc = self._init_object()
        instance = doc.getInstance()
        ILifeCycleController(instance).start("testing")

        # first yes
        self.login('editor2')
        doc = self._get_object()
        self._decide(doc, 'accept')

        # test first no on all_yes
        self.login('editor3')
        doc = self._get_object()
        self._decide(doc, 'accept')

        self.login('editor2')
        doc = self._get_object()
        self._decide(doc, 'reject')
        instance = doc.getInstance()
        self.failUnless(instance is None)

    def test_0config_fail1(self):
        # test failing of configuration
        self.assertRaises(ConfigurationError,
                          self._import_wf,
                          path="workflows/decision_fail_1.alf")

    def test_0config_fail2(self):
        # test failing of configuration
        self.assertRaises(ConfigurationError,
                          self._import_wf,
                          path="workflows/decision_fail_2.alf")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DecisionTest))
    return suite 

if __name__ == '__main__':
    framework()
