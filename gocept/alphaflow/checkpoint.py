# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Checkpoints"""

from OFS.Folder import Folder
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

import zope.interface

import Products.AlphaFlow.interfaces
import Products.AlphaFlow.lifecycle
import Products.AlphaFlow.utils


class CheckpointDefinition(Folder):

    zope.interface.implements(
        Products.AlphaFlow.interfaces.ICheckpointDefinition)

    security = ClassSecurityInfo()

    id = None
    title = None

    _activities = ()
    # XXX?  Was ist _activity? das gleiche wie aq_parent?
    _activity = None

    schema_to_validate = Products.AlphaFlow.interfaces.ICheckpointDefinition

    # XXX? Warum diese Property?
    def __get_activities(self):
        return self._activities

    def __set_activities(self, value):
        self._activities = value

    activities = property(__get_activities, __set_activities)

    def __init__(self, activity=None, id=None, title=u""):
        self._activity = activity
        self.id = id
        self.title = title

    security.declarePrivate("validate")
    def validate(self):
        errors = Products.AlphaFlow.utils.validateFields(
            self.schema_to_validate, self)
        for aspect in self.objectValues():
            if Products.AlphaFlow.interfaces.IAspectDefinition.providedBy(
                aspect):
                errors.extend(aspect.validate())
            else:
                errors.append((self,
                               "A Checkpoint can only contain Aspects, "
                               "but found %r." % aspect))
        Products.AlphaFlow.utils.log_validation_errors(self, errors)
        return errors


InitializeClass(CheckpointDefinition)


class ExitDefinition(CheckpointDefinition):

    zope.interface.implements(Products.AlphaFlow.interfaces.IExitDefinition)

    schema_to_validate = Products.AlphaFlow.interfaces.IExitDefinition

    condition = u'python:True'

InitializeClass(ExitDefinition)


class Checkpoint(Products.AlphaFlow.lifecycle.LifeCycleObjectBase):

    portal_type = "Checkpoint"

    zope.interface.implements(
        zope.app.annotation.interfaces.IAttributeAnnotatable,
        Products.AlphaFlow.interfaces.ICheckpoint)

    alphaflow_type = "checkpoint"

    security = ClassSecurityInfo()

    manage_options = \
        ({'label' : 'Overview', 'action' : 'manage_overview'},) + \
        Products.AlphaFlow.lifecycle.LifeCycleObjectBase.manage_options

    log_name = "checkpoint"
    log_children_name = "aspects"

    generated_workitems = ()

    def __init__(self, definition, id):
        Checkpoint.inheritedAttribute("__init__")(self, id)
        self.definition = definition.getId()

    def getActivities(self):
        return self.getDefinition().activities

    def getDefinition(self):
        return self.aq_parent.getActivity()[self.definition]

    security.declarePrivate('onStart')
    def onStart(self):
        for aspect in self.getDefinition().objectValues():
            inst = self.createChild(aspect, "Aspect")
            controller = Products.AlphaFlow.interfaces.ILifeCycleController(
                inst)
            controller.start('Started by checkpoint.')
        self.generated_workitems = self.getWorkItem().createWorkItems(
            self.getActivities())
        Products.AlphaFlow.interfaces.ILifeCycleController(self).complete(
            'Completed all aspects.')


@zope.component.adapter(Products.AlphaFlow.interfaces.ICheckpoint,
                        Products.AlphaFlow.interfaces.ILifeCycleEvent)
def checkpoint_failed(checkpoint, event):
    # XXX tests
    cp_controller = Products.AlphaFlow.interfaces.ILifeCycleController(
        checkpoint)
    if cp_controller.state == 'failed':
        # Cascade the failure
        workitem = checkpoint.aq_inner.getParentNode()
        wi_controller = Products.AlphaFlow.interfaces.ILifeCycleController(
            workitem)
        wi_controller.fail("Checkpoint failed.")

InitializeClass(Checkpoint)
