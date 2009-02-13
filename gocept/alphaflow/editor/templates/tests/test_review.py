# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.process import Process, ProcessVersion


class ParallelReviewTest(AlphaFlowTestCase):

    interfaces_to_test = [ ]

    def test_use_parallel_review_template(self):
        wftool = self.portal.workflow_manager
        wftool.processes['dummy'] = Process('dummy')
        wftool.processes["dummy"].editable(ProcessVersion())
        wftool.processes["dummy"].update()
        process = wftool.processes['dummy'].current()

        # Load form
        self.assertPublish("@@template-parallelreview", process)

        # Submit form
        self.assertEquals(0, len(process.objectIds()))
        self.assertPublish("@@template-parallelreview?form.actions.apply=Save&form.reviews=3&form.title=Review",
                           process)
        self.assertEquals(6, len(process.objectIds()))

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ParallelReviewTest))
    return suite
