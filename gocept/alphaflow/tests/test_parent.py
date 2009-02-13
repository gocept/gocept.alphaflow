# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest
import os.path

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.aspects.interfaces import \
        IParentAspect, IParentAspectDefinition
from Products.AlphaFlow.aspects.parent import \
        ParentAspect, ParentAspectDefinition
from Products.AlphaFlow.interfaces import ILifeCycleController
import Products.AlphaFlow.graphing

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')


class ParentTest(AlphaFlowTestCase):

    interfaces_to_test = [
       (IParentAspect, ParentAspect),
       (IParentAspectDefinition, ParentAspectDefinition)
        ]

    def test_graph_edges(self):
        self._import_wf('workflows/parent_graphing.alf')
        self.assertEquals(
            [],
            self.test_process['self_reference'].graphGetPossibleChildren())
        self.assertEquals(
            [{'exit': 'parent', 'id': 'self_reference',
              'label': 'parent of', 'qualifier': 'parent'}],
            self.test_process['normal'].graphGetPossibleChildren())
        graphing = Products.AlphaFlow.graphing.WorkflowGraph(self.test_process)

        expected_dot = file(
            os.path.join(OUTPUT_DIR, 'parent_graph.dot')).read()
        self.assertEquals(expected_dot, graphing._generate_dot().to_string())


    def test_parent(self):
        self._import_wf('workflows/parent.alf')
        portal = self.portal
        portal.invokeFactory('DummyContent', 'doc1')
        doc = portal.doc1
        notes = []

        def setRoute(route):
            doc.route = route

        def note(note):
            notes.append(note)

        doc.setRoute = setRoute
        doc.note = note

        doc.manage_addLocalRoles('manager', ['Manager'])

        doc.assignProcess(self.test_process)
        doc.route = 'escalate'
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start('testing')

        # escalate again
        self.assertEquals('active', controller.state)
        ntask = doc.getWorkItemsForCurrentUser()[0].complete('escalate')

        self.assertEquals('active', controller.state)
        ntask = doc.getWorkItemsForCurrentUser()[0].complete('finish')

        self.assertEquals('ended', controller.state)
        self.assertEquals(['start', 'escalate', 'start', 'normal', 'escalate',
                           'normal', 'finish'],
                          notes)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ParentTest))
    return suite

if __name__ == '__main__':
    framework()

