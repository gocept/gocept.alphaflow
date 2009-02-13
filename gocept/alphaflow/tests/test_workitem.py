# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

import Products.AlphaFlow.interfaces
from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.workitem import BaseWorkItem

from Acquisition import Implicit


class ContentDummy:

    def UID(self):
        return 1


class DummyInstance(Implicit):

    def __getitem__(self, key, default=None):
        return getattr(self, key, default)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def getInstance(self):
        return self


class WorkItemTest(AlphaFlowTestCase):

    interfaces_to_test = []

    def test_isChild(self):
        do = ContentDummy()
        pi = DummyInstance()

        for id in ["1", "1.1", "1.1.1", "1.2", "2"]:
            pi[id] = BaseWorkItem(id, "a")

        pi["1.1"].generated_by = "1"
        pi["1.1.1"].generated_by = "1.1"
        pi["1.2"].generated_by = "1"

        self.failUnless(pi["1.1"].isChildOf("1"))
        self.failUnless(pi["1.1.1"].isChildOf("1"))
        self.failUnless(pi["1.1.1"].isChildOf("1.1"))
        self.failUnless(pi["1.2"].isChildOf("1"))
        self.failIf(pi["1"].isChildOf("1"))
        self.failIf(pi["1.2"].isChildOf("1.1"))
        self.failIf(pi["1"].isChildOf("2"))
        self.failIf(pi["2"].isChildOf("1"))

        # This remodels a routing situation
        for id in ["R", "G1", "G2", "W1", "W2", "G1a"]:
            pi[id] = BaseWorkItem(id, "a")

        pi["G1"].generated_by = "R"
        pi["G2"].generated_by = "R"
        pi["W1"].generated_by = "R"
        pi["W2"].generated_by = "W1"
        pi["G1a"].generated_by = "W2"

        self.failUnless(pi["G1a"].isChildOf("R"))

    def test_getactivity_raises_attributeerror(self):
        doc = self._init_object('workflows/instancetest.alf')
        instance = doc.getInstance()

        controller = Products.AlphaFlow.interfaces.ILifeCycleController(instance)
        controller.start('testing')

        items = sorted(instance.getWorkItems(), key=lambda x:x.activity_id)
        work_item = items[0]
        self.assertEquals('bar', work_item.getActivity().getId())
        self.test_process.manage_delObjects(['bar'])
        # Gah. Cache cleanup needed.
        del work_item._v_my_activity
        self.assertRaises(AttributeError, work_item.getActivity)

        # We can still access the schema, though
        self.assert_(work_item.Schema())

    def test_action_url(self):
        doc = self._init_object('workflows/action_url.alf')
        instance = doc.getInstance()

        controller = Products.AlphaFlow.interfaces.ILifeCycleController(instance)
        controller.start('testing')

        configuration = instance.getWorkItems()[0]
        action = configuration.getActions()[0]
        self.assert_('af_edit_workitem' in action.getURL(configuration))

        action()
        task = instance.getWorkItems()[0]
        action = task.getActions()[0]
        self.assert_(action.getURL(task).endswith('/complete?exit=complete'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(WorkItemTest))
    return suite 
