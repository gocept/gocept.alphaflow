# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.process import Process, ProcessVersion


class TimeLimittemplateTest(AlphaFlowTestCase):

    interfaces_to_test = [ ]

    def test_use_timelimit_template(self):
        wftool = self.portal.workflow_manager
        wftool.processes['dummy'] = Process('dummy')
        wftool.processes["dummy"].editable(ProcessVersion())
        wftool.processes["dummy"].update()
        process = wftool.processes['dummy'].current()

        # Load form
        self.assertPublish("@@template-timelimit", process)

        # Submit form
        self.assertEquals(0, len(process.objectIds()))
        self.assertPublish("@@template-timelimit?form.actions.apply=Save&form.assignment=decision&form.assignment-empty-marker=1&form.title=Irgendwas",
                           process)
        self.assertEquals(5, len(process.objectIds()))

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TimeLimittemplateTest))
    return suite
