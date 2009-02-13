# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# test_configuration.py,v 1.1.2.1 2005/04/28 13:31:32 mac Exp

import unittest

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.interfaces import\
     IConfigurationActivity, IConfigurationWorkItem, ILifeCycleController
from Products.AlphaFlow.activities.configuration import \
     ConfigurationActivity, ConfigurationWorkItem
from Products.AlphaFlow.exception import ConfigurationError


class ConfigurationTest(AlphaFlowTestCase):

    interfaces_to_test = [(IConfigurationActivity, ConfigurationActivity),
                          (IConfigurationWorkItem, ConfigurationWorkItem)
                          ]

    def test_grouped_schema_not_all(self):
        self._import_wf("workflows/configuration.alf")
        portal = self.portal
        alf = getToolByName(portal, 'workflow_manager')
        doc = self.create(portal, "DummyContent", "doc")
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start('test')
        wis = instance.getWorkItems()
        self.assertEqual(1, len(wis))
        gs = wis[0].getGroupedSchema()
        act_ids_expected = ['write_doc', 'review', 'assign_task']
        act_ids_expected.sort()
        act_ids_got = [g.activity_id for g in gs]
        act_ids_got.sort()
        self.assertEquals(act_ids_expected, act_ids_got)

    def test_0config_success2(self):
        self.failIf(self._import_wf("workflows/configuration_all.alf"))

    def test_1config_fail1(self):
        # test missing configures attribute
        self.assertRaises(ConfigurationError,
                          self._import_wf,
                          path="workflows/configuration_fail_1.alf")

    def test_grouped_schema_all(self):
        self._create_test_users()
        self._import_wf('workflows/multi_review_with_config.alf')
        portal = self.portal
        alf = getToolByName(portal, 'workflow_manager')
        portal.invokeFactory("DummyContent", "doc")
        doc = portal.doc
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start('test')
        wis = instance.getWorkItems()
        self.assertEqual(1, len(wis))
        gs = wis[0].getGroupedSchema()
        act_ids_expected = sorted(['write_document', 'review_document1',
                                   'review_document2', 'config_at_start'])
        act_ids_got = sorted([g.activity_id for g in gs])
        self.assertEquals(act_ids_expected, act_ids_got)
        self.assertEquals(gs[0].Title(), 'Dokument schreiben')

    def test_multiple_filtered_configuration(self):
        self._import_wf('workflows/simple_review_choose_reviewer.alf')
        portal = self.portal
        alf = getToolByName(portal, 'workflow_manager')
        portal.invokeFactory("DummyFolder", "testfolder")
        doc = portal.testfolder
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start('test')
        wis = instance.getWorkItems()
        self.assertEqual(1, len(wis))
        gs = wis[0].getGroupedSchema()

        # We have to check the normal Schema of the activity as well.
        # One bug once had the correct grouped schema but the normal
        # Schema() method which AT uses still included _all_ possible
        # configuration items. Stupid.
        schema_fields = wis[0].Schema().keys()
        self.failIf("review_draft_assignees" in schema_fields, 
                    "review_draft_assginees should not be available")

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ConfigurationTest))
    return suite 

if __name__ == '__main__':
    framework()

