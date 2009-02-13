# AlphaFlow - next generation workflow module for Plone
#
# Copyright 2004-2006 gocept gmbh & co. kg
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# $Id$
"""Installer"""

import os
from StringIO import StringIO

import zope.component
from Products.CMFCore.utils import getToolByName
from Products.CMFCore import permissions
from Products.Archetypes.Extensions.utils import installTypes, install_subskin
from Products.Archetypes.public import listTypes
from Products.CMFFormController.globalVars import ANY_BUTTON
from Products.CMFFormController.FormAction import FormActionKey

from Products.AlphaFlow import config
from Products.AlphaFlow.utils import modifyRolesForPermission
from Products.AlphaFlow.Extensions import dcworkflow
from Products.AlphaFlow.interfaces import \
     IWorkItemClass, IWorkflowImporter
from Products.AlphaFlow.process import Process


def install_dcworkflow(self, out):
    wf_id = 'alphaflow_fake'
    pw = getToolByName(self, 'portal_workflow')

    def dc_factory():
        wf = dcworkflow.create(wf_id)
        dcworkflow.setupCore(wf, 'AlphaFlow fake workflow',
                             ['visible', 'pending', 'published', 'private',
                              'archived'], [])
        wf.states.setInitialState('visible')
        return wf
    dcworkflow.register(wf_id, dc_factory)
    dcworkflow.install(self, wf_id)
    pw.setChainForPortalTypes('Instance', wf_id)

    # If we patch ATCT we want to have alphaflow_fake as default workflow.
    if config.PATCH_PLONE_TYPES:
        pw.setDefaultChain(wf_id)
        pw.setChainForPortalTypes('Folder', wf_id)
        pw.setChainForPortalTypes('Topic', wf_id)
        pw.setChainForPortalTypes('Large Plone Folder', wf_id)


def uninstall_dcworkflow(self, out):
    pw = getToolByName(self, 'portal_workflow')
    fake_id = 'alphaflow_fake'
    fake_chain = (fake_id, )
    default_id = 'plone_workflow'
    folder_id = 'folder_workflow'

    if pw._default_chain == fake_chain:
        pw.setDefaultChain(default_id)
    if pw.getChainFor('Folder') == fake_chain:
        pw.setChainForPortalTypes('Folder', folder_id)
    if pw.getChainFor('Topic') == fake_chain:
        pw.setChainForPortalTypes('Topic', folder_id)
    if pw.getChainFor('Large Plone Folder') == fake_chain:
        pw.setChainForPortalTypes('Large Plone Folder', folder_id)


def install_instanceobject(self, out):
    at = getToolByName(self, "archetype_tool")
    at.manage_installType(typeName="Instance", package="AlphaFlow")

    # Need to change content_edit action
    fc = getToolByName(self, "portal_form_controller")
    fc.addFormAction('content_edit', 'success', 'Instance', ANY_BUTTON,
        'traverse_to', 'string:af_redirect_to_content')


def install_workitems(self, out):
    fc = getToolByName(self, "portal_form_controller")
    wf_tool = getToolByName(self, "portal_workflow")
    for name, workitem in zope.component.getUtilitiesFor(IWorkItemClass):
        fc.addFormAction('content_edit', 'success', workitem.portal_type,
            ANY_BUTTON, 'traverse_to',
            'string:af_redirect_to_workitem_action')
        # Disable DCWorkFlow for this portal type
        wf_tool.setChainForPortalTypes(pt_names=[workitem.portal_type],
                                       chain='')


def uninstall_formcontroller_actions(self, out):
    fc = getToolByName(self, "portal_form_controller")
    for name, workitem in zope.component.getUtilitiesFor(IWorkItemClass):
        # gaah, this API sucks
        key = FormActionKey('content_edit', 'success',
                            workitem.portal_type, ANY_BUTTON)
        fc.actions.delete(key)

    key = FormActionKey('content_edit', 'success', 'Instance', ANY_BUTTON)
    fc.actions.delete(key)


