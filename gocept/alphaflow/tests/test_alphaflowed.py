# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

import zope.component
import zope.interface
import zope.publisher.interfaces.browser

from Products.Five.traversable import FakeRequest
from gocept.alphaflow.interfaces import IAlphaFlowed
from gocept.alphaflow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from gocept.alphaflow.workflowedobject import AlphaFlowed


class AlphaFlowedTests(AlphaFlowTestCase):
    # Tests aspects of objects that support having a process instance assigned.

    interfaces_to_test = [(IAlphaFlowed, AlphaFlowed),
                          ]
    def test_protocol_macro(self):
        portal = self.portal
        self.loginAsPortalOwner()
        portal.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = portal.testdocument
        request = FakeRequest()
        zope.interface.directlyProvides(
            request, zope.publisher.interfaces.browser.IDefaultBrowserLayer)
        protocol_view = zope.component.getMultiAdapter(
            (doc, request), name='workflow_protocol')
        self.assertEquals('startTag', protocol_view.index.macros['protocol'][3][0])
        self.assertEquals('table', protocol_view.index.macros['protocol'][3][1][0])

    def test_no_late_defaults(self):
        # AT has an annoyance that sets the defaults although the values might be set already
        # we avoid this to allow setting values during manage_afterAdd that don't get overwritten.
        self.portal.createObject('foo', 'DefaultTestContent')
        self.assertEquals('during_add', self.portal['foo'].body)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AlphaFlowedTests))
    return suite 
