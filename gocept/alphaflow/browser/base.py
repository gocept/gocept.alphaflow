# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""AlphaFlow view basics"""

import Products.Five


class AlphaFlowView(Products.Five.BrowserView):

    def absolute_url(self):
        return self.context.absolute_url() + '/' + self.__name__
