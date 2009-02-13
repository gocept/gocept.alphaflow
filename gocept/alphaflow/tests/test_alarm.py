# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from DateTime import DateTime

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.interfaces import \
     IAlarmWorkItem, IAlarmActivity
from Products.AlphaFlow.activities.alarm import AlarmWorkItem, AlarmActivity
from Products.AlphaFlow.interfaces import ILifeCycleController


class AlarmTest(AlphaFlowTestCase):

    interfaces_to_test = [
       (IAlarmWorkItem, AlarmWorkItem),
       (IAlarmActivity, AlarmActivity)
    ]

    def _init_object(self):
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf('workflows/alarm_review.alf')

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

    def _getAlarmWorkItem(self, workitems):
        for wi in workitems:
            if IAlarmWorkItem.providedBy(wi):
                return wi
        raise RuntimeError

    def test_definition(self):
        portal = self.portal
        wftool = getToolByName(portal, 'workflow_manager')
        doc = self._init_object()

        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start("testing")
        self.assertEquals(controller.state, "active")
        wis = instance.getWorkItems()
        # one is the edit and one is the alarm
        self.assertEquals(len(wis), 2)

        alarm_wi = self._getAlarmWorkItem(wis)
        self.failUnless(alarm_wi)
        self.assertEquals(alarm_wi.getStatusInfo(), 
                          "deadline not yet reached")
        self.assertEquals(ILifeCycleController(alarm_wi).state,
                          "active")

        # we're testing if the deadline is not reached
        now = DateTime()
        datestring = '%d.%m.%Y %H:'
        # one minute in the future
        doc.deadline = now + 1/1440.0

        wftool.pingCronItems()
        self.assertEquals(alarm_wi.getStatusInfo(), "deadline not yet reached")
        self.assertEquals(ILifeCycleController(alarm_wi).state,
                          "active")
        self.assertEquals(alarm_wi.getGeneratedWorkItems(), [])

        # create a new DateTime() object to get a date one minute in the
        # past
        doc.deadline = now - 1/1440.0

        wftool.pingCronItems()
        self.assertEquals(ILifeCycleController(alarm_wi).state,
                          "ended")
        self.assertEquals(alarm_wi.getStatusInfo(), "deadline exceeded")
        self.assertEquals(len(alarm_wi.getGeneratedWorkItems()), 0)

        # test failure on error for new wf instance
        instance.getWorkItems('active')[0].complete('complete') # complete wf first
        wftool.pingCronItems()

        doc.assignProcess(self.test_process) # assign new process
        doc.deadline = 'gaak'

        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start("testing")
        wis = instance.getWorkItems()
        alarm_wi = self._getAlarmWorkItem(wis)

        wftool.pingCronItems()
        self.assertEquals(ILifeCycleController(alarm_wi).state,
                          "failed")
        self.assertEquals(controller.state, "failed")
        self.assertEquals(len(alarm_wi.getGeneratedWorkItems()), 0)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AlarmTest))
    return suite
