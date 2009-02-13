# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""parent aspect continues with parent of given activity

The parent aspect is good to use if you have a block of activities (for
instance escalation, error handling, etc) which is reachable from various
points from within the workflow. After handling the escalation, error etc the
workflow can continue exactly where the error occoured in the first place.

"""
import zope.interface
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

import Products.AlphaFlow.interfaces
from Products.AlphaFlow import config
from Products.AlphaFlow.aspect import AspectDefinition, Aspect
from Products.AlphaFlow.interfaces import IAspectDefinitionClass
from Products.AlphaFlow.aspects.interfaces import \
    IParentAspectDefinition, IParentAspect


class ParentAspectDefinition(AspectDefinition):

    zope.interface.implements(IParentAspectDefinition)
    zope.interface.classProvides(IAspectDefinitionClass)

    security = ClassSecurityInfo()

    meta_type = "AlphaFlow Parent AspectDefinition"
    activity_type = "parent"

    parentOf = None

    schema_to_validate = IParentAspectDefinition

    def graphGetPossibleChildren(self):
        # XXX make activity lookup an adapter
        activity = self.getParentNode().getParentNode()
        assert Products.AlphaFlow.interfaces.IActivity.providedBy(activity)
        if activity.getId() != self.parentOf:
            children = [{'id': self.parentOf,
                         'exit': 'parent',
                         'qualifier': 'parent',
                         'label': 'parent of'}]
        else:
            # Don't display a reference to the parent if it's the same activity
            # that defines the aspect.
            children = []
        return children


InitializeClass(ParentAspectDefinition)


class ParentAspect(Aspect):

    zope.interface.implements(IParentAspect)

    security = ClassSecurityInfo()

    activity_type  = "parent"

    security.declarePrivate('__call__')
    def __call__(self):
        "Trigger that gets called after the workitem has been started."
        parent = self.getWorkItem()
        my_activity = parent.getActivity()
        parent_name = self.getDefinition().parentOf

        while parent.activity_id != parent_name:
            parent = parent.getParent()
            if parent is None:
                raise AlphaFlowException(
                    'Could not find %r activity within parents' % parent_name)

        continue_with = parent.getParent()
        if continue_with is None:
            raise AlphaFlowException(
                'Activity %r does not have a parent' % parent)

        self.getWorkItem().createWorkItems((continue_with.activity_id,))


InitializeClass(ParentAspect)
registerType(ParentAspect, config.PROJECTNAME)
