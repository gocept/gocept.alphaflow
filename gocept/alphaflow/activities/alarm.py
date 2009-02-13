# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Implements alarm activities.
"""

import transaction
import zope.interface 
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType
from Products.Archetypes import public as atapi
import Products.CMFCore.utils

import Products.AlphaFlow.interfaces
from Products.AlphaFlow.workitem import BaseWorkItem
from Products.AlphaFlow.activity import BaseAutomaticActivity
from Products.AlphaFlow.activities.interfaces import \
    IAlarmActivity, IAlarmWorkItem
from Products.AlphaFlow import config, utils


class AlarmActivity(BaseAutomaticActivity):

    zope.interface.implements(IAlarmActivity)
    zope.interface.classProvides(Products.AlphaFlow.interfaces.IActivityClass)

    meta_type = "AlphaFlow Alarm Activity"
    activity_type = "alarm"
    icon = "misc_/AlphaFlow/alarm"

    # The following defaults for schema fields are needed to avoid attribute
    # errors. However, they will not validate by default to force users to
    # fill in data.
    due = None

    schema_to_validate = IAlarmActivity

    configurationSchema = atapi.Schema((
        atapi.DateTimeField("due",
            widget=atapi.CalendarWidget(
                label="Alarm date and time",
                description="Select a date and time "
                                "when the alarm should trigger.",
                description_msgid="description_alarm_activity",
                i18n_domain="alphaflow"
                )),
        ))


InitializeClass(AlarmActivity)


class AlarmWorkItem(BaseWorkItem):
    # XXX I know that the activity says it would be automatic. We share the
    # same schema but different behaviour.

    zope.interface.implements(IAlarmWorkItem)
    zope.interface.classProvides(Products.AlphaFlow.interfaces.IWorkItemClass)

    security = ClassSecurityInfo()

    activity_type  = "alarm"

    security.declarePrivate('trigger_workitem')
    def trigger_workitem(self):
        """triggers a workitem if the deadline is exceeded"""
        activity = self.getActivity()
        deadline = self.getActivityConfiguration('due')
        if not deadline:
            deadline = utils.evaluateTales(activity.due, workitem=self)
        if deadline.isPast():
            self.passCheckpoint("continue")
            lc = Products.AlphaFlow.interfaces.ILifeCycleController(self)
            lc.complete(activity.title_or_id())

    security.declareProtected(config.WORK_WITH_PROCESS, 'getStatusInfo')
    def getStatusInfo(self):
        """Return current status of workitem as a text."""
        controller = Products.AlphaFlow.interfaces.ILifeCycleController(self)
        if controller.state == 'active':
            return "deadline not yet reached"
        elif controller.state == 'ended':
            return "deadline exceeded"
        return "Error Status"


InitializeClass(AlarmWorkItem)
registerType(AlarmWorkItem, config.PROJECTNAME)


@zope.component.adapter(Products.AlphaFlow.interfaces.ICronPing)
def receive_cron_ping(event):
    wc = Products.CMFCore.utils.getToolByName(
        event.process_manager, "workflow_catalog")

    workitems = wc(activity_type="alarm", state="active")
    workitems = [x.getObject() for x in workitems]
    workitems = [x for x in workitems if x is not None]

    for item in workitems:
        try:
            item.trigger_workitem()
        except Exception, m:
            controller = \
                Products.AlphaFlow.interfaces.ILifeCycleController(item)
            controller.fail('Failed to trigger the work itemm.', m)
        if config.ENABLE_ZODB_COMMITS:
            transaction.commit()