def configure_catalogs(self, out):
    if 'workflow_catalog' not in self.objectIds():
        self.manage_addProduct['ZCatalog'].manage_addZCatalog(
                                        'workflow_catalog', 'Workflow Catalog')

    added = 0

    indexes = [
        ('meta_type', 'FieldIndex'),
        ('alphaflow_type', 'FieldIndex'),
        ('activity_type', 'FieldIndex'),
        ('activity_id', 'FieldIndex'),
        ('process_uid', 'FieldIndex'),
        ('state', 'FieldIndex'),
        ('modified', 'DateIndex'),
        ('listRelevantUsers', 'KeywordIndex'),
        ('getContentObjectUID', 'FieldIndex'),
        ('showInWorkList', 'FieldIndex'),
    ]
    wfc = getToolByName(self, 'workflow_catalog')
    existing_indexes = wfc.Indexes.objectIds()

    for index_name, index_type in indexes:
        if index_name not in existing_indexes:
            wfc.addIndex(index_name, index_type)
            added += 1

    metadata = [
        "getViewUrl",
        "getShortInfo",
        "getActivityTitleOrId",
        "getContentObjectUID",
        ]
    available_columns = wfc.schema()

    for column in metadata:
        if column not in available_columns:
            wfc.addColumn(column)
            added += 1

    # type/catalog mapping
    catalog_setting = ['workflow_catalog']
    at = getToolByName(self, "archetype_tool")
    at.setCatalogsByType('Instance', catalog_setting)
    for name, workitem in zope.component.getUtilitiesFor(IWorkItemClass):
        at.setCatalogsByType(workitem.meta_type, catalog_setting)

    # Checkpoints
    # XXX This needs review and more flexibility
    at.setCatalogsByType('Checkpoint', catalog_setting)
    at.setCatalogsByType('DCWorkflowAspect', catalog_setting)
    at.setCatalogsByType('ExpressionAspect', catalog_setting)
    at.setCatalogsByType('EMailAspect', catalog_setting)
    at.setCatalogsByType('ParentAspect', catalog_setting)
    at.setCatalogsByType('PermissionAspect', catalog_setting)

    if added:
        wfc.refreshCatalog(clear=1)


def install_portal_catalog(self, out):
    catalog = getToolByName(self, 'portal_catalog')

    # Remove old artefact for triggering cache updates on reindexing
    if 'alphaflow_cache_trigger' in catalog.Indexes.objectIds():
        catalog.delIndex('alphaflow_cache_trigger')

    # Install new index hook for cache updates, if necessary
    allowed_index = catalog.Indexes['allowedRolesAndUsers']
    if allowed_index.meta_type != config.mtAllowedRolesAndUsersProxy:
        catalog.delIndex('allowedRolesAndUsers')
        catalog.addIndex('allowedRolesAndUsers',
                         config.mtAllowedRolesAndUsersProxy)
        catalog.reindexIndex('allowedRolesAndUsers', {})


def uninstall_portal_catalog(self, out):
    catalog = getToolByName(self, 'portal_catalog')
    allowed_index = catalog.Indexes['allowedRolesAndUsers']
    if allowed_index.meta_type == config.mtAllowedRolesAndUsersProxy:
        catalog.delIndex('allowedRolesAndUsers')
        catalog.addIndex('allowedRolesAndUsers', 'KeywordIndex')
        catalog.reindexIndex('allowedRolesAndUsers', {})


def install_manager(self, out):
    wfm = getattr(self, 'workflow_manager', None)
    if wfm is None:
        self.manage_addProduct["AlphaFlow"].manage_addTool('AlphaFlow Process Manager')
    at = getToolByName(self, "portal_actions")
    at.addActionProvider("workflow_manager")


def install_roles(self, out, roles):
    print >>out, 'Adding user defined roles ...'
    for role in roles:
        if role in self.userdefined_roles():
            continue
        self._addRole(role)


def uninstall_roles(self, out, roles):
    self._delRoles([role for role in self.userdefined_roles()
                    if role in roles])


def configure_permissions(self, out):
    modifyRolesForPermission(self, config.INIT_PROCESS,
            ['Manager', 'Owner', 'Reviewer'],
            acquire=True)
    modifyRolesForPermission(self, config.WORK_WITH_PROCESS,
            ['Manager', 'ProcessUser', 'Owner'],
            acquire=True)

    alf = getToolByName(self, 'workflow_manager')
    modifyRolesForPermission(alf, config.HANDLE_WORKITEM,
                             ['Assignee', 'Manager'], acquire=False)
    modifyRolesForPermission(alf, permissions.View,
                             ['ProcessUser', 'Manager', 'Owner'],
                             acquire=False)


def uninstall_skin(self, out):
    remove_skin_layer(self, 'alphaflow')


