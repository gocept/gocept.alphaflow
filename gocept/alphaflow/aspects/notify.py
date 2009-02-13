# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Implement the email aspect.
"""

import AccessControl
import Globals

import zope.interface

import Products.Archetypes.public

import Products.AlphaFlow.interfaces
import Products.AlphaFlow.config
import Products.AlphaFlow.aspect
from Products.AlphaFlow.aspects.interfaces import \
     IEMailAspectDefinition, IEMailAspect
import Products.AlphaFlow.activities.notify


class EMailAspectDefinition(Products.AlphaFlow.aspect.AspectDefinition):

    zope.interface.implements(IEMailAspectDefinition)
    zope.interface.classProvides(
        Products.AlphaFlow.interfaces.IAspectDefinitionClass)

    meta_type = "AlphaFlow EMail AspectDefinition"
    aspect_type = "email"
    icon = "misc_/AlphaFlow/email"

    recipient_modes = ()
    template = ""
    mailSubject = None

    schema_to_validate = IEMailAspectDefinition


Globals.InitializeClass(EMailAspectDefinition)


class EMailAspect(Products.AlphaFlow.aspect.Aspect):

    zope.interface.implements(IEMailAspect)

    security = AccessControl.ClassSecurityInfo()

    aspect_type  = "email"

    security.declarePrivate('__call__')
    def __call__(self):
        """Send email."""
        work_items = [self.getWorkItem()]
        Products.AlphaFlow.activities.notify._send_email(
            self, self.getDefinition(), work_items)


Globals.InitializeClass(EMailAspect)
Products.Archetypes.public.registerType(
    EMailAspect, Products.AlphaFlow.config.PROJECTNAME)
