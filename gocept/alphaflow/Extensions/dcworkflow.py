# -*- coding: latin1 -*-
# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$


from Products.DCWorkflow.DCWorkflow import DCWorkflowDefinition
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowTool import addWorkflowFactory


_registered_workflows = []

def register(id, factory):
    """register workflow

    >>> from Products.AlphaFlow.Extensions import dcworkflow
    >>> def fac():
    ...     return dcworkflow.create('wf')
    >>> dcworkflow.register('wf', fac)

    """
    def workflow_factory(workflow_id):
        if workflow_id != id:
            raise ValueError, "Id mismatch %r != %r" % (
                id, workflow_id)
        return factory()

    _registered_workflows.append(id)
    addWorkflowFactory(workflow_factory, id)


def install(portal, workflow_id):
    """install workflow with given id

    >>> from Products.AlphaFlow.Extensions import dcworkflow
    >>> def fac():
    ...     return dcworkflow.create('wf')
    >>> dcworkflow.register('wf', fac)

    The id is 'wf', let's install it. 

    >>> dcworkflow.install(self.portal, 'wf')
    >>> 'wf' in self.portal.portal_workflow.getWorkflowIds()
    True

    We have not registerd simple, so we fail with ValueError:
    >>> dcworkflow.install(self.portal, 'simple')  # doctest +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ValueError: 'simple'

    """
    portal_workflow = getToolByName(portal, 'portal_workflow')
    try:
        portal_workflow.manage_addWorkflow(workflow_id, workflow_id)
    except KeyError, e:
        raise ValueError, e


def installAllWorkflows(portal):
    """install all workflows in portal which have been registered
 
    Register some workflows, and check they are not installed yet.

    >>> from Products.AlphaFlow.Extensions import dcworkflow
    >>> from Products.CMFCore.utils import getToolByName
    >>> dcworkflow._clean_registry()
    >>> def faca():
    ...     return dcworkflow.create('wfa')
    >>> dcworkflow.register('wfa', faca)
    >>> def facb():
    ...     return dcworkflow.create('wfb')
    >>> dcworkflow.register('wfb', facb)
    >>> portal_workflow = getToolByName(self.portal, 'portal_workflow')
    >>> 'wfa' in portal_workflow.getWorkflowIds()
    False
    >>> 'wfb' in portal_workflow.getWorkflowIds()
    False

    Now install the workflows:

    >>> dcworkflow.installAllWorkflows(self.portal)
    >>> 'wfa' in portal_workflow.getWorkflowIds()
    True
    >>> 'wfb' in portal_workflow.getWorkflowIds()
    True

    """
    for wf_id in _registered_workflows:
        install(portal, wf_id)


def create(workflow_id):
    """create a workflow

    >>> from Products.AlphaFlow.Extensions import dcworkflow
    >>> wf = dcworkflow.create('simple')
    >>> wf.getId()
    'simple'

    >>> wf = dcworkflow.create('complex')
    >>> wf.getId()
    'complex'
    """
    ob = DCWorkflowDefinition(workflow_id)
    return ob

def setupCore(wf, title, states, transitions):
    """Setup common parts of a workflow.

    setupCore just adds the states you specify:

    >>> from Products.AlphaFlow.Extensions import dcworkflow
    >>> wf = dcworkflow.create('a')
    >>> dcworkflow.setupCore(wf, 'mytitle', ['state1', 'state2', 'state3'],
    ...           transitions=['s1_s2', 's1_s3'])
    >>> wf.states['state1']
    <StateDefinition at a/states/state1>
    >>> wf.states['state2']
    <StateDefinition at a/states/state2>
    >>> wf.states['state3']
    <StateDefinition at a/states/state3>
    >>> wf.transitions['s1_s2']
    <TransitionDefinition at a/transitions/s1_s2>
    >>> wf.transitions['s1_s3']
    <TransitionDefinition at a/transitions/s1_s3>
    """ 
    wf.title = title
    for state in states:
        wf.states.addState(state)
    for transition in transitions:
        wf.transitions.addTransition(transition)

    for v in ['review_history', 'comments', 'time', 'actor', 'action']:
        wf.variables.addVariable(v)

    wf.variables.setStateVar('review_state')

    # we need all those variables, some only for compatibility
    vdef = wf.variables['review_history']
    vdef.setProperties(description="""Provides access to workflow history""",
                       default_value="""""",
                       default_expr="""state_change/getHistory""",
                       for_catalog=0,
                       for_status=0,
                       update_always=0,
                       props={'guard_permissions':
                              'Request review; Review portal content'})

    vdef = wf.variables['comments']
    vdef.setProperties(description="""Comments about the last transition""",
                       default_value="""""",
                       default_expr="""python:state_change.kwargs.get('comment', '')""",
                       for_catalog=0,
                       for_status=1,
                       update_always=1,
                       props=None)

    vdef = wf.variables['time']
    vdef.setProperties(description="""Time of the last transition""",
                       default_value="""""",
                       default_expr="""state_change/getDateTime""",
                       for_catalog=0,
                       for_status=1,
                       update_always=1,
                       props=None)

    vdef = wf.variables['actor']
    vdef.setProperties(description="""The ID of the user who performed the last transition""",
                       default_value="""""",
                       default_expr="""user/getUserName""",
                       for_catalog=0,
                       for_status=1,
                       update_always=1,
                       props=None)

    vdef = wf.variables['action']
    vdef.setProperties(description="""The last transition""",
                       default_value="""""",
                       default_expr="""transition/getId|nothing""",
                       for_catalog=0,
                       for_status=1,
                       update_always=1,
                       props=None)


# private helpers
def _clean_registry():
    # clean registry from workflows -- mainly used in tests
    del _registered_workflows[:]
