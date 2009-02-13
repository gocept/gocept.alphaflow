# vim:fileencoding=utf-8
# Copyright (c) 2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Test harness for life cycle control. """

import unittest

import DateTime
import Products.AlphaFlow.tests.AlphaFlowTestCase
import Products.AlphaFlow.browser.instance


class LifeCycleTests(
    Products.AlphaFlow.tests.AlphaFlowTestCase.AlphaFlowTestCase):

    def test_second_fail_is_noop(self):
        doc = self._init_object('workflows/instancetest.alf')
        instance = doc.getInstance()

        controller = Products.AlphaFlow.interfaces.ILifeCycleController(instance)
        self.assertEquals([], controller.event_log)
        self.assertEquals('new', controller.state)

        controller.start('testing')
        self.assertEquals(1, len(controller.event_log))
        self.assertEquals('active', controller.state)

        # First fail: switches state and triggers callback
        controller.fail('foo')
        self.assertEquals(2, len(controller.event_log))
        self.assertEquals('failed', controller.state)

        # Second fail: doesn't switch, doesn't trigger and doesn't change log
        controller.fail('bar')
        self.assertEquals(2, len(controller.event_log))
        self.assertEquals('failed', controller.state)

        # Also, failing something that is ended, is a no-op
        controller.terminate('bar')
        self.assertEquals(3, len(controller.event_log))
        self.assertEquals('ended', controller.state)

        controller.fail('baz')
        self.assertEquals(3, len(controller.event_log))
        self.assertEquals('ended', controller.state)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LifeCycleTests))
    return suite 
