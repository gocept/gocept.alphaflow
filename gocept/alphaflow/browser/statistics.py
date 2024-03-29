# -*- coding: iso-8859-1 -*-
# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""AlphaFlow configlet"""

import Products.Five

import gocept.alphaflow.interfaces


class Statistics(Products.Five.BrowserView):

    def cycle_time(self, begin, end):
        """Adds new process to process manager."""
        statistics = gocept.alphaflow.interfaces.IProcessStatistics(
            self.context)
        return round(statistics.cycle_time(begin, end) * 60)
