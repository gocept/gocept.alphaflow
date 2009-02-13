# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Aspect and their definitions."""

import OFS.SimpleItem
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

import zope.interface
import zope.app.annotation.interfaces

import gocept.alphaflow.interfaces
import gocept.alphaflow.lifecycle
import gocept.alphaflow.utils
import gocept.alphaflow.config


class AspectDefinition(OFS.SimpleItem.SimpleItem):

    zope.interface.implements(gocept.alphaflow.interfaces.IAspectDefinition)

    sortPriority = 0
    nonEditableFields = ()
    title = u""
    commentfield = ""

    security = ClassSecurityInfo()

    schema_to_validate = gocept.alphaflow.interfaces.IAspectDefinition

    security.declarePrivate("validate")
    def validate(self):
        errors = gocept.alphaflow.utils.validateFields(
            self.schema_to_validate, self)
        gocept.alphaflow.utils.log_validation_errors(self, errors)
        return errors

    def graphGetPossibleChildren(self):
        return []


InitializeClass(AspectDefinition)


class Aspect(gocept.alphaflow.utils.ContentObjectRetrieverBase,
             gocept.alphaflow.lifecycle.LifeCycleObjectBase):

    zope.interface.implements(
        gocept.alphaflow.interfaces.IAspect,
        zope.app.annotation.interfaces.IAttributeAnnotatable)

    alphaflow_type = "aspect"

    security = ClassSecurityInfo()

    id = None
    title = ""

    definition = None

    manage_options = \
        ({'label' : 'Overview', 'action' : 'manage_overview'},) + \
        gocept.alphaflow.lifecycle.LifeCycleObjectBase.manage_options

    def __init__(self, definition, id):
        Aspect.inheritedAttribute("__init__")(self, id)
        self.definition = definition.getId()

    def getDefinition(self):
        return self.aq_parent.getDefinition()[self.definition]

    def __call__(self):
        pass

    def onStart(self):
        Aspect.inheritedAttribute("onStart")(self)
        controller = gocept.alphaflow.interfaces.ILifeCycleController(self)
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
    security.declareProtected(gocept.alphaflow.config.WORK_WITH_PROCESS,
                              'getContentObject')
    def getContentObject(self):
        instance = self.getInstance()
        return instance.getContentObject()

    security.declareProtected(gocept.alphaflow.config.WORK_WITH_PROCESS,
                              'getContentObjectUID')
    def getContentObjectUID(self):
        instance = self.getInstance()
        return instance.getContentObjectUID()


@zope.component.adapter(gocept.alphaflow.interfaces.IAspect,
                        gocept.alphaflow.interfaces.ILifeCycleEvent)
def aspect_failed(aspect, event):
    aspect_controller = gocept.alphaflow.interfaces.ILifeCycleController(
        aspect)
    if aspect_controller.state == 'failed':
        checkpoint = aspect.aq_inner.getParentNode()
        cp_controller = gocept.alphaflow.interfaces.ILifeCycleController(
            checkpoint)
        cp_controller.fail("Aspect failed.")

InitializeClass(Aspect)
