# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Implement the email aspect.
"""

import AccessControl
import Globals

import zope.interface

import Products.Archetypes.public

import gocept.alphaflow.interfaces
import gocept.alphaflow.config
import gocept.alphaflow.aspect
from gocept.alphaflow.aspects.interfaces import \
     IEMailAspectDefinition, IEMailAspect
import gocept.alphaflow.activities.notify


class EMailAspectDefinition(gocept.alphaflow.aspect.AspectDefinition):

    zope.interface.implements(IEMailAspectDefinition)
    zope.interface.classProvides(
        gocept.alphaflow.interfaces.IAspectDefinitionClass)

    meta_type = "AlphaFlow EMail AspectDefinition"
    aspect_type = "email"
    icon = "misc_/AlphaFlow/email"

    recipient_modes = ()
    template = ""
    mailSubject = None

    schema_to_validate = IEMailAspectDefinition


Globals.InitializeClass(EMailAspectDefinition)


class EMailAspect(gocept.alphaflow.aspect.Aspect):

    zope.interface.implements(IEMailAspect)

    security = AccessControl.ClassSecurityInfo()

    aspect_type  = "email"

    security.declarePrivate('__call__')
    def __call__(self):
        """Send email."""
        work_items = [self.getWorkItem()]
        gocept.alphaflow.activities.notify._send_email(
            self, self.getDefinition(), work_items)


Globals.InitializeClass(EMailAspect)
Products.Archetypes.public.registerType(
    EMailAspect, gocept.alphaflow.config.PROJECTNAME)
