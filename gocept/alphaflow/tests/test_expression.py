# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
#
import unittest

from AccessControl import SpecialUsers

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.interfaces import \
     IExpressionActivity, IExpressionWorkItem, ILifeCycleController
from Products.AlphaFlow.activities.expression import \
     ExpressionActivity, ExpressionWorkItem
from Products.AlphaFlow.aspects.interfaces import \
     IExpressionAspectDefinition, IExpressionAspect
from Products.AlphaFlow.aspects.expression import \
     ExpressionAspectDefinition, ExpressionAspect

from Products.AlphaFlow.utils import getTalesContext


class ExpressionTest(AlphaFlowTestCase):

    interfaces_to_test = [
        (IExpressionWorkItem, ExpressionWorkItem),
        (IExpressionActivity, ExpressionActivity),
        (IExpressionAspect, ExpressionAspect),
        (IExpressionAspectDefinition, ExpressionAspectDefinition),
        ]

    def _init_object(self, wf='workflows/expression.alf'):
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf(wf)

        wftool = getToolByName(portal, 'workflow_manager')

        self.login("author")
        mtool = getToolByName(portal, 'portal_membership')
        home = mtool.getHomeFolder("author")
        # Create object for instanciation of this process
        home.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = home.testdocument
        doc.assignProcess(self.test_process)
        return doc

    def test_definition(self):
        doc = self._init_object()

        # props not existing
        self.assertRaises(AttributeError,
                          getattr, doc, "asdf_asdf_prop_hjkl")
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start("testing")
        self.assertEquals(controller.state, "active")
        self.assertEqual(2, doc.asdf_asdf_prop_hjkl)
        wis = instance.getWorkItems()
        # only the task is left
        self.assertEquals(len(wis), 1)

    def test_runas(self):
        doc = self._init_object('workflows/expression-runas.alf')
        self.login('author')
        instance = doc.getInstance()
        ILifeCycleController(instance).start("testing")

        self.assertEquals('System Processes', doc.run_system)
        self.assertEquals('System Processes', doc.run_system_explicit)
        self.assertEquals('author', doc.run_current)
        self.assertEquals('author', doc.run_author)

    def test_talescontext(self):
        doc = self._init_object()
        self.login('author')

        instance = doc.getInstance()
        ILifeCycleController(instance).start('test')
        wi = instance.getWorkItems()[0]

        context = getTalesContext(workitem=wi)
        vars = context.vars

        self.assertEquals(doc, vars['content'])
        self.assertEquals(doc, vars['here'])
        self.assertEquals(wi, vars['workitem'])
        self.assertEquals(self.portal, vars['portal'])
        self.assertEquals(wi.getActivity(), vars['activity'])
        self.assertEquals('author',
                          vars['alphaflow']['currentUser'].getUserName())
        self.assertEquals(SpecialUsers.system, vars['alphaflow']['systemUser'])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ExpressionTest))
    return suite 
