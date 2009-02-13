# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Interfaces and schemas for the editor."""

import zope.interface
import zope.schema

import Products.AlphaFlow.sources
import Products.AlphaFlow.aspects.permission


class ISimpleRecipientSchema(zope.interface.Interface):
    """A very simplistic approach to allow editing of notification
    recipients.
    """

    owner = zope.schema.Choice(
        title=u"Email owner",
        source=Products.AlphaFlow.sources.BooleanSource())

    next = zope.schema.Choice(
        title=u"Email assignees of the next activities",
        source=Products.AlphaFlow.sources.BooleanSource())

    current = zope.schema.Choice(
        title=u"Email assignees of the current activity",
        source=Products.AlphaFlow.sources.BooleanSource())

    last = zope.schema.Choice(
        title=u"Email assignees of the last activities",
        source=Products.AlphaFlow.sources.BooleanSource())

    roles = zope.schema.Tuple(
      title=u"Email all users with roles",
      value_type=zope.schema.Choice(
        source=Products.AlphaFlow.sources.RoleSource()))


class IPermissionSettingEdit(Products.AlphaFlow.aspects.interfaces.IPermissionSetting):

    type = zope.schema.Choice(
        title=u"Type", 
        source=Products.AlphaFlow.aspects.permission.PermissionSettingSource())
