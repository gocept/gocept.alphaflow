# Copyright (c) 2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Terminate the workflow."""

import zope.interface
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from Products.AlphaFlow import config
from Products.AlphaFlow.workitem import BaseAutomaticWorkItem
from Products.AlphaFlow.activity import BaseAutomaticActivity
from Products.AlphaFlow.interfaces import \
     IActivityClass, IWorkItemClass, ILifeCycleController
from Products.AlphaFlow.activities.interfaces import \
     ITerminationActivity, ITerminationWorkItem


class TerminationActivity(BaseAutomaticActivity):

    zope.interface.implements(ITerminationActivity)
    zope.interface.classProvides(IActivityClass)

    meta_type = "AlphaFlow Termination Activity"
    activity_type = "termination"
    icon = "misc_/AlphaFlow/expression" #XXX


InitializeClass(TerminationActivity)


class TerminationWorkItem(BaseAutomaticWorkItem):

    zope.interface.implements(ITerminationWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    activity_type  = "termination"

    def run(self):
        """Performs the actual automatic activity"""
        instance = self.getInstance()
        workitems = instance.getWorkItems()
        for wi in workitems:
            if wi is self:
                continue
            ILifeCycleController(wi).terminate(
                "Terminated by %s." % self.getActivity().title_or_id())


InitializeClass(TerminationWorkItem)
registerType(TerminationWorkItem, config.PROJECTNAME)
