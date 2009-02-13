# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""ProcessManager related views"""

import zope.component

import AccessControl
import Products.CMFCore.utils
import Products.AlphaFlow.browser.base


class Tools(Products.AlphaFlow.browser.base.AlphaFlowView):

    def cleanup(self):
        self.context.cleanUpInstances()
        self.request.response.redirect(
          self.context.absolute_url() +
          '/manage_tools?manage_tabs_message=Cleaned+up.')
