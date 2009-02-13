# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Process statistics."""

import zope.component
import zope.interface

import Products.CMFCore.utils

import Products.AlphaFlow.interfaces


class Statistics(object):
    """Statistics as an adapter for processes."""

    zope.interface.implements(Products.AlphaFlow.interfaces.IProcessStatistics)
    zope.component.adapts(Products.AlphaFlow.interfaces.IProcessVersion)

    def __init__(self, context):
        self.context = context
        self.catalog = Products.CMFCore.utils.getToolByName(context,
                                                            "workflow_catalog")

    def cycle_time(self, begin, end):
        """Tells how long it took in average to move from one activity to
        another in the workflow."""
        paths = list(self.paths(begin, end))
        duration = 0
        for a, b in paths:
            a_start = Products.AlphaFlow.interfaces.ILifeCycleController(a).begin
            b_end = Products.AlphaFlow.interfaces.ILifeCycleController(a).end
            if a_start is None or b_end is None:
                continue
            # Compute the duration in seconds
            duration += (b_end - a_start)
        # Return the average duration in seconds.
        if not paths:
            avg = 0
        else:
            avg = duration / len(paths)
        return avg

    def paths(self, begin, end):
        """Returns all paths from all instances of this process that move from
        the activity `begin` to the activity `end`.
        """
        workitems = self.catalog(
            alphaflow_type='workitem',
            activity_id=end, process_uid=self.context.UID())
        paths = 0
        for workitem in workitems:
            workitem = workitem.getObject()
            path = self._find_reverse_path(workitem, begin)
            if path is not None:
                yield (path, workitem)

    def _find_reverse_path(self, workitem, activity):
        """Find a path from a workitem to an activity with a given id.

        The path is traversed reverse by walking up the workitem's parents
        until a work item is found which matches the given activity.

        This is much faster than traversing the tree from the root.
        """
        seen = set()
        instance = workitem.getParentNode()
        candidate = workitem
        while Products.AlphaFlow.interfaces.IWorkItem.providedBy(candidate):
            if candidate.getActivity().getId() == activity:
                return candidate
            candidate = instance[candidate.generated_by]
