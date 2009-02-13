# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""View for workitems."""

import Products.Five

import Products.AlphaFlow.interfaces
import Products.AlphaFlow.config


class Overview(Products.Five.BrowserView):
    """Overview"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.controller = \
            Products.AlphaFlow.interfaces.ILifeCycleController(context)

    def event_log(self):
        return self.controller.event_log

    def begin(self):
        """Time the work item was started."""
        return self.controller.begin

    def completed_by(self):
        """ID of the user that completed this work item."""
        return self.controller.completed_by
