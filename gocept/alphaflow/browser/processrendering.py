# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import Products.Five

import Products.AlphaFlow.interfaces


class ProcessGraph(Products.Five.BrowserView):

    @property
    def graphing(self):
        g = Products.AlphaFlow.interfaces.IWorkflowGraph(self.context)
        g.zoom = self.request.get('zoom') or g.zoom
        g.highlight = self.request.get('highlight')
        session = getattr(self.request, 'SESSION', {})
        g.expand_groups = session.get('expandgroup', [])
        return g

    def expandGroup(self, groupname):
        expanded = self.request.SESSION.get('expandgroup', ())
        if groupname not in expanded:
            expanded += (groupname,)
        self.request.SESSION.set('expandgroup', expanded)

    def closeGroup(self, groupname):
        expanded = self.request.SESSION.get('expandgroup', ())
        if groupname in expanded:
            expanded = list(expanded)
            expanded.remove(groupname)
            expanded = tuple(expanded)
        self.request.SESSION.set('expandgroup', expanded)

    def closeAllGroups(self):
        if 'expandgroup' in self.request.SESSION.keys():
            del self.request.SESSION['expandgroup']

    def getGraph(self):
        self.request.RESPONSE.setHeader('Content-Type', 'image/png')
        return self.graphing.render(format='png')

    def getGraphSVG(self):
        self.request.RESPONSE.setHeader('Content-Type', 'image/svg+xml')
        self.request.RESPONSE.setHeader('Content-Disposition',
                                        'attachment; filename="workflow.svg"')
        return self.graphing.render(format='svg')

    def getMap(self):
        self.request.RESPONSE.setHeader('Content-Type', 'text/xml')
        return self.graphing.render(format='cmapx')
