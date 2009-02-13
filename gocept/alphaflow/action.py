# Copyright (c) 2004-2008 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Action class"""

import zope.interface
from Products.AlphaFlow.interfaces import IAction


class Action(object):
    """An action to be performed on a workitem."""

    zope.interface.implements(IAction)

    __allow_access_to_unprotected_subobjects__ = 1

    id = ""
    title = ""
    url = ""
    enabled = True

    def __init__(self, id, title, url, callback, enabled=True):
        self.id = id
        self.title = title
        self.url = url
        assert callable(callback)
        self._callback = callback
        self.enabled = enabled

    def __call__(self):
        return self._callback()

    def getURL(self, workitem):
        # XXX think more thoroughly about how to integrate this feature
        if workitem.needs_data():
            return ("%(wi_url)s/af_edit_workitem?"
                    "workitem=%(wid)s&amp;action=%(aid)s" %
                    dict(wi_url=workitem.absolute_url(),
                         wid=workitem.getId(),
                         aid=self.id))
        else:
            return self.url
