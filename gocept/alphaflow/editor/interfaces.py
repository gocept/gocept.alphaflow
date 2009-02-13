# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Interfaces and schemas for the editor."""

import zope.interface
import zope.schema

import gocept.alphaflow.sources
import gocept.alphaflow.aspects.permission


class ISimpleRecipientSchema(zope.interface.Interface):
    """A very simplistic approach to allow editing of notification
    recipients.
    """

    owner = zope.schema.Choice(
        title=u"Email owner",
        source=gocept.alphaflow.sources.BooleanSource())

    next = zope.schema.Choice(
        title=u"Email assignees of the next activities",
        source=gocept.alphaflow.sources.BooleanSource())

    current = zope.schema.Choice(
        title=u"Email assignees of the current activity",
        source=gocept.alphaflow.sources.BooleanSource())

    last = zope.schema.Choice(
        title=u"Email assignees of the last activities",
        source=gocept.alphaflow.sources.BooleanSource())

    roles = zope.schema.Tuple(
      title=u"Email all users with roles",
      value_type=zope.schema.Choice(
        source=gocept.alphaflow.sources.RoleSource()))


class IPermissionSettingEdit(gocept.alphaflow.aspects.interfaces.IPermissionSetting):

    type = zope.schema.Choice(
        title=u"Type", 
        source=gocept.alphaflow.aspects.permission.PermissionSettingSource())
