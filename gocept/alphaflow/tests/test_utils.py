# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from gocept.alphaflow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from gocept.alphaflow import utils


class UtilityTests(AlphaFlowTestCase):
    # Test our utility functions

    def test_append_to_query_string(self):
        self.assertEquals(
            'http://localhost?asdf=1',
            utils.urlAppendToQueryString('http://localhost', 'asdf=1'))
        self.assertEquals(
            'http://localhost?bsdf=2&asdf=1',
            utils.urlAppendToQueryString('http://localhost?bsdf=2', 'asdf=1'))
        self.assertEquals(
            'http://localhost?bsdf=2&asdf=Foo+bar',
            utils.urlAppendToQueryString('http://localhost?bsdf=2',
                                         'asdf=Foo+bar'))
        self.assertEquals(
            'http://localhost?bsdf=2&asdf=Foo+bar',
            utils.urlAppendToQueryString('http://localhost?bsdf=2',
                                         'asdf=Foo bar'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UtilityTests))
    return suite
