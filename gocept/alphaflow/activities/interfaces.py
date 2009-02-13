# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Interfaces of and related to specific activities and work items.
"""

import zope.interface
import zope.schema

from Products.AlphaFlow.interfaces import *
import Products.AlphaFlow.sources
import Products.AlphaFlow.config


##############
# helper stuff


class IEMailRecipientMode(zope.interface.Interface):
    """Configure which users are recipients for an email activity."""

    def getRecipientsForWorkItem(workitem):
        """Returns list of user ids which are recipients for a specific
        workitem."""


###########################################
# general activity and work item interfaces

class IRouteActivity(IActivity, IActivityContainer):
    """Routing activity

    A routing activity  controls complex routing within a workflow over
    multiple work items and work item branches.

    The start checkpoint starts one or more routes. When a route reaches a
    gate (by calling createWorkItems with a gate as an activity) the gate
    notices that and might trigger. When a gate triggers all active routes and
    all other active gates are terminated. Only routes and gates that are
    offsprings from this routing activity will be controlled by the gates of
    this routing activity.
    """

    routes = zope.schema.Tuple(
        title=u"Routes to start",
        default=(),
        description=u"Select the activities that should be started as an "
                    u"individual route when this route is started.",
        value_type=zope.schema.Choice(
            source=Products.AlphaFlow.sources.ActivitySource()))

    gates = zope.schema.Tuple(
        title=u"Gates",
        default=(),
        description=u"Select the gates that should be started as"
                    u"synchronisation points for this route.",
        value_type=zope.schema.Choice(
            source=Products.AlphaFlow.sources.GateSource()))


class IRouteWorkItem(IWorkItem):
    """a routing workitem"""

    opened_routes = zope.interface.Attribute("A list of work item ids that are opened routes.")


##############################################
# assignable activity and work item interfaces

class IConfigurationActivity(IAssignableActivity):
    """configuration activity

    Configures other activities."""

    configures = zope.schema.Tuple(
        title=u"Activities to configure",
        default=(),
        description=u"Select the activities that should be configured "
                    u"in this workflow step.",
        value_type=zope.schema.Choice(
            source=Products.AlphaFlow.sources.ActivitySource()),
        required=False, # None is a marker for "all".
                        # XXX This is ugly. The field really is required.
        )


class IConfigurationWorkItem(IAssignableWorkItem):
    """workitem for configuration activity."""

    def configure(REQUEST=None):
        """Do the configuration of the other activities."""


class INTaskActivity(IAssignableActivity):
    """Generalized task (task + decision about continuation)"""


class INTaskWorkItem(IAssignableWorkItem):

    def complete(exit):
        """Call this to signal when the user is done and has decided which exit
           to use.

           exit ... one of the exit ids
        """

class ISimpleDecisionActivity(IAssignableActivity):
    """Decide to accept or reject something.
    """

    decision_notice = zope.schema.TextLine(
      title=u"What is the decision about?")

class IDecisionActivity(IAssignableActivity):
    """Decide to accept or reject.

    First 'no' counts as result 'no'.
    decision_modus says how many 'yes' are needed for a 'yes' result.
    """

    decision_notice = zope.schema.Text(
      title=u"What is the decision about?")

    decision_modus = zope.schema.Choice(
      title=u"Decision mode",
      description=u"Is one `yes` sufficient or does everyone have to say `yes`?",
      values=['first_yes', 'all_yes'])

class IDecisionWorkItem(IAssignableWorkItem):
    """WorkItem for DecisionActivity."""

    def reject():
        """Rejects the decision."""

    def accept():
        """Accepts the decision."""


#############################################
# automatic activity and work item interfaces

class IAlarmActivity(IAutomaticActivity):
    """ Triggers a work item on a given DateTime."""

    due = zope.schema.TextLine(
        title=u"Alarm time",
        description=u"A TALES expression that returns a DateTime object.")


class IAlarmWorkItem(IWorkItem):
    """ Implements the alarm configuration for the activity """

    def trigger_workitem():
        """triggers a work item if the deadline is exceeded"""


class IEMailActivity(IAutomaticActivity):
    """Sends an email to certain interested users about activities in
    this workflow.
    """

    recipient_modes = zope.schema.Tuple(
        title=u"Possible recipients, provide IEMailRecipientMode")

    mailSubject = zope.schema.TextLine(
        title=u"Subject",
        description=u"A TALES string: expression.")

    template = zope.schema.Choice(
        title=u"Message",
        source=Products.AlphaFlow.sources.EmailTemplateSource())


class IEMailWorkItem(IAutomaticWorkItem):
    """Implements the sending of the email."""


class IExpressionActivity(IAutomaticActivity):
    """Execute an expression activity and work item.

    Expressions are run as TALES expressions and have the following contexts:

        workitem - the current work item
        object - the object associated with this process
        activity - the activity for this work item
        portal - the portal root object
    """

    expression = zope.schema.TextLine(title=u"TALES expression")

    runAs = zope.schema.TextLine(
        title=u"Run as user", 
        description=u"Give a TALES expression that evaluates to either a "
                     "username or a user object.",
        default=u"alphaflow/systemUser")


class IExpressionWorkItem(IAutomaticWorkItem):
    """expression workitem """


class ISwitchActivity(IActivity):
    """For a tuple of TALES expressions which return either True or False,
    create a list of WorkItems on either the first or any True.

    toplevel variables for TALES expression see ITalesActivity
    """

    mode = zope.schema.Choice(title=u"Execution mode",
                              description=u"Determines whether all matching "
                                     "cases are executed or just the first.",
                              values=('first', 'all'))


class ISwitchWorkItem(IWorkItem):
    """switch workitem"""


class IGateActivity(IAutomaticActivity):
    """Gate to support routing mechanisms."""

    mode = zope.schema.Choice(
        title=u"Mode",
        description=u"Mode in which the gate works.",
        values=[Products.AlphaFlow.config.MULTI_MERGE,
                    Products.AlphaFlow.config.DISCRIMINATE,
                    Products.AlphaFlow.config.DELAYED_DISCRIMINATE,
                    Products.AlphaFlow.config.SYNCHRONIZING_MERGE])


class IGateWorkItem(IWorkItem):
    """Gate to support routing mechanisms."""


class ITerminationActivity(IAutomaticActivity):
    """Terminate the workflow."""


class ITerminationWorkItem(IWorkItem):
    """Terminate the workflow."""
