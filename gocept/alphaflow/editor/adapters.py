# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Adapters for the editor."""

import zope.interface

import Products.AlphaFlow.editor.interfaces
import Products.AlphaFlow.activities.notify

import Acquisition


def mode_property(cls):
    """Generates a property that

        - when read, determines whether a recipient mode specified by <cls> 
          is selected
        - when set, updates the recipient_modes list by removing or adding
          the mode specified by <cls>

    """
    def _get_recipient(self):
        for x in self.context.recipient_modes:
            if isinstance( x, cls):
              return True
        return False
    def _set_recipient(self, value):
        if value == _get_recipient(self):
            # This case is kind of implicitly handled by the formlib. I catch
            # it here anyway to make the algorithm a bit more obvious.
            return
        if value:
            self.context.recipient_modes += (cls(),)
        else:
            self.context.recipient_modes = tuple(
              mode for mode in self.context.recipient_modes 
                if not isinstance(mode, cls))
    return property(fget=_get_recipient, fset=_set_recipient)

def create_wrapped_recipient_schema(context):
    srs = SimpleRecipientSchema(context)
    return srs.__of__(context)

class SimpleRecipientSchema(Acquisition.Implicit):

    zope.interface.implements(Products.AlphaFlow.editor.interfaces.ISimpleRecipientSchema)

    def __init__(self, context):
        self.context = context

    owner = mode_property(Products.AlphaFlow.activities.notify.RecipientOwner)
    next = mode_property(
        Products.AlphaFlow.activities.notify.RecipientNextAssignees)
    current = mode_property(
        Products.AlphaFlow.activities.notify.RecipientCurrentAssignees)
    last = mode_property(
        Products.AlphaFlow.activities.notify.RecipientPreviousAssignees)

    def _get_roles(self):
        for x in self.context.recipient_modes:
            if isinstance(x,
                          Products.AlphaFlow.activities.notify.RecipientActualRole):
              return tuple(x.roles)
        return ()
    def _set_roles(self, value):
        if value == self._get_roles():
            # This case is kind of implicitly handled by the formlib. I catch
            # it here anyway to make the algorithm a bit more obvious.
            return
        # Remove the old recipients mode(s) first
        self.context.recipient_modes = tuple(
            mode for mode in self.context.recipient_modes 
            if not isinstance(
                mode, Products.AlphaFlow.activities.notify.RecipientActualRole))
        # If we don't have roles, we can stop now
        if not value:
            return
        # Add a new recipient mode and set the `roles` attribute
        mode = Products.AlphaFlow.activities.notify.RecipientActualRole()
        mode.roles = value
        self.context.recipient_modes += (mode,)
    roles = property(fget=_get_roles, fset=_set_roles)


class PermissionSettingEdit(Acquisition.Implicit):

    zope.interface.implements(
        Products.AlphaFlow.editor.interfaces.IPermissionSettingEdit)

    def __init__(self, context):
        self.context = context

    def _get_type(self):
        return self.context.__class__
    def _set_type(self, value):
        if value == self.context.__class__:
            return
        new_context = value(self.context.permission,
                            self.context.roles,
                            self.context.acquire)
        new_context.id = self.context.id
        permission_aspect = self.context.aq_inner.getParentNode()
        permission_aspect.manage_delObjects([new_context.id])
        permission_aspect[new_context.id] = new_context
        self.context = new_context
    type = property(fget=_get_type, fset=_set_type)

    def _get_roles(self):
        return self.context.roles
    def _set_roles(self, value):
        self.context.roles = value
    roles = property(fget=_get_roles, fset=_set_roles)

    def _get_permission(self):
        return self.context.permission
    def _set_permission(self, value):
        self.context.permission = value
    permission = property(fget=_get_permission, fset=_set_permission)

    def _get_acquire(self):
        return self.context.acquire
    def _set_acquire(self, value):
        self.context.acquire = value
    acquire = property(fget=_get_acquire, fset=_set_acquire)
