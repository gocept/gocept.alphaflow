# Copyright (c) 2004-2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

"""Emulate the DCWorkFlow status interface."""

from DateTime import DateTime

import zope.interface 
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from Products.AlphaFlow import config
from Products.AlphaFlow.aspect import AspectDefinition, Aspect
from Products.AlphaFlow.interfaces import IAspectDefinitionClass
from Products.AlphaFlow.aspects.interfaces import IDCWorkflowAspectDefinition


class WorkflowHistoryFake(dict):

    def __setitem__(self, key, value):
        if key != "alphaflow_fake":
            super(WorkflowHistoryFake, self).__setitem__(key, value)

    def set(self, key, value):
        super(WorkflowHistoryFake, self).__setitem__(key, value)


class DCWorkflowAspectDefinition(AspectDefinition):

    zope.interface.implements(IDCWorkflowAspectDefinition)
    zope.interface.classProvides(IAspectDefinitionClass)

    meta_type = "AlphaFlow DCWorkflow AspectDefinition"
    aspect_type = "dcworkflow"
    icon = "misc_/AlphaFlow/dcworkflow"

    schema_to_validate = IDCWorkflowAspectDefinition

    status = None


InitializeClass(DCWorkflowAspectDefinition)


class DCWorkflowAspect(Aspect):

    security = ClassSecurityInfo()

    aspect_type  = "dcworkflow"

    security.declarePrivate("__call__")
    def __call__(self):
        ob = self.getContentObject()
        definition = self.getDefinition()
        wfh = getattr(ob, "workflow_history", {})
        if type(wfh) is not WorkflowHistoryFake:
            wfh = ob.workflow_history = WorkflowHistoryFake(wfh)
            wfh["alphaflow_fake"] = ()
        affh = list(wfh.get("alphaflow_fake", ()))
        affh.append({
                "review_state": definition.status,
                "action": definition.title,
                "time": DateTime(),
                })
        wfh.set("alphaflow_fake", tuple(affh))
        ob.aq_inner.reindexObject(idxs=['review_state'])


InitializeClass(DCWorkflowAspect)
registerType(DCWorkflowAspect, config.PROJECTNAME)