def remove_skin_layer(self, layer):
    ps = getToolByName(self, 'portal_skins')
    for skin in ps.getSkinSelections():
        path = ps.getSkinPath(skin)
        path = [s.strip() for s in path.split(',')]
        if layer in path:
            path.remove(layer)
            path = ', '.join(path)
            ps.addSkinSelection(skin, path)


def upgrade_instances(self, out):
    alf = getToolByName(self, 'workflow_manager')
    for instance in alf.listInstances():
        instance._rebuild_cache()


def install_process_definitions(self, out, globals):
    alf = getToolByName(self, 'workflow_manager')
    wf_dir = None
    for dir in config.WORKFLOW_DIRS:
        candidate = os.path.abspath(os.path.join(os.path.split(
                    globals['__file__'])[0], dir))
        if os.path.isdir(candidate):
            wf_dir = candidate
            break

    if wf_dir is None:
        raise KeyError, "No workflow directory exists: %s" \
            % config.WORKFLOW_DIRS

    for wf_basename in os.listdir(wf_dir):
        base, ext = os.path.splitext(wf_basename)
        wf_filename = os.path.join(wf_dir, wf_basename)
        if ext != '.alf':
            continue
        if base in alf.processes.objectIds():
            del alf.processes[base]
        print >>out, "Installing %r workflow" % base
        importer = zope.component.getUtility(IWorkflowImporter, name='xml')
        version = importer(file(wf_filename))
        alf.processes[base] = Process(base)
        process = alf.processes[base]
        process.editable(version)
        process.update()


def install(self):
    out = StringIO()

    print >>out, 'Installing skin ...'
    install_subskin(self, out, config.GLOBALS)

    print >>out, 'Installing types ...'
    installTypes(self, out, listTypes(config.PROJECTNAME), config.PROJECTNAME)

    print >>out, "Setting catalog types ..."
    configure_catalogs(self, out)

    install_roles(self, out, ['Assignee', 'ProcessUser'])

    print >>out, 'Importing faked workflow'
    install_dcworkflow(self, out)

    print >>out, "Installing 'workflow_manager' ..."
    install_manager(self, out)

    print >>out, "Setting initial permissions ..."
    configure_permissions(self, out)

    print >>out, "Registering Instance object ..."
    install_instanceobject(self, out)

    print >>out, "Registering work items"
    install_workitems(self, out)

    print >>out, "Configuring portal catalog index / event channel"
    install_portal_catalog(self, out)

    print >>out, "Adding portlet ..."
    portlet = "here/portlet_worklist/macros/portlet"
    if portlet not in self.right_slots:
        self.right_slots = tuple(self.right_slots) + (portlet,)

    print >>out, 'Upgrading instances ...'
    upgrade_instances(self, out)

    if config.PATCH_PLONE_TYPES:
        print >>out, "Installing process definitions ..."
        install_process_definitions(self, out, config.GLOBALS)

    print >>out, "Successfully installed AlphaFlow"
    return out.getvalue()


def uninstall(self):
    out = StringIO()

    # Run the remaining other uninstall steps
    print >>out, 'Uninstalling...'

    qi = getToolByName(self, 'portal_quickinstaller')
    installed_products = qi.listInstalledProducts()
    alphaflow = [prod for prod in installed_products if prod['id']=='AlphaFlow']
    if not alphaflow:
        print >>out, "Alphaflow is not installed. Aborting."
        return

    old_version = alphaflow[0]['installedVersion']
    print >>out, 'Old version is %s, saving that.' % old_version

    # Upgrade support for re-install mechanism
    portal = getToolByName(self, 'portal_url').getPortalObject()
    setattr(portal, 'last_uninstalled_alphaflow_version', old_version)

    print >>out, "Uninstalling portal catalog index / event channel"
    uninstall_portal_catalog(self, out)

    print >>out, "Removing roles and permissions ..."
    uninstall_roles(self, out, ["Assignee", "ProcessUser"])

    print >>out, 'Removing fake workflow ...'
    uninstall_dcworkflow(self, out)

    print >> out, 'Uninstalling FormController actions ...'
    uninstall_formcontroller_actions(self, out)

    print >>out, 'Uninstalling skin ...'
    uninstall_skin(self, out)

    print >>out, "Removing portlet ..."
    portlet = "here/portlet_worklist/macros/portlet"
    self.right_slots = tuple([x for x in self.right_slots if x != portlet])

    return out.getvalue()
