# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest
import transaction

from Products.AlphaFlow.interfaces import IAlphaFlowed
from Products.AlphaFlow import config

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase

from Products.ATContentTypes.content.document import ATDocument
from Products.ATContentTypes.content.event import ATEvent


class PatchTest(AlphaFlowTestCase):

    interfaces_to_test = [
        (IAlphaFlowed, ATDocument),
        (IAlphaFlowed, ATEvent),
        ]

    def test_working(self):
        portal = self.portal
        for type in ['Document', 'Event', 'File', 'Image', 'Link', 
                     'News Item']:
            portal.invokeFactory(type, 'testid-%s' % type)
            doc = getattr(portal, 'testid-%s' % type)
            self.failUnless(hasattr(doc, 'getSuitableProcesses'))
            transaction.savepoint()


def test_suite():
    suite = unittest.TestSuite()
    if config.PATCH_PLONE_TYPES:
        suite.addTest(unittest.makeSuite(PatchTest))
    return suite
