# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""NTask activity and work item."""

import zope.interface
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from Products.Archetypes import public as atapi

from Products.AlphaFlow.interfaces import IActivityClass, IWorkItemClass
from Products.AlphaFlow.activities.interfaces import \
    INTaskActivity, INTaskWorkItem, ILifeCycleController
from Products.AlphaFlow.workitem import \
     BaseAssignableWorkItem, workflow_action
from Products.AlphaFlow.activity import BaseAssignableActivity
from Products.AlphaFlow import config, utils
from Products.AlphaFlow.action import Action


class NTaskActivity(BaseAssignableActivity):

    zope.interface.implements(INTaskActivity)
    zope.interface.classProvides(IActivityClass)

    security = ClassSecurityInfo()

    meta_type = "AlphaFlow NTask Activity"
    activity_type = "ntask"
    icon = "misc_/AlphaFlow/ntask"

    schema_to_validate = INTaskActivity

    configurationSchema = atapi.Schema((
        atapi.TextField("task",
            widget=atapi.TextAreaWidget(
                label="Description of the task",
                description="Provide a description of the task, so that the "
                            "assigned user knows what to do.",
                description_msgid="description_task_activity",
                i18n_domain="alphaflow"
                )),
        )) + BaseAssignableActivity.configurationSchema


InitializeClass(NTaskActivity)


class NTaskWorkItem(BaseAssignableWorkItem):

    zope.interface.implements(INTaskWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    security = ClassSecurityInfo()

    activity_type  = "ntask"

    ###########
    # IWorkItem

    security.declareProtected(config.WORK_WITH_PROCESS, 'getActions')
    def getActions(self):
        """Determine all possible actions."""
        return [self._get_action(exit)
                for exit in self.getActivity().getExits()]

    security.declarePrivate('_get_action')
    def _get_action(self, exit):
        def callback():
            self.complete(exit.id)

        try:
            exit_enabled = utils.evaluateTales(exit.condition, workitem=self)
        except Exception:
            exit_enabled = False

        a = Action(exit.id,
                   exit.title or exit.id,
                   "%s/complete?exit=%s" % (self.absolute_url(inner=True),
                                            exit.id),
                   callback,
                   exit_enabled)
        return a

    ################
    # INTaskWorkItem

    security.declareProtected(config.HANDLE_WORKITEM, "complete")
    @workflow_action
    def complete(self, exit, REQUEST=None):
        """Complete this workitem"""
        # Verify that the exit that was triggered is actually enabled.
        for action in self.getActions():
            if action.id == exit and action.enabled:
                break
        else:
            raise RuntimeError('No exit with id `%s` enabled.' % exit)

        self.passCheckpoint(exit)
        ILifeCycleController(self).complete("n/a")
        return "Task completed."

    security.declareProtected(config.WORK_WITH_PROCESS, 'getShortInfo')
    def getShortInfo(self):
        """Returns a short information text."""
        return self.getActivityConfiguration("task")

    security.declareProtected(config.WORK_WITH_PROCESS, 'getShortInfo')
    def getStatusInfo(self):
        """Returns a short status information text."""
        return self.getComment()


InitializeClass(NTaskWorkItem)
registerType(NTaskWorkItem, config.PROJECTNAME)
