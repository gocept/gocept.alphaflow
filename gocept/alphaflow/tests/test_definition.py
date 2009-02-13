# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import os
import unittest
import string

import transaction
from random import shuffle
from tempfile import mktemp
from xml.dom import minidom

import zope.component
import zope.interface
import zope.app.annotation.interfaces

from OFS.SimpleItem import SimpleItem

from Products.Archetypes.tests.utils import *
from Products.Archetypes.tests.common import *

from Products.CMFCore.utils import getToolByName
from Products.Archetypes.Referenceable import Referenceable

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase

from Products.AlphaFlow.tests.content import DummyContent

from Products.AlphaFlow.interfaces import \
    IProcessVersion, IInstance, IActivity, IActivityClass, \
    IWorkItem, IAutomaticWorkItem, IAction, IAssignableActivity, \
    IAutomaticActivity, ILifeCycleController, IWorkflowImporter
from Products.AlphaFlow.aspects.interfaces import IPermissionSetting
from Products.AlphaFlow.xmlimport.interfaces import IWorkflowAttribute
from Products.AlphaFlow.xmlimport.attribute import WorkflowAttribute
from Products.AlphaFlow.instance import Instance
from Products.AlphaFlow.lifecycle import \
     LifeCycleControllerFactory
from Products.AlphaFlow.process import Process, ProcessVersion
from Products.AlphaFlow.activity import \
      BaseAssignableActivity, BaseActivity, BaseAutomaticActivity
from Products.AlphaFlow.workitem import \
    BaseWorkItem, BaseAutomaticWorkItem
from Products.AlphaFlow.action import Action
from Products.AlphaFlow.aspects.permission import PermissionSetting
from Products.AlphaFlow.activities.decision import DecisionWorkItem
from Products.AlphaFlow.utils import flexSplit
from Products.AlphaFlow.checkpoint import ExitDefinition
import Products.AlphaFlow.aspects.expression

from Products.AlphaFlow.exception import UnknownActivityError


_ids_used = {}
def get_random_id():
    id = None
    while id is None or _ids_used.get(id, False):
        id = list(string.ascii_lowercase)
        shuffle(id)
        id = ''.join(id)
    _ids_used[id] = True
    return id


class WorkitemFake(SimpleItem):

    zope.interface.implements(
        zope.app.annotation.interfaces.IAttributeAnnotatable)

    id = 'faked'

    def getId(self):
        return self.id


class ProcessDefinitionFake(SimpleItem, Referenceable):
    pass


