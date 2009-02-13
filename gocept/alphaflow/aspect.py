# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Aspect and their definitions."""

import OFS.SimpleItem
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

import zope.interface
import zope.app.annotation.interfaces

import Products.AlphaFlow.interfaces
import Products.AlphaFlow.lifecycle
import Products.AlphaFlow.utils
import Products.AlphaFlow.config


class AspectDefinition(OFS.SimpleItem.SimpleItem):

    zope.interface.implements(Products.AlphaFlow.interfaces.IAspectDefinition)

    sortPriority = 0
    nonEditableFields = ()
    title = u""
    commentfield = ""

    security = ClassSecurityInfo()

    schema_to_validate = Products.AlphaFlow.interfaces.IAspectDefinition

    security.declarePrivate("validate")
    def validate(self):
        errors = Products.AlphaFlow.utils.validateFields(
            self.schema_to_validate, self)
        Products.AlphaFlow.utils.log_validation_errors(self, errors)
        return errors

    def graphGetPossibleChildren(self):
        return []


InitializeClass(AspectDefinition)


class Aspect(Products.AlphaFlow.utils.ContentObjectRetrieverBase,
             Products.AlphaFlow.lifecycle.LifeCycleObjectBase):

    zope.interface.implements(
        Products.AlphaFlow.interfaces.IAspect,
        zope.app.annotation.interfaces.IAttributeAnnotatable)

    alphaflow_type = "aspect"

    security = ClassSecurityInfo()

    id = None
    title = ""

    definition = None

    manage_options = \
        ({'label' : 'Overview', 'action' : 'manage_overview'},) + \
        Products.AlphaFlow.lifecycle.LifeCycleObjectBase.manage_options

    def __init__(self, definition, id):
        Aspect.inheritedAttribute("__init__")(self, id)
        self.definition = definition.getId()

    def getDefinition(self):
        return self.aq_parent.getDefinition()[self.definition]

    def __call__(self):
        pass

    def onStart(self):
        Aspect.inheritedAttribute("onStart")(self)
        controller = Products.AlphaFlow.interfaces.ILifeCycleController(self)
        try:
            self.__call__()
        except Exception, m:
            # XXX Test needed
            controller.fail("Aspect failed.", m)
        else:
            controller.complete("Completed aspect.")

    #########################
    # IContentObjectRetriever

    # Force acquisition of getContentObject by context instead of containment
    security.declareProtected(Products.AlphaFlow.config.WORK_WITH_PROCESS,
                              'getContentObject')
    def getContentObject(self):
        instance = self.getInstance()
        return instance.getContentObject()

    security.declareProtected(Products.AlphaFlow.config.WORK_WITH_PROCESS,
                              'getContentObjectUID')
    def getContentObjectUID(self):
        instance = self.getInstance()
        return instance.getContentObjectUID()


@zope.component.adapter(Products.AlphaFlow.interfaces.IAspect,
                        Products.AlphaFlow.interfaces.ILifeCycleEvent)
def aspect_failed(aspect, event):
    aspect_controller = Products.AlphaFlow.interfaces.ILifeCycleController(
        aspect)
    if aspect_controller.state == 'failed':
        checkpoint = aspect.aq_inner.getParentNode()
        cp_controller = Products.AlphaFlow.interfaces.ILifeCycleController(
            checkpoint)
        cp_controller.fail("Aspect failed.")

InitializeClass(Aspect)
