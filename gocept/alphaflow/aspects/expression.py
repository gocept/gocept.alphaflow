# Copyright (c) 2004-2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Execute a TALES expression -- aspect and definition."""

import zope.interface
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from gocept.alphaflow import config
from gocept.alphaflow.interfaces import IAspectDefinitionClass
from gocept.alphaflow.aspect import AspectDefinition, Aspect
from gocept.alphaflow.aspects.interfaces import \
    IExpressionAspectDefinition, IExpressionAspect
from gocept.alphaflow.activities.expression import evaluate_expression


class ExpressionAspectDefinition(AspectDefinition):

    zope.interface.implements(IExpressionAspectDefinition)
    zope.interface.classProvides(IAspectDefinitionClass)

    meta_type = "AlphaFlow Expression AspectDefinition"
    aspect_type = "expression"
    icon = "misc_/AlphaFlow/expression"

    expression = u"nothing"
    runAs = u"alphaflow/systemUser"

    schema_to_validate = IExpressionAspectDefinition


InitializeClass(ExpressionAspectDefinition)


class ExpressionAspect(Aspect):

    zope.interface.implements(IExpressionAspect)

    security = ClassSecurityInfo()

    aspect_type  = "expression"

    ######################
    # ITalesAspect

    security.declarePrivate('__call__')
    def __call__(self):
        """Evaluates the TALES expression."""
        evaluate_expression(self, self.getDefinition())


InitializeClass(ExpressionAspect)
registerType(ExpressionAspect, config.PROJECTNAME)
