# -*- coding: iso-8859-1 -*-
# Copyright (c) 2004-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Process instance views"""

import Products.AlphaFlow.interfaces
from Products.AlphaFlow.interfaces import ILifeCycleController


class ZMIOverview(object):
    """Overview"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.controller = ILifeCycleController(context)

    def event_log(self):
        return self.controller.event_log


class WorkflowLog(object):
    """A log constructed from the work items of the current or last
    process."""

    def __init__(self, context, request):
        self.context= context
        self.request = request
        instances = self.context.getAllInstances()
        if not instances:
            self.log_entries = []
            return
        work_items = instances[0].getWorkItems(None)
        self.log_entries = [Products.AlphaFlow.interfaces.IWorkItemLogEntry(wi)
                            for wi in work_items]
        # Filter away all entries that were terminated
        self.log_entries = [x for x in self.log_entries
                            if (x.state != 'ended' or x.controller.completed)]
        self.log_entries.sort(lambda x,y:-cmp(x.date, y.date))
