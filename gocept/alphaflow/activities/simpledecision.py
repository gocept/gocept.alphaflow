# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Simple Decision activity and work item."""

import zope.interface
import zope.component
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from Products.Archetypes import public as atapi
from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.interfaces import \
    IActivityClass, IWorkItemClass, ILifeCycleController
from Products.AlphaFlow.activities.interfaces import \
    ISimpleDecisionActivity, IDecisionWorkItem, IWorkItemFactory
from Products.AlphaFlow.workitem import BaseAssignableWorkItem
from Products.AlphaFlow.activity import BaseAssignableActivity
from Products.AlphaFlow import config, utils
from Products.AlphaFlow.action import Action


class WorkItemFactory(object):

    zope.component.adapts(ISimpleDecisionActivity)
    zope.interface.implements(IWorkItemFactory)

    def __init__(self, activity):
        self.activity = activity

    def __call__(self, source, content_object=None):
        """Instantiates a SimpleDecisionWorkItem for every assignee."""
        assignees = self.activity._list_relevant_users(source)
        wis = []
        for assignee in assignees:
            w_id = utils.generateUniqueId('Workitem')
            wi = SimpleDecisionWorkItem(
                w_id, self.activity.getId(), content_object, assignee)
            wis.append(wi)
        return wis


class SimpleDecisionActivity(BaseAssignableActivity):
    """Decide to accept or reject.
    """

    zope.interface.implements(ISimpleDecisionActivity)
    zope.interface.classProvides(IActivityClass)

    security = ClassSecurityInfo()

    meta_type = 'AlphaFlow Simple Decision Activity'
    activity_type = 'simpledecision'
    icon = 'misc_/AlphaFlow/decision'

    decision_notice = None

    schema_to_validate = ISimpleDecisionActivity

    # configurationSchema gets modified by __init__!
    configurationSchema = BaseAssignableActivity.configurationSchema.copy()
    configurationSchema.get('assignees').widget = atapi.MultiSelectionWidget(
        label='Assigned users',
        description='Select one or more users who should decide the document',
        i18n_description='d_review',
        format='checkbox')

    def __init__(self):
        SimpleDecisionActivity.inheritedAttribute('__init__')(self)
        self._setExit('accept', u"If the answer is 'yes'...")
        self._setExit('reject', u"If the answer is 'no'...")

    security.declareProtected(config.MANAGE_WORKFLOW,
                              'graphGetPossibleChildren')
    def graphGetPossibleChildren(self):
        """Return a list of possible following activities. (List of ids)"""
        activities = super(DecisionActivity, self).graphGetPossibleChildren()
        for act in activities:
            if act["exit"] == "accept":
                act["color"] = "green"
            elif act["exit"] == "reject":
                act["color"] = "red"
        return activities

    def _list_relevant_users(self, source):
        #XXX duplicated code from activity.py, refactor!
        if self.assigneesKind == 'possible':
            relevant = source.getInstance().getActivityConfiguration("assignees",
                self.getId())
            if not isinstance(relevant, (list, tuple)):
                relevant = []
        else:
            if self.assigneesExpression is not None:
                relevant = utils.evaluateTales(self.assigneesExpression,
                                               activity=self,
                                               instance=source.getInstance())
                groupstool = getToolByName(self, "portal_groups")
                relevant = utils.expandGroups(groupstool, relevant)
            else:
                # we have roles
                roles = self.roles
                relevant = source.listMembersWithRolesOnContentObject(roles)
        return relevant


InitializeClass(SimpleDecisionActivity)


class SimpleDecisionWorkItem(BaseAssignableWorkItem):

    zope.interface.implements(IDecisionWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    activity_type  = "simpledecision"
    security = ClassSecurityInfo()

    def __init__(self, id, activity_id, content_object, assignee):
        SimpleDecisionWorkItem.inheritedAttribute('__init__')\
                (self, id, activity_id, content_object)
        self.assignee = assignee

    ###########
    # IWorkItem

    security.declareProtected(config.WORK_WITH_PROCESS, 'getActions')
    def getActions(self):
        """Determine all possible actions."""
        actions = [
            Action('accept',
                   u'Accept',
                   self.absolute_url(inner=True)+"/accept",
                   self.accept),
            Action('reject',
                   u'Reject',
                   self.absolute_url(inner=True)+"/reject",
                   self.reject),
        ]
        return actions

    def listRelevantUsers(self):
        """return the stored assignee"""
        return [self.assignee]

    ###################
    # IDecisionWorkItem

    security.declareProtected(config.HANDLE_WORKITEM, "reject")
    def reject(self, REQUEST=None):
        """Reject"""
        if self.state != "active":
            raise ValueError, "Can't reject when not active."
        self.passCheckpoint("reject")
        ILifeCycleController(self).complete("Rejected.")
        self.notifyAssigneesChange()
        self._update_ui_after_action('Rejected.', REQUEST)

    security.declareProtected(config.HANDLE_WORKITEM, "accept")
    def accept(self, REQUEST=None):
        """Accept"""
        if self.state != "active":
            raise ValueError, "Can't accept when not active."
        self.passCheckpoint("accept")
        ILifeCycleController(self).complete("Accepted.")
        self.notifyAssigneesChange()
        self._update_ui_after_action("Review registered.", REQUEST)

    security.declareProtected(config.WORK_WITH_PROCESS, 'getShortInfo')
    def getShortInfo(self):
        """Returns a short information text."""
        content = self.getContentObject()
        if content is None:
            info = "n/a"
        else:
            info = content.Title()


InitializeClass(SimpleDecisionWorkItem)
registerType(SimpleDecisionWorkItem, config.PROJECTNAME)
