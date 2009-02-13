# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.CMFCore.utils import getToolByName
from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.interfaces import \
        ISwitchWorkItem, ISwitchActivity, ILifeCycleController
from Products.AlphaFlow.activities.switch import \
        SwitchWorkItem, SwitchActivity

class SwitchTest(AlphaFlowTestCase):

    interfaces_to_test = [
       (ISwitchWorkItem, SwitchWorkItem),
       (ISwitchActivity, SwitchActivity)
        ]

    def test_definition(self):
        doc = self._init_object()

        instance = doc.getInstance()
        ILifeCycleController(instance).start("testing")
        self.assertEquals(instance.state, "active")
        wis = instance.getWorkItems(state="ended")
        self.assertEquals(len(wis), 3) # switch_ac_1, switch_ac_2, switch_ac_3
        for wi in wis:
            if wi.getActivity().getId() == "switch_ac_1":
                cont_ac_1 = wi
                break
        else:
            self.fail()
        self.assertEqual(cont_ac_1.activity_type, "switch")

        # test wis created by cont_ac_1
        cont_ac_1_wis = cont_ac_1.getGeneratedWorkItems()
        self.assertEqual(len(cont_ac_1_wis), 2)
        cont_ac_2 = cont_ac_1_wis[0]
        self.assertEqual(cont_ac_2.getActivity().getId(), "switch_ac_2")
        self.assertEquals(cont_ac_2.state, "ended")
        self.assertEqual(cont_ac_2.activity_type, "switch")
        cont_ac_3 = cont_ac_1_wis[1]
        self.assertEqual(cont_ac_3.getActivity().getId(), "switch_ac_3")
        self.assertEquals(cont_ac_3.state, "ended")
        self.assertEqual(cont_ac_3.activity_type, "switch")

        # test wis created by cont_ac_2
        cont_ac_2_wis = cont_ac_2.getGeneratedWorkItems()
        self.assertEqual(len(cont_ac_2_wis), 1)
        task1 = cont_ac_2_wis[0]
        self.assertEqual(task1.activity_type, "ntask")
        self.assertEqual(task1.getActivity().getId(), "do_this")

        # test wis created by cont_ac_3
        cont_ac_3_wis = cont_ac_3.getGeneratedWorkItems()
        self.assertEqual(len(cont_ac_3_wis), 2)
        task1 = cont_ac_3_wis[0]
        self.assertEqual(task1.activity_type, "ntask")
        self.assertEqual(task1.getActivity().getId(), "do_this")
        task2 = cont_ac_3_wis[1]
        self.assertEqual(task2.activity_type, "ntask")
        self.assertEqual(task2.getActivity().getId(), "do_that")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SwitchTest))
    return suite 

if __name__ == '__main__':
    framework()

