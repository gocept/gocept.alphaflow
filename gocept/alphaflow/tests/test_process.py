# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase

from Products.AlphaFlow.interfaces import \
    IProcess, IProcessVersion
from Products.AlphaFlow.process import Process, ProcessVersion


class ProcessTest(AlphaFlowTestCase):

    interfaces_to_test = [(IProcess, Process),
                          (IProcessVersion, ProcessVersion),
                          ]

    def test_process_revert(self):
        self.portal['foo'] = Process('foo')
        # Acquisition wrapping
        process = self.portal['foo']
        self.assertRaises(Exception, process.revert)

        base_version = process.editable(ProcessVersion())
        self.assertRaises(Exception, process.revert)

        process.update()
        self.assertEquals(None, process.editable())
        process.revert()
        self.assertEquals(None, process.editable())

        new_version = process.editable(base_version.getId())
        process.revert()
        self.assertEquals(None, process.editable())
        process.revert()
        self.assertEquals(None, process.editable())


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessTest))
    return suite
