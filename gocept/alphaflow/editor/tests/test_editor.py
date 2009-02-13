# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

import zope.publisher.browser

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.editor.editor import\
        Editor, ActivityPanel, EditActivity
from Products.AlphaFlow.process import Process, ProcessVersion
import Products.AlphaFlow.config


class EditorViewTest(AlphaFlowTestCase):

    interfaces_to_test = [ ]

    def setUp(self):
        super(EditorViewTest, self).setUp()
        self._import_wf('workflows/editor_everything.alf', valid=False)
        self.editor_wf = \
            self.portal.workflow_manager.processes['test'].current()
        self.aspects = self.editor_wf.alarm['continue'].objectValues()

    def test_canRenderWorkflow(self):
        request = zope.publisher.browser.TestRequest()
        pm = self.portal.workflow_manager
        pm.processes['asdf'] = Process('asdf')
        process = pm.processes["asdf"].editable(ProcessVersion())
        process.title = "test"

        editorview = Editor(process, request)
        add_activity = EditActivity(process, request).add

        add_activity('ntask')
        act1 = process.objectValues()[0]
        add_activity('ntask')
        act2 = list(set(process.objectValues()) - set([act1]))[0]

        # we should have two activities in this process
        self.assertEquals(2, len(process.objectIds()))
        self.assertEquals(False, editorview.canRenderWorkflow())

        # now connect those and we should be able to display a graph
        act1[Products.AlphaFlow.config.CHECKPOINT_START].activities += (
            act2.id, )
        self.assertEquals(True, editorview.canRenderWorkflow())

    def test_editor_main(self):
        self.assertPublish('@@editor.html', self.editor_wf)
        self.assertPublish('@@edit', self.editor_wf)

    def test_editor_missing_start_activity(self):
        self.editor_wf.startActivity = ('non-existing',)
        self.assertPublish('@@edit', self.editor_wf)
        self.assertPublish('@@graph.png', self.editor_wf)
        self.assertPublish('@@map', self.editor_wf)

    def test_editor_graph(self):
        self.assertPublish('@@graph.png', self.editor_wf)
        self.assertPublish('@@map', self.editor_wf)

    def test_editor_activities(self):
        self.assertPublish('@@activitypanel', self.editor_wf)

    def test_editor_alarm(self):
        self.assertPublish('@@edit', self.editor_wf.alarm)
        self.assertPublish('@@activity_details', self.editor_wf.alarm)
        self.assertPublish('@@add_activity?activity=alarm&title=alarm2',
                           self.editor_wf)

    def test_editor_configuration(self):
        self.assertPublish('@@edit', self.editor_wf.configuration)
        self.assertPublish('@@activity_details', self.editor_wf.configuration)
        self.assertPublish(
            '@@add_activity?activity=configuration&title=configuration2',
            self.editor_wf)

    def test_editor_decision(self):
        self.assertPublish('@@edit', self.editor_wf.decision)
        self.assertPublish('@@activity_details', self.editor_wf.decision)
        self.assertPublish(
            '@@add_activity?activity=decision&title=decision2',
            self.editor_wf)

    def test_editor_email(self):
        self.assertPublish('@@edit', self.editor_wf.email)
        self.assertPublish('@@activity_details', self.editor_wf.email)
        self.assertPublish(
            '@@add_activity?activity=email&title=email2',
            self.editor_wf)

    def test_editor_ntask(self):
        self.assertPublish('@@edit', self.editor_wf.ntask)
        self.assertPublish('@@activity_details', self.editor_wf.ntask)
        self.assertPublish('@@edit', self.editor_wf.ntask.ntask_exit)
        self.assertPublish(
            '@@add_activity?activity=ntask&title=ntask2', self.editor_wf)
        self.assertPublish('@@add_exit', self.editor_wf.ntask)

    def test_editor_simpledecision(self):
        self.assertPublish('@@edit', self.editor_wf.simpledecision)
        self.assertPublish('@@activity_details', self.editor_wf.simpledecision)
        self.assertPublish(
            '@@add_activity?activity=simpledecision&title=simpledecision2',
            self.editor_wf)

    def test_editor_switch(self):
        self.assertPublish('@@edit', self.editor_wf.switch)
        self.assertPublish('@@activity_details', self.editor_wf.switch)
        self.assertPublish('@@edit', self.editor_wf.switch.switch_case)
        self.assertPublish(
            '@@add_activity?activity=switch&title=switch2',
            self.editor_wf)
        self.assertPublish('@@add_exit', self.editor_wf.switch)

    def test_editor_routing(self):
        self.assertPublish('@@edit', self.editor_wf.route)
        self.assertPublish('@@activity_details', self.editor_wf.route)
        self.assertPublish('@@edit', self.editor_wf.gate)
        self.assertPublish('@@activity_details', self.editor_wf.gate)
        self.assertPublish(
            '@@add_activity?activity=route&title=route2',
            self.editor_wf)
        self.assertPublish(
            '@@add_activity?activity=gate&title=gate2',
            self.editor_wf)

    def test_editor_checkpoint(self):
        self.assertPublish('@@edit', self.editor_wf.alarm['continue'])
        self.assertPublish('@@edit', self.editor_wf.alarm['CHECKPOINT_START'])
        self.assertPublish('@@edit', self.editor_wf.alarm['CHECKPOINT_COMPLETE'])

    def test_editor_dcworkflow(self):
        self.assertPublish('@@edit', self.aspects[0])
        self.assertPublish('@@add_aspect?aspect_type=dcworkflow',
                           self.editor_wf.alarm['continue'])

    def test_editor_expression_aspect(self):
        self.assertPublish('@@edit', self.aspects[1])
        self.assertPublish('@@add_aspect?aspect_type=expression',
                           self.editor_wf.alarm['continue'])

    def test_editor_email_aspect(self):
        self.assertPublish('@@edit', self.aspects[2])
        self.assertPublish('@@add_aspect?aspect_type=email',
                           self.editor_wf.alarm['continue'])

    def test_editor_parent(self):
        self.assertPublish('@@edit', self.aspects[3])
        self.assertPublish('@@add_aspect?aspect_type=parent',
                           self.editor_wf.alarm['continue'])

    def test_editor_permission(self):
        self.assertPublish('@@edit', self.aspects[4])
        # Add
        self.assertPublish('@@edit', self.aspects[4].objectValues()[0])
        # Remove
        self.assertPublish('@@edit', self.aspects[4].objectValues()[1])
        # Set
        self.assertPublish('@@edit', self.aspects[4].objectValues()[2])
        self.assertPublish('@@add_aspect?aspect_type=permission',
                           self.editor_wf.alarm['continue'])
        self.assertPublish('@@add_setting', self.aspects[4])

    def test_delete(self):
        # Delete an activity
        self.assertPublish('@@delete', self.editor_wf.alarm)
        self.assertRaises(AttributeError, getattr, self.editor_wf, 'alarm')
        # Delete an ntask exit
        self.assertPublish('@@delete', self.editor_wf.ntask.ntask_exit)
        self.assertRaises(AttributeError, getattr, self.editor_wf.ntask,
                          'ntask_exit')
        # Delete a switch case
        self.assertPublish('@@delete', self.editor_wf.switch.switch_case)
        self.assertRaises(AttributeError, getattr, self.editor_wf.switch,
                          'switch_case')

    def test_delete_aspect(self):
        # Delete an aspect
        # (I know that there are 5 aspects around, so removing the fifth with
        # result in index 4 not available anymore.)
        self.assertEquals(5,
                          len(self.editor_wf.alarm['continue'].objectIds()))
        self.assertPublish('@@delete', self.aspects[4])
        self.assertEquals(4,
                          len(self.editor_wf.alarm['continue'].objectIds()))

    def test_delete_permissionsetting(self):
        self.assertEquals(3,
                          len(self.aspects[4].objectValues()))
        self.assertPublish('@@delete', self.aspects[4].objectValues()[0])
        self.assertEquals(2,
                          len(self.aspects[4].objectValues()))


