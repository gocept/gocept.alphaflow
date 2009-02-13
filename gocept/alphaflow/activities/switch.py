# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""A switch activity.

Walk through a list of cases, each of which carries a TALES expression which
may evaluate to either True (the case being considered a match) or False.
Depending on the switch mode, either stop after the first match or visit all
cases. Create WorkItems from the activities of all matches found.

"""

import zope.interface
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from Products.AlphaFlow import config
from Products.AlphaFlow.workitem import BaseWorkItem
from Products.AlphaFlow.activity import BaseActivity
from Products.AlphaFlow.checkpoint import ExitDefinition
from Products.AlphaFlow.interfaces import \
    IActivityClass, IWorkItemClass, ILifeCycleController
from Products.AlphaFlow.activities.interfaces import \
    ISwitchActivity, ISwitchWorkItem
from Products.AlphaFlow import utils


class CaseDefinition(ExitDefinition):
    # XXX This class is needed for BBB at least to support persistence.
    pass


class SwitchActivity(BaseActivity):

    zope.interface.implements(ISwitchActivity)
    zope.interface.classProvides(IActivityClass)

    security = ClassSecurityInfo()

    meta_type = "AlphaFlow Switch Activity"
    activity_type = "switch"

    # Default to make editor work
    mode = None

    schema_to_validate = ISwitchActivity


InitializeClass(SwitchActivity)


class SwitchWorkItem(BaseWorkItem):

    zope.interface.implements(ISwitchWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    security = ClassSecurityInfo()

    activity_type  = "switch"

    security.declarePrivate('onStart')
    def onStart(self):
        "Trigger that gets called after the workitem has been started."
        super(SwitchWorkItem, self).onStart()
        activity = self.getActivity()
        first = activity.mode == "first"

        for case in activity.getExits():
            try:
                case_result = utils.evaluateTales(case.condition,
                                                  workitem=self)
            except Exception, m:
                ILifeCycleController(self).fail(
                    "Evaluating condition on case %s of activity %s raised an "
                    " exception." % (case.id, activity.title_or_id()), m)
                return
            if case_result:
                self.passCheckpoint(case.id)
                if first:
                    break

        ILifeCycleController(self).complete(activity.title_or_id())


InitializeClass(SwitchWorkItem)
registerType(SwitchWorkItem, config.PROJECTNAME)