class ProcessDefinitionTest(AlphaFlowTestCase):

    interfaces_to_test = [(IInstance, Instance),
                          (IWorkItem, BaseWorkItem),
                          (IAutomaticWorkItem, BaseAutomaticWorkItem),
                          (IAction, Action),
                          (IProcessVersion, ProcessVersion),
                          (IWorkflowAttribute, WorkflowAttribute),
                          (IAssignableActivity, BaseAssignableActivity),
                          (IActivity, BaseActivity),
                          (IAutomaticActivity, BaseAutomaticActivity),
                          (IPermissionSetting, PermissionSetting),
                          ]

    def _check_DOM_equality(self, exp_dom, got_dom, wf_name):
        """Check, if two DOMs are equal

        wf_name ... name of workflow-file
        """
        self._check_DOM_frag_recursive(exp_dom.documentElement,
                                       got_dom.documentElement,
                                       wf_name)


    def _check_DOM_frag_recursive(self, exp, got, wf_name):
        self.failIf(got is None,
                    "%s: %s(%s) missing in got DOM" % (wf_name,
                                                       exp.nodeName,
                                                       exp.attributes.items()))
        if exp.childNodes:
            exp_childs = self._filter_relevant_childs(exp).childNodes
            got = self._filter_relevant_childs(got)
            got_childs = got.childNodes
            self.assertEqual(len(exp_childs),
                             len(got_childs),
                             "%s:\nexp: %s\ngot: %s" % (wf_name, exp_childs,
                                                        got_childs))
            for child in exp_childs:
                self._check_DOM_frag_recursive(child,
                                               self._find_in_node(got, child),
                                               wf_name)
        documentElement = False
        if exp == exp.ownerDocument.documentElement:
            documentElement = True
        self._compare_DOM_nodes(exp, got, wf_name,
                                documentElement=documentElement)
    def _get_assignees_attrs(self):
        task = activity_registry.get('ntask')
        act_attrs = (findAttrInAttributes(task, 'assigneesKind'),
                     findAttrInAttributes(task, 'roles'),
                     findAttrInAttributes(task, 'assigneesExpression'),
                     )
        return act_attrs

    def _filter_relevant_attrs(self, node):
        "Get a sorted list of the relevant (not empty, not default) attributes."
        act_attrs = None
        nodeName = node.nodeName
        for registry in registries:
            try:
                act_attrs = registry.getFromDOMNode(node).attributes
                break
            except KeyError:
                pass
        if act_attrs is None:
            if nodeName == 'assignees':
                act_attrs = self._get_assignees_attrs()
            else:
                raise AssertionError, '%s: can not get Workflowattributes' % (
                    nodeName)
        res = []
        for attr, value in node.attributes.items():
            if value == '':
                continue
            if attr.startswith("editor:") or attr.startswith("xmlns"):
                continue
            if nodeName == 'workflow' and attr == 'id':
                continue # id in workflow tag may be left out or set by hand
            for act_attr in act_attrs:
                if (act_attr.domAttr == attr and
                    convert_to_xml(act_attr.default) == value):
                    break
            else:
                res.append((attr, value))
        return sorted(res)

    def _filter_relevant_childs(self, node):
        assignees_attrs = self._get_assignees_attrs()
        childNodes = node.childNodes[:]
        for child in childNodes:
            if child.nodeType in [minidom.Node.COMMENT_NODE,
                                  minidom.Node.TEXT_NODE]:
                # remove text and comment nodes
                node.removeChild(child)
            if child.nodeName == 'assignees':
                breaked = False
                for attr in assignees_attrs:
                    if child.getAttribute(attr.domAttr) != \
                           convert_to_xml(attr.default):
                        breaked = True
                        break
                if not breaked:
                    # remove assignees tag if all attributes are default
                    node.removeChild(child)
        return node


    def _find_in_node(self, src_node, node):
        pot_nodes = src_node.getElementsByTagName(node.nodeName)
        if len(pot_nodes) == 1: # the only one should be the searched
            return pot_nodes[0]
        for pot_node in pot_nodes:
            if pot_node.getAttribute('id') != node.getAttribute('id'):
                continue
            if pot_node.parentNode.nodeName != node.parentNode.nodeName:
                continue
            if pot_node.parentNode.nodeName != 'workflow' and \
                   pot_node.parentNode.getAttribute('id') != \
                   node.parentNode.getAttribute('id'):
                continue
            pot_node_items = self._filter_relevant_attrs(pot_node)
            node_items = self._filter_relevant_attrs(node)
            if pot_node_items != node_items:
                continue
            return pot_node

    def _compare_DOM_nodes(self, exp_node, got_node, wf_name,
                           documentElement=False):
