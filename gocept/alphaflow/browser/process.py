# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Process related views"""

import zope.component

from Products.CMFCore.utils import getToolByName
from Products.Archetypes.config import UID_CATALOG

import Products.AlphaFlow.interfaces
import Products.AlphaFlow.process
from Products.AlphaFlow.browser.base import AlphaFlowView
import Products.AlphaFlow.utils


class Process(AlphaFlowView):

    def manage_update(self, redirect):
        self.context.update()
        self.request.response.redirect(redirect)

    def update(self, redirect):
        self.context.update()
        status = "?portal_status_message=Workflow updated"
        self.request.response.redirect(redirect + status)


class ProcessVersion(AlphaFlowView):

    def restartInstances(self, redirect):
        pm = getToolByName(self.context, "workflow_manager")
        pm.replaceInstances(self.context)
        status = "?portal_status_message=" \
                 "Instances restarted using current workflow version"
        self.request.response.redirect(redirect+status)

    def make_editable(self, redirect):
        self.context.copyToCurrent()
        container = self.context.acquireProcess().getParentNode()
        status = "?portal_status_message=" \
                 "Copied version '%s'." % self.context.getId()
        self.request.response.redirect(redirect+status)



class ProcessReadContainer(AlphaFlowView):
    """Management view for readable process containers.

    """

    def __init__(self, *args, **kwargs):
        super(ProcessReadContainer, self).__init__(*args, **kwargs)

    def is_global(self):
        # XXX ???
        return False

    def list(self):
        for obj in self.context.objectValues():
            if Products.AlphaFlow.interfaces.IProcess.providedBy(obj):
                yield obj


class ProcessWriteContainer(AlphaFlowView):
    """Management view for writeable process containers."""

    def __init__(self, *args, **kwargs):
        super(ProcessWriteContainer, self).__init__(*args, **kwargs)

    def _redirect(self):
        self.request.response.redirect(self.context.absolute_url() +
                                       "/manage_processes")

    def manage_addProcess(self, id):
        self.context[id] = Products.AlphaFlow.process.Process(id)
        self._redirect()

    def addProcess(self, title, redirect):
        """Adds new process to process manager."""
        id = Products.AlphaFlow.utils.generateUniqueId('process')
        process = self.context[id] = Products.AlphaFlow.process.Process(id)
        editable = process.editable(
            Products.AlphaFlow.process.ProcessVersion())
        editable.title = title
        status = "?portal_status_message=Workflow created"
        self.request.response.redirect(redirect + status)

    def manage_removeProcess(self, id, redirect):
        del self.context[id]
        self.request.response.redirect(redirect)

    def removeProcess(self, id, redirect):
        del self.context[id]
        status = "?portal_status_message=Workflow deleted"
        self.request.response.redirect(redirect + status)

    def manage_importXML(self, id, xmlfile):
        importer = zope.component.getUtility(
          Products.AlphaFlow.interfaces.IWorkflowImporter, name='xml')
        version = importer(xmlfile)
        self.context[id] = Products.AlphaFlow.process.Process(id)
        process = self.context[id]
        process.editable(version)
        self._redirect()


class PortalProcesses(AlphaFlowView):
    """Management view for all processes within a portal at once."""

    def list_by_path(self):
        GLOBAL_TITLE = "Global process definitions"

        def manage_url(container):
            return container.absolute_url() + "/@@manage_processes"

        def plone_url(container):
            return container.absolute_url() + "/@@alphaflow_processes"

        pm = getToolByName(self, "workflow_manager")
        cat = getToolByName(self, UID_CATALOG)

        processes_by_container = {}
        for process in pm.listProcessDefinitions():
            container = process.getParentNode()
            processes_by_container.setdefault(container, []).append(process)

        global_container_path = '/'.join(pm.processes.getPhysicalPath())
        processes_by_path = {}
        for container, processes in processes_by_container.items():
            path = '/'.join(container.getPhysicalPath())
            if path.startswith(global_container_path):
                path = None
                title = GLOBAL_TITLE
            else:
                title = container.title_or_id()
            processes_by_path[path] = {
                "manage_url": manage_url(container),
                "plone_url": plone_url(container),
                "title": title,
                "processes": processes,
                }
        if None not in processes_by_path:
            processes_by_path[None] = {
                "manage_url": manage_url(pm.processes),
                "plone_url": plone_url(pm.processes),
                "title": GLOBAL_TITLE,
                "processes": [],
                }

        return [data for path, data in sorted(processes_by_path.items())]