class ActivityPanelTest(AlphaFlowTestCase):

    interfaces_to_test = []

    def test_getActivities(self):
        self._import_wf('workflows/permission.alf')
        pm = self.portal.workflow_manager
        process = pm.processes['test'].current()
        request = zope.publisher.browser.TestRequest()

        ap = ActivityPanel(process, request)
        activities = ap.getActivities()
        self.assertEquals(11, len(list(activities)))

    def test_listProcessActivities(self):
        self._import_wf('workflows/permission.alf')
        pm = self.portal.workflow_manager
        process = pm.processes['test'].current()
        request = zope.publisher.browser.TestRequest()

        apview = ActivityPanel(process, request)
        activities = apview.listProcessActivities()
        self.assertEquals(5, len(activities))

    def test_addActivity(self):
        self._create_test_users()
        self._import_wf('workflows/permission.alf')
        pm = self.portal.workflow_manager
        process = pm.processes['test'].current()
        request = zope.publisher.browser.TestRequest()
        # test for a defined amount of activities this workflow provides
        before = set(process.objectIds())

        add_activity = EditActivity(process, request).add
        newactivity = add_activity("switch")
        process[newactivity].title = 'New activity as a test'
        after = set(process.objectIds())

        new = after - before
        self.assertEquals(1, len(new))
        new_activity = process[list(new)[0]]
        self.failUnless(new_activity.id.startswith("switch"))
        self.assertEquals("New activity as a test", new_activity.title)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(EditorViewTest))
    suite.addTest(unittest.makeSuite(ActivityPanelTest))
    return suite
