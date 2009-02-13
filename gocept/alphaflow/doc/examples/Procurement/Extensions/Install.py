# Copyright (c) 2004-2006 gocept. All rights reserved.
# See also LICENSE.txt
# $Id$

import os.path
from StringIO import StringIO

import zope.component

from Products.CMFCore.utils import getToolByName

from Products.Archetypes import public as atapi
from Products.Archetypes.Extensions.utils import installTypes, install_subskin

from Products.AlphaFlow.interfaces import \
     IWorkflowImporter, IProcessWriteContainer
from Products.AlphaFlow.process import Process
from Products.Procurement import config, utils


def install(self):
    out = StringIO()

    self._addRole("Procurement")
    self._addRole("Finance")

    for account in config.accounts.keys():
        self.acl_users.userFolderAddGroup(utils.getGroupFromAccount(account),())

    installTypes(self, out,
                 atapi.listTypes(config.PROJECTNAME),
                 config.PROJECTNAME)

    install_subskin(self, out, config.GLOBALS)

    wf_tool = getToolByName(self, "portal_workflow")
    wf_tool.setChainForPortalTypes(
        [t['portal_type'] for t in atapi.listTypes(config.PROJECTNAME)],
        "alphaflow_fake")

    alf = getToolByName(self, 'workflow_manager')
    id = "procurement"

    if id in alf.processes.objectIds():
        IProcessWriteContainer(alf.processes).remove(id)

    wf_dir = os.path.abspath(os.path.join(
            os.path.split(config.GLOBALS['__file__'])[0],
            "workflows"))
    importer = zope.component.getUtility(IWorkflowImporter, name='xml')
    version = importer(file(os.path.join(wf_dir, "simple.alf")))
    process = IProcessWriteContainer(alf.processes).add(id, Process(id))
    process.editable(version)
    process.update()
