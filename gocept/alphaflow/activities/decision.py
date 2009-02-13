# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Decision activity and work item."""

import zope.interface
from AccessControl import ClassSecurityInfo, getSecurityManager
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from Products.Archetypes import public as atapi

import Products.AlphaFlow.workitem
from Products.AlphaFlow.interfaces import \
    IActivityClass, IWorkItemClass, ILifeCycleController
from Products.AlphaFlow.activities.interfaces import \
    IDecisionActivity, IDecisionWorkItem, ILifeCycleController
from Products.AlphaFlow.workitem import BaseAssignableWorkItem
from Products.AlphaFlow.activity import BaseAssignableActivity
from Products.AlphaFlow import config
from Products.AlphaFlow.action import Action


class DecisionActivity(BaseAssignableActivity):
    """Decide to accept or reject.

    First 'no' counts as result 'no'.
    decision_modus says how many 'yes' are needed for a 'yes' result.
    """

    zope.interface.implements(IDecisionActivity)
    zope.interface.classProvides(IActivityClass)

    security = ClassSecurityInfo()

    meta_type = "AlphaFlow Decision Activity"
    activity_type = "decision"
    icon = "misc_/AlphaFlow/decision"

    known_decision_modi = ['first_yes', 'all_yes']

    decision_notice = None
    decision_modus = ""

    schema_to_validate = IDecisionActivity

    configurationSchema = BaseAssignableActivity.configurationSchema.copy()
    configurationSchema.get('assignees').widget = atapi.MultiSelectionWidget(
        label="Assigned users",
        description="Select one or more users who should decide the document",
        i18n_description="d_review",
        format='checkbox')

    def __init__(self):
        DecisionActivity.inheritedAttribute('__init__')(self)

        self._setExit("accept", u"If the answer is 'yes'...")
        self._setExit("reject", u"If the answer is 'no'...")


InitializeClass(DecisionActivity)


class DecisionWorkItem(BaseAssignableWorkItem):

    zope.interface.implements(IDecisionWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    activity_type  = "decision"
    security = ClassSecurityInfo()
    decisions = None

    ###########
    # IWorkItem

    security.declarePrivate("onStart")
    def onStart(self):
        super(DecisionWorkItem, self).onStart()
        self.decisions = {}

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

    ###################
    # IDecisionWorkItem

    security.declareProtected(config.HANDLE_WORKITEM, "reject")
    def reject(self, REQUEST=None):
        """Reject"""
        if self.state != "active":
            raise ValueError, "Can't reject when not active."
        self._register_decision(False)
        self.passCheckpoint("reject")
        ILifeCycleController(self).complete('Rejected.')
        self.notifyAssigneesChange()
        self._update_ui_after_action('Rejected.', REQUEST)

    security.declareProtected(config.HANDLE_WORKITEM, "accept")
    def accept(self, REQUEST=None):
        """Accept"""
        if self.state != "active":
            raise ValueError, "Can't accept when not active."
        self._register_decision(True)
        self._is_accepted()
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

    #########
    # private

    security.declarePrivate('_register_decision')
    def _register_decision(self, decision):
        "decision must be True or False."
        user = getSecurityManager().getUser().getUserName()
        if user in self.decisions:
            raise ValueError, "Can't decide two times."
        self.decisions[user] = decision
        self._p_changed = 1

    security.declarePrivate('_get_assignees_dict')
    def _get_assignees_dict(self):
        assignees = dict([ (name, True) for name in self.listRelevantUsers()])
        return assignees

    security.declarePrivate('_is_accepted_first_yes')
    def _is_accepted_first_yes(self):
        # one or more accepted -> accepted
        for decision in self.decisions.values():
            if decision:
                return True
        return False

    security.declarePrivate('_is_accepted_all_yes')
    def _is_accepted_all_yes(self):
        # all accepted --> accepted
        assignees = self._get_assignees_dict()
        return assignees == self.decisions

    security.declarePrivate('_is_accepted')
    def _is_accepted(self):
        acc = getattr(self,
                      '_is_accepted_' + self.getActivity().decision_modus)()
        if not acc:
            return
        self.passCheckpoint("accept")
        ILifeCycleController(self).complete("All assignees accepted.")


InitializeClass(DecisionWorkItem)
registerType(DecisionWorkItem, config.PROJECTNAME)


class DecisionLogEntry(Products.AlphaFlow.workitem.GenericLogEntry):
    """Decisions show which users gave input for a decision."""

    zope.component.adapts(DecisionWorkItem)

    @property
    def annotation(self):
        annotation = []
        for user, decision in self.context.decisions.items():
            annotation.append("%s: %s" % (
                user, decision and 'accepted' or 'rejected'))
        return '<br/>'.join(annotation)
