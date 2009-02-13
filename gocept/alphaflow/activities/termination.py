# Copyright (c) 2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Terminate the workflow."""

import zope.interface
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from gocept.alphaflow import config
from gocept.alphaflow.workitem import BaseAutomaticWorkItem
from gocept.alphaflow.activity import BaseAutomaticActivity
from gocept.alphaflow.interfaces import \
     IActivityClass, IWorkItemClass, ILifeCycleController
from gocept.alphaflow.activities.interfaces import \
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
