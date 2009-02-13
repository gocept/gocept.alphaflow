# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase

from Products.AlphaFlow.interfaces import IWorkflowGraph
from Products.AlphaFlow.graphing import WorkflowGraph


class WorkflowGraphTest(AlphaFlowTestCase):

    interfaces_to_test = [(IWorkflowGraph, WorkflowGraph)]

    def test_renderpng(self):
        self._import_wf('workflows/permission.alf')
        pm = self.portal.workflow_manager
        graph = WorkflowGraph(self.test_process)
        image = graph.render('png')
        self.assertEquals('\x89PNG', image[0:4])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(WorkflowGraphTest))
    return suite
