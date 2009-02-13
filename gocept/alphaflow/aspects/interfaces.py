# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Interfaces specific to aspects.

"""

import zope.interface

from Products.AlphaFlow.interfaces import IAspectDefinition, IAspect
import Products.AlphaFlow.sources


class IExpressionAspectDefinition(IAspectDefinition):
    """Evaluate an expression.

    Expressions are run as TALES expressions and have the following contexts:

        aspect - the current aspect
        object - the object associated with this process
        definition - the definition for this aspect
        portal - the portal root object
    """

    expression = zope.schema.TextLine(
        default=u"nothing",
        title=u"TALES expression")

    runAs = zope.schema.TextLine(
        title=u"Run as user", 
        description=u"Give a TALES expression that evaluates to either a "
                     "username or a user object.",
        default=u"alphaflow/systemUser")


class IExpressionAspect(IAspect):
    """expression aspect"""


class IEMailAspectDefinition(IAspectDefinition):
    """Sends an email to certain interested users about activities in
    this workflow.
    """

    recipient_modes = zope.schema.Tuple(
        title=u"Possible recipients, provide IEMailRecipientMode")

    mailSubject = zope.schema.TextLine(title=u"Subject")

    template = zope.schema.Choice(
        title=u"Message",
        source=Products.AlphaFlow.sources.EmailTemplateSource())


class IEMailAspect(IAspect):
    """Implements the sending of the email."""


class IParentAspectDefinition(IAspectDefinition):
    """continue with parent of a certain activity"""

    parentOf = zope.schema.Choice(
        title=u"Start parent of ...",
        description=u"This aspect will start the activity that is"
                    u"is the parent of the activity you select here.",
        source=Products.AlphaFlow.sources.ActivitySource())


class IParentAspect(IAspect):
    """continue with parent of a certain activity"""


class IPermissionSetting(zope.interface.Interface):
    """A permission change setting information."""

    def apply(content):
        """Apply the permission setting on the content object."""

    permission = zope.schema.Choice(
        title=u"Permission",
        description=u"The permission that should be changed.",
        source=Products.AlphaFlow.sources.PermissionSource())

    roles = zope.schema.Tuple(
        required=False,
        title=u"Roles",
        description=u"Apply the change to these roles.",
        value_type=zope.schema.Choice(
            source=Products.AlphaFlow.sources.RoleSource()))

    acquire = zope.schema.Choice(
        title=u"Inherit allowed roles from the portal",
        source=Products.AlphaFlow.sources.BooleanSource(),
        required=False)


class IPermissionAspectDefinition(IAspectDefinition):
    """Modifies the permission configuration of the associated object.

    Permissions are stored as folder items below the aspect.

    """


class IPermissionAspect(IAspect):
    """Implements the permission change"""


class IDCWorkflowAspectDefinition(IAspectDefinition):
    """simulates the DC Workflow Changes the state on a document to a "DC
       Workflow compatible" state
    """

    status = zope.schema.Choice(
        title=u"Workflow status",
        source=Products.AlphaFlow.sources.DCWorkflowStatusSource())


class IDCWorkflowAspect(IAspect):
    """Aspect simulating DC Workflow state changes"""