#        print exp_node.getAttribute('id'),
        self.failIf(got_node is None,
                    "%s: %s(%s) missing in got DOM" % (
            wf_name, exp_node.nodeName, exp_node.attributes.items()))
        self.assertEqual(exp_node.nodeName, got_node.nodeName)
        if exp_node.nodeName != 'workflow':
            # workflow does not have compareable id
            self.assertEqual(exp_node.getAttribute('id'),
                             got_node.getAttribute('id'))
        if not documentElement:
            self.assertEqual(exp_node.parentNode.nodeName,
                             got_node.parentNode.nodeName)
            if exp_node.parentNode.nodeName != "workflow":
                # workflow does not have compareable id
                self.assertEqual(exp_node.parentNode.getAttribute('id'),
                                 got_node.parentNode.getAttribute('id'))

        exp_node_items = self._filter_relevant_attrs(exp_node)
        got_node_items = self._filter_relevant_attrs(got_node)
        self.assertEqual(exp_node_items,
                         got_node_items,
                         "%s:\nexp: %s\ngot: %s" % (wf_name,
                                                    exp_node_items,
                                                    got_node_items))

    def test_xml_import(self):
        self._create_test_users()
        self._import_wf()
        portal = self.portal
        alf = getToolByName(portal, "workflow_manager")
        test = alf.processes['test'].current()

    def test_activitygroup_import(self):
        self._import_wf('workflows/activitygroup.alf')
        test = self.portal.workflow_manager.processes['test'].current()
        self.assertEquals('foobar', test['edit'].group)

    def test_definition_(self):
        # Creates a simple workflow
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()

        wftool = getToolByName(portal, 'workflow_manager')

        # Create a new process definition
        wftool.processes["myProcess"] = Process('myProcess')
        wftool.processes["myProcess"].editable(ProcessVersion())
        wftool.processes["myProcess"].update()

        process = wftool.processes['myProcess'].current()

        process.setTitle("My demo process")
        process.setDescription("A process that demonstrates the new"
            "workflow tool")
        process.startActivity = ("write_document",)

        def add_activity(process, id, name):
            factory = zope.component.getUtility(IActivityClass, name=name)
            process[id] = factory()
            activity = process[id]
            activity.id = id
            return activity

        # "task" is a special kind of activity to ask people to do
        # something
        write_document = add_activity(process, "write_document", "ntask")
        cp_complete = ExitDefinition()
        cp_complete.activities = ("check_document", )
        cp_complete.id = "complete"
        write_document._setObject("complete", cp_complete)

        # "vote" is an activity, that asks people if something should
        # proceed or not
        check_document = add_activity(process, "check_document", "decision")
        check_document.decision_modus = 'all_yes'
        check_document.decision_notice = u'Decide something!'

        # Let's create some content
        portal.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = portal.testdocument
        # error on not existing process id
        self.assertRaises(AttributeError, doc.assignProcess, 'not existing processId')
        doc.assignProcess(wftool.processes['myProcess'].current())

        instance = doc.getInstance()

        instance.edit(write_document_assignees="author",
            write_document_task="Bitte eine" 
            "Pressemitteilung zum Thema Drogenpraevention 2004 schreiben",
            check_document_assignees=["editor1", "editor2"])

        controller = ILifeCycleController(instance)
        controller.start("testing")
        self.assertEquals(controller.state, "active")

        # Check for the correct error if an non-existing activity is created
        self.assertRaises(UnknownActivityError, instance.createWorkItems, ['nonexistent'], instance)

        wftool.processes["other_process"] = Process('other_process')
        wftool.processes["other_process"].editable(ProcessVersion())
        wftool.processes["other_process"].update()
        # If a process is already assigned, we can not assign another:
        self.assertRaises(Exception, doc.assignProcess,
                          wftool.processes['other_process'].current())
        new_instance = doc.getInstance()
        self.failUnless(instance.aq_base is new_instance.aq_base)

        self.login("author")
        write_document_wi = doc.getWorkItemsForCurrentUser()[0]
        # Test for instance.getWorkItems with optional activity_id parameter
        instance = doc.getInstance()
        self.assertEquals([], instance.getWorkItems(activity_id="michgibtsnich"))
        self.assertEquals([write_document_wi], 
                          instance.getWorkItems(activity_id="write_document"))

        write_document_wi.complete('complete')

        self.login("editor1")
        doc.getWorkItemsForCurrentUser()[0].accept()

        self.login("editor2")
        doc.getWorkItemsForCurrentUser()[0].accept()

        self.loginAsPortalOwner()
        self.assertEquals(0, len(instance.getWorkItems()))
        self.assertEquals(False, doc.hasInstanceAssigned())

    def test_get_process(self):
        # XXX This test might be superfluous.
        portal = self.portal
        alf = getToolByName(portal, 'workflow_manager')
        pid = get_random_id()
        alf.processes[pid] = Process(pid)
        process = alf.processes[pid]
        process.editable(ProcessVersion())
        process.update()
        current = process.current()
        self.assert_(IProcessVersion.providedBy(current))

    def test_grouped_schema(self):
        self._create_test_users()
        self._import_wf('workflows/multi_review.alf')
        portal = self.portal
        alf = getToolByName(portal, 'workflow_manager')
        portal.invokeFactory("DummyContent", "doc")
        doc = portal.doc
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        controller = ILifeCycleController(instance)
        controller.start('test')
        wis = instance.getWorkItems()
        self.assertEqual(1, len(wis))
        gs = wis[0].getGroupedSchema()
        act_ids_expected = ['write_document']
        act_ids_expected.sort()
        act_ids_got = [ g.activity_id for g in gs ]
        act_ids_got.sort()
        self.assertEquals(act_ids_expected, act_ids_got)
        self.assertEquals(gs[0].Title(), 'Dokument schreiben')

    def test_suitableprocs(self):
        self._create_test_users()
        self._import_wf()
        # we have one wf now
        portal = self.portal
        self.loginAsPortalOwner()
        portal.invokeFactory('DummyContent', 'doc')
        doc = portal.doc
        suitable = [s for s in doc.getSuitableProcesses()
                    if s.getId() == 'test']
        self.assertEquals(1, len(suitable))
        # test with user w/o reviewer or manager role
        self.login('author')
        suitable = [s for s in doc.getSuitableProcesses()
                    if s.process_ref.id == 'test']
        self.assertEquals(0, len(suitable))
        # test with user with *local* reviewer role
        doc.manage_addLocalRoles('author', ['Reviewer'])
        suitable = [s for s in doc.getSuitableProcesses()
                    if s.getId() == 'test']
        self.assertEquals(1, len(suitable))
        # test expression override
        portal.alf_suitable_processes = 'python:[]'
        doc.manage_addLocalRoles('author', ['Reviewer'])
        suitable = [s for s in doc.getSuitableProcesses()
                    if s.getId() == 'test']
        self.assertEquals(suitable, [])

    def test_getActionById(self):
        wi = DecisionWorkItem('asdf', 'pups')
        self.assertEqual(wi.getActionById('accept').id, 'accept')
        self.assertEqual(wi.getActionById('reject').id, 'reject')
        self.assertRaises(KeyError, wi.getActionById, 'asdf')

    def test_viewUrl_without_activity(self):
        # A decision work item that is attached to an activity that doesn't
        # exist anymore will return '' for the view URL.
        wi = DecisionWorkItem('asdf', 'pups')
        self.assertEquals('', wi.getViewUrl())

    def test_cache(self):
        zope.component.provideAdapter(LifeCycleControllerFactory,
                                      adapts=(WorkitemFake,),
                                      provides=ILifeCycleController)
        portal = self.portal
        portal.invokeFactory('DummyContent', 'doc1')
        doc1 = portal.doc1
        definition = ProcessDefinitionFake()
        i = Instance(definition, doc1, 'test')

        wi = WorkitemFake()
        ILifeCycleController(wi).state = 'active'
        i._setObject(wi.id, wi)
        wi = i._getOb(wi.id)
        i._update_cache(wi)
        self.assertEquals([wi], i.getWorkItems())

        ILifeCycleController(wi).state = 'complete'
        i._update_cache(wi)
        self.assertEquals([], i.getWorkItems())
        self.assertEquals([wi], i.getWorkItems('complete'))

    def test_rebuild_cache(self):
        zope.component.provideAdapter(LifeCycleControllerFactory,
                                      adapts=(WorkitemFake,), provides=ILifeCycleController)
        portal = self.portal
        portal.invokeFactory('DummyContent', 'doc1')
        doc1 = portal.doc1
        definition = ProcessDefinitionFake()
        i = Instance(definition, doc1, 'test')
        wi = WorkitemFake()
        ILifeCycleController(wi).state = 'active'
        i._setObject(wi.id, wi)
        wi = i._getOb(wi.id)

        # The cache doesn't know about it.
        self.assertEquals([], i.getWorkItems())

        # After rebuilding the cache, it does.
        i._rebuild_cache()
        self.assertEquals([wi], i.getWorkItems())

    def test_copy(self):
        # after copying an object should not have an instance assigned
        self._create_test_users()
        self._import_wf()
        portal = self.portal
        content = self.create(portal, 'DummyContent', 'doc1')
        transaction.savepoint()
        content.assignProcess(self.test_process)
        ILifeCycleController(content.getInstance()).start('test')
        self.assert_(content.hasInstanceAssigned())
        cb = portal.manage_copyObjects(['doc1'])
        result = portal.manage_pasteObjects(cb)
        new_id = result[0]['new_id']
        new_ob = getattr(portal, new_id)
        self.assert_(not new_ob.hasInstanceAssigned())

    def test_export_import(self):
        self.loginAsPortalOwner()
        self._create_test_users()
        self._import_wf()
        portal = self.portal
        alf = getToolByName(portal, 'workflow_manager')

        folder = self.create(portal, 'DummyFolder', 'f1')
        target_folder = self.create(portal, 'DummyFolder', 'f2')
        content = self.create(folder, 'DummyContent', 'doc1')

        folder.assignProcess(self.test_process)
        instance = folder.getInstance()
        ILifeCycleController(instance).start('test')
        transaction.savepoint()

        data = portal.manage_exportObject('f1', download=True)
        file_name = mktemp()
        try:
            file(file_name, 'wb').write(data)
            target_folder._importObjectFromFile(file_name)
        finally:
            try:
                os.remove(file_name)
            except IOError:
                pass

        imported = target_folder.f1

        # After an import, we still seem to have an instance assigned:
        self.failUnless(imported.hasInstanceAssigned())
        # This is wrong, as we didn't export/import the actual process
        # instance along.
        # Doing a sanity check turns out that this is an issue and resolve
        # it by removing the instance from the imported object:
        issues = alf.doSanityCheck()
        self.assertEquals(1, len(issues))
        self.assert_(not imported.hasInstanceAssigned())

    def test_contentretrieve(self):
        self.loginAsPortalOwner()
        self._create_test_users()
        self._import_wf()
        portal = self.portal

        fold = self.create(portal, 'DummyFolder', 'f1')
        doc = self.create(fold, 'DummyContent', 'doc1')
        doc.setTitle('gaaack')
        doc.reindexObject()
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start('testing')

        wi = instance.getWorkItems()[0]

        def check(ob):
            self.assertEquals(doc.absolute_url(), ob.getUrl())
            self.assertEquals(doc.getPhysicalPath(),
                              ob.getContentObjectPath())
            self.assertEquals(doc, ob.getContentObject())
            brain = ob.getContentObjectPortalCatalogBrain()
            self.assertEquals(doc.Title(), brain.Title)
            self.assertEquals(doc.absolute_url(), brain.getURL())

        check(instance)
        check(wi)

    def test_getviewurl(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/getviewurl.alf')
        portal = self.portal

        doc = self.create(portal, 'DummyContent', 'doc1')
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start('testing')

        wis = instance.getWorkItems()
        self.assertEquals(2, len(wis))

        this = wis[0]
        that = wis[1]
        if this.getActivity().getId() == 'do_that':
            this = wis[1]
            that = wis[0]

        self.assertEquals('%s/edit' % doc.absolute_url(), this.getViewUrl())
        self.assertEquals('%s/view' % doc.absolute_url(), that.getViewUrl())

    def test_instance_transaction(self):
        self.loginAsPortalOwner()
        portal = self.portal

        self._create_test_users()
        self._import_wf('workflows/instance_transaction.alf')
        alf = getToolByName(portal, 'workflow_manager')

        doc = self.create(portal, 'DummyContent', 'doc1')
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start('testing')
        wis = instance.getWorkItems()

        self.assertEquals(0, instance._creating)
        self.assertRaises(UnknownActivityError,
                          instance.createWorkItems, ['i-do-not-exist'], wis[0])
        self.assertEquals(0, instance._creating)

    def test_before_start(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/before_start.alf')
        portal = self.portal
        wftool = getToolByName(portal, 'workflow_manager')

        doc = self.create(portal, 'DummyContent', 'doc1')
        doc.before = 0
        doc.after = 0
        doc.expr_works = 0
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start('testing')

        self.assertEquals(1, doc.expr_works)
        self.assertEquals(1, doc.before)
        self.assertEquals(0, doc.after)
        self.assertEquals([],
                          wftool.processes['test'].current()['some-task'].graphGetStartActivities())
        self.assertEquals(1, len(instance.getWorkItems()))
        task = instance.getWorkItems()[0]
        self.assertEquals(1, len(task.objectValues()))
        task_start = task.objectValues()[0]
        self.assertEquals(1, len(task_start.objectValues()))
        task_start_expression = task_start.objectValues()[0]
        self.assert_(isinstance(
            task_start_expression,
            Products.AlphaFlow.aspects.expression.ExpressionAspect))

    def test_invalid_imports(self):
        importer = zope.component.getUtility(IWorkflowImporter, "xml")
        self.assertRaises(ValueError, importer, "/tmp/test.alf")

    def test_flexsplit(self):
        self.assertEquals(["a","b"], flexSplit("a,b"))
        self.assertEquals(["a","b","c"], flexSplit("a,b,c"))
        self.assertEquals(["a"], flexSplit("a"))
        self.assertEquals(["a", "b"], flexSplit("a b"))
        self.assertEquals(["a", "b", "c"], flexSplit("a b c"))
        self.assertEquals(["a"], flexSplit("a "))
        self.assertEquals(["a", "b", "c"], flexSplit("a,b c"))
        self.assertEquals(["a", "b", "c"], flexSplit("a, b ,c"))

    def test_restart(self):
        self.loginAsPortalOwner()
        self._import_wf('workflows/task.alf')
        portal = self.portal

        doc = self.create(portal, 'DummyContent', 'doc1')
        doc.assignProcess(self.test_process)
        instance = doc.getInstance()
        ILifeCycleController(instance).start('testing')

        # This was a bug that is explicitly tested for now
        self.failUnless(instance.aq_base is doc.getInstance().aq_base)
        ILifeCycleController(instance).reset('more testing')
        ILifeCycleController(instance).start('more testing')
        self.failUnless(instance.aq_base is doc.getInstance().aq_base)

    def test_invalid_permission(self):
        self.loginAsPortalOwner()
        self._import_wf("workflows/invalid_permission.alf", valid=False)
        alf = getToolByName(self.portal, "workflow_manager")
        test = alf.processes['test'].current()
        test.validate()
        self.assertEquals(2, len(test.validation_errors))
        self.assert_(test.validation_errors[1].endswith(
            "Field &quot;Permission&quot;: Constraint not satisfied"))

    def test_dcworkflow(self):
        # test that a workflow state set in manage_afterAdd is not in any way
        # modified by dcworkflow again
        self.loginAsPortalOwner()
        portal = self.portal
        self._import_wf('workflows/dcworkflow.alf')
        wftool = getToolByName(portal, 'portal_workflow')
        test_process = self.test_process

        def manage_afterAdd(self, item, container):
            DummyContent.inheritedAttribute('manage_afterAdd')(self, item,
                                                               container)
            if len(self.getAllInstances()) > 0:
                return
            self.assignProcess(test_process)
            ILifeCycleController(self.getInstance()).start("testing")

        DummyContent.manage_afterAdd = manage_afterAdd
        try:
            portal.invokeFactory('DummyContent', 'doc1')
            doc1 = portal.doc1

            # We expect the workflow state to be 'private' now.
            # alphaflow_fake's initial state is 'visible' though
            review_state = wftool.getStatusOf(
                'alphaflow_fake', doc1)['review_state']
            self.assertEquals('private', review_state)
        finally:
            del DummyContent.manage_afterAdd

    def test_fallout_startActivity(self):
        # test for fix of bug #2666
        self.loginAsPortalOwner()
        self._create_test_users()
        self._import_wf('workflows/fallout_startActivity.alf')

        doc1 = self.create(self.portal, 'DummyContent', 'doc1')
        doc1.assignProcess(self.test_process)
        instance = doc1.getInstance()
        controller = ILifeCycleController(instance)
        controller.start('test')
        self.assertEqual('failed', controller.state)
        fallout_workitems = instance.getWorkItems('failed')
        self.assertEqual(1, len(fallout_workitems))
        self.assertEqual('become_fallout', fallout_workitems[0].activity_id)

    def test_dcworkflow_source(self):
        binder = Products.AlphaFlow.sources.DCWorkflowStatusSource()
        source = binder(self.portal)
        self.assertEquals(sorted(['archived', 'visible', 'pending', 'private',
                                  'published']),
                          list(source))

    def test_groups_source(self):
        binder = Products.AlphaFlow.sources.GroupSource()
        source = binder(self.portal)
        self.assertEquals(['Administrators', 'Reviewers'], list(source))
        self.assertEquals(
            [u'Administrators', u'Reviewers'],
            [binder.factory.getTitle(self.portal, g) for g in source])

    def test_groups_source_unicode(self):
        # The groups' data is given in UTF-8. The source has to convert this.
        group = self.portal.portal_groups.getGroupById('Administrators')
        group.setProperties(title='T\xc3\xa4st')
        binder = Products.AlphaFlow.sources.GroupSource()
        source = binder(self.portal)
        self.assertEquals(['Reviewers', 'Administrators'], list(source))
        self.assertEquals(
            [u'Reviewers', u'T\xe4st'],
            [binder.factory.getTitle(self.portal, g) for g in source])

    def test_permission_source(self):
        binder = Products.AlphaFlow.sources.PermissionSource()
        source = binder(self.portal)
        result = list(source)
        self.failUnless('View' in result)
        self.failUnless('Access contents information' in result)

def convert_to_xml(value):
    """Convert a value to XML notation."""
    if isinstance(value, basestring):
        return value
    elif isinstance(value, tuple) or isinstance(value, list):
        return ' '.join(value)
    elif isinstance(value, bool):
        return value and 'true' or 'false'
    elif isinstance(value, int):
        return str(value)
    elif value is None:
        return ''
    raise ValueError, "Don't know how to handle '%s'." % value


def findAttrInAttributes(klass, classAttr):
    """Find classAttr in WorkflowAttributes of klass."""
    for attr in klass.attributes:
        if attr.classAttr == classAttr:
            return attr


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessDefinitionTest))
    return suite 
