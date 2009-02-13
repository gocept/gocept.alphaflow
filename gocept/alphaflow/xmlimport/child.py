# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Descriptors for importing checkpoints and activity exits."""


import Products.AlphaFlow.interfaces
import Products.AlphaFlow.exception
import Products.AlphaFlow.checkpoint
import Products.AlphaFlow.xmlimport.utils


class CheckpointFromNode(object):

    id = None
    node_name = None

    def factory(self, activity):
        return Products.AlphaFlow.checkpoint.CheckpointDefinition()

    def __init__(self, node_name, id=None):
        self.node_name = node_name
        self.id = id or node_name

    def apply(self, node, activity):
        checkpoint = getattr(activity, self.id, None)
        children = Products.AlphaFlow.xmlimport.utils.import_child_elements(
            node, activity, (self.node_name,), default=checkpoint)

        if len(children) > 1:
            raise Products.AlphaFlow.exception.ConfigurationError(
                "Only one child element %s allowed for element %s." %
                (self.node_name, node.nodeName))

        if not checkpoint:
            if children:
                checkpoint = children[0]
            else:
                checkpoint = self.factory(activity)
            activity._setObject(self.id, checkpoint)

        activity[self.id].id = self.id


class ExitFromNode(CheckpointFromNode):

    def factory(self, activity):
        return Products.AlphaFlow.interfaces.IExitDefinition(activity)


class MultipleExitsFromNodes(ExitFromNode):

    def apply(self, node, activity):
        for child in Products.AlphaFlow.xmlimport.utils.import_child_elements(
            node, activity, (self.node_name,)):
            if not child.id:
                raise Products.AlphaFlow.exception.ConfigurationError(
                    "Element %s must have an ID." % self.node_name)

            activity._setObject(child.getId(), child)
