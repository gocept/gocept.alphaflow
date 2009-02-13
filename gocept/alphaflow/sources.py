# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Source definitions."""

import Products.CMFCore.utils

import zc.sourcefactory.contextual
import zc.sourcefactory.basic


class BooleanSource(zc.sourcefactory.basic.BasicSourceFactory):
    """A source for selecting true/false."""

    def getValues(self):
        return [True, False]

    def getTitle(self, value):
        if value:
            return u"Yes"
        return u"No"


class PossibleActivitiesSource(
    zc.sourcefactory.contextual.BasicContextualSourceFactory):
    """This source lists all activities that can be created within the context
    of a process.
    """

    def getValues(self, context):
        # We get back a list of tuples with (name, utility)
        return [x[1] for x in context.listPossibleActivities()]

    def getToken(self, context, value):
        for name, activity in context.listPossibleActivities():
            if activity is value:
                return name

    getTitle = getToken


class ActivitySource(
    zc.sourcefactory.contextual.BasicContextualSourceFactory):
    """This source lists all activities that were created within the context 
    of a process.
    """

    def getValues(self, context):
        process = context.acquireProcess()
        activities = process.objectValues()
        activities.sort(key=lambda x:x.title_or_id())
        return [x.getId() for x in activities]

    def getTitle(self, context, value):
        process = context.acquireProcess()
        try:
            return process[value].title or value
        except KeyError:
            return value


class GateSource(ActivitySource):

    def getValues(self, context):
        values = super(GateSource, self).getValues(context)
        process = context.acquireProcess()
        return [activity for activity in values if
            Products.AlphaFlow.activities.interfaces.IGateActivity.
                providedBy(process[activity])]


class EmailTemplateSource(

    zc.sourcefactory.contextual.BasicContextualSourceFactory):
    """This source lists all email templates."""

    def getValues(self, context):
        pm = Products.CMFCore.utils.getToolByName(context, 'workflow_manager')
        return pm.email_templates.objectIds()

    def getTitle(self, context, value):
        pm = Products.CMFCore.utils.getToolByName(context, 'workflow_manager')
        return pm.email_templates[value].title_or_id()


class RoleSource(
    zc.sourcefactory.contextual.BasicContextualSourceFactory):
    """This source returns all roles available in the portal.
    """

    title = "Plone roles"

    def getValues(self, context):
        portal = Products.CMFCore.utils.getToolByName(
            context, "portal_url").getPortalObject()
        return portal.valid_roles()


class GroupSource(
    zc.sourcefactory.contextual.BasicContextualSourceFactory):
    """This source returns all groups available in the portal.
    """

    title = "Plone roles"

    def getValues(self, context):
        gt = Products.CMFCore.utils.getToolByName(context, "portal_groups")
        groups = gt.listGroupIds()
        groups.sort(key=lambda x:self.getTitle(context, x))
        return groups

    def getTitle(self, context, value):
        gt = Products.CMFCore.utils.getToolByName(context, "portal_groups")
        group = gt.getGroupById(value)
        if group is None:
            title = value
        else:
            title = group.getGroupTitleOrName()
        return title.decode('utf-8')


class PermissionSource(
    zc.sourcefactory.contextual.BasicContextualSourceFactory):
    """This source returns all permissions available in the portal.
    """

    title = "Zope permissions"

    def getValues(self, context):
        root = Products.CMFCore.utils.getToolByName(
            context, "portal_url").getPortalObject()
        return [x['name'] for x in root.permission_settings()]


class DCWorkflowStatusSource(
    zc.sourcefactory.contextual.BasicContextualSourceFactory):
    """This source returns all dc workflow status as configured
    for the alphaflow_fake workflow.

    """

    def getValues(self, context):
        wf = Products.CMFCore.utils.getToolByName(context, "portal_workflow")
        return sorted(wf['alphaflow_fake'].states.objectIds())
