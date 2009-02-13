# vim:fileencoding=utf-8
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Test harness for process instances. """

import unittest
import transaction

import DateTime
import Products.AlphaFlow.tests.AlphaFlowTestCase
import Products.AlphaFlow.browser.instance


class InstanceTests(Products.AlphaFlow.tests.AlphaFlowTestCase.AlphaFlowTestCase):

    def test_workflowlog(self):
        doc = self._init_object('workflows/instancetest.alf')

        instance = doc.getInstance()

        request = None
        log = Products.AlphaFlow.browser.instance.WorkflowLog(doc, request)
        self.assertEquals([], log.log_entries)

        Products.AlphaFlow.interfaces.ILifeCycleController(instance).start('testing')

        # There are two active work items
        log = Products.AlphaFlow.browser.instance.WorkflowLog(doc, request)
        self.assertEquals(2, len(log.log_entries))
        foo = log.log_entries[0]
        self.assertEquals('active', foo.state)
        self.assertEquals(1, len(foo.users))
        self.assertEquals('Foo', foo.task)
        self.assertEquals('', foo.results)
        self.assert_(isinstance(foo.date, DateTime.DateTime))
        self.assertEquals('', foo.comment)
        self.assertEquals('', foo.annotation)

        bar = log.log_entries[1]
        self.assertEquals('active', bar.state)
        self.assertEquals([], bar.users)
        self.assertEquals('Bar', bar.task)
        self.assertEquals('', bar.results)
        self.assert_(isinstance(bar.date, DateTime.DateTime))
        self.assertEquals('', bar.comment)
        self.assertEquals('', bar.annotation)

        # Now we terminate one and complete the other. The terminated one is
        # gone, the other is shown with an updated state:
        foo.controller.terminate('foo')
        bar.controller.complete('bar')

        # The workflow is completed now, we still see the workflow log,
        # though.
        log = Products.AlphaFlow.browser.instance.WorkflowLog(doc, request)
        self.assertEquals(1, len(log.log_entries))
        bar = log.log_entries[0]
        self.assertEquals('ended', bar.state)
        self.assertEquals(['author'], [x.getUserName() for x in bar.users])
        self.assertEquals('Bar', bar.task)
        self.assertEquals('', bar.results)
        self.assert_(isinstance(bar.date, DateTime.DateTime))
        self.assertEquals('', bar.comment)
        self.assertEquals('', bar.annotation)

    def test_workflowlog_noinstance(self):
        doc = self._init_object('workflows/instancetest.alf', attach=False)

        # We can ask for the log and see an empty version if there is no instance attached yet.
        request = None
        log = Products.AlphaFlow.browser.instance.WorkflowLog(doc , request)
        self.assertEquals([], log.log_entries)
        self.assertEquals(None, doc.getInstance())

    def test_renaming_object(self):
        doc = self._init_object('workflows/instancetest.alf', attach=True)
        transaction.commit()

        self.assert_(doc.getInstance().getContentObject().aq_base is doc.aq_base)
        self.portal['Members']['author'].manage_renameObject('testdocument',
                                                             'notestdocument')
        self.assert_(doc.getInstance().getContentObject().aq_base is doc.aq_base)

    def test_allinstances(self):
        # No instance at all
        doc = self._init_object('workflows/instancetest.alf', attach=False)
        self.assertEquals(0, len(doc.getAllInstances()))

        # One instance, freshly created
        doc2 = self._init_object(workflow='workflows/instancetest.alf',
                                 make_users=False, id='testdocument2')
        self.assertEquals(1, len(doc2.getAllInstances()))
        self.assertEquals(doc.getInstance(), doc2.getAllInstances()[0])
        instance = doc.getInstance()
        Products.AlphaFlow.interfaces.ILifeCycleController(
            instance).start('testing')

        # Complete the instance
        log = Products.AlphaFlow.browser.instance.WorkflowLog(doc2, None)
        log.log_entries[0].controller.complete('foo')
        log.log_entries[1].controller.complete('foo')

        # Still showing up, but not the current one anymore
        self.assertEquals(1, len(doc2.getAllInstances()))
        self.assertEquals(None, doc2.getInstance())
        self.assertNotEquals(None, doc2.getAllInstances()[0])

        # Get another instance for that document
        doc2.assignProcess(self.test_process)
        self.assertEquals(2, len(doc2.getAllInstances()))
        self.assertNotEquals(None, doc2.getInstance())
        # The first instance in the list is the current ones, old instances follow.
        self.assertEquals(doc2.getInstance(), doc2.getAllInstances()[0])
        self.assertNotEquals(doc2.getInstance(), doc2.getAllInstances()[1])

    def test_failedinstance_noworkitems(self):
        doc = self._init_object('workflows/instancetest.alf')

        # Initially, the instance isn't started, so there are no workitems.
        self.assertEquals([], doc.getWorkItemsForCurrentUser())

        # Start the instance, now there is a work item.
        instance = doc.getInstance()
        controller = (
            Products.AlphaFlow.interfaces.ILifeCycleController(instance))
        controller.start('testing')
        self.assertEquals(1, len(doc.getWorkItemsForCurrentUser() ))

        # Now, when we fail the instance, the work item disappears.
        controller.fail('testing')
        work_items = doc.getWorkItemsForCurrentUser()
        self.assertEquals([], doc.getWorkItemsForCurrentUser())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(InstanceTests))
    return suite 
