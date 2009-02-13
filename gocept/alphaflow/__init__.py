# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Zope initialization code"""

from AccessControl import ModuleSecurityInfo
from AccessControl.Permission import registerPermissions

from Products.CMFCore import utils as cmfcoreutils
from Products.CMFCore import DirectoryView
from Products.Archetypes.public import process_types, listTypes
from App.ImageFile import ImageFile

from Products.AlphaFlow import config


def registerPermission(permission, default_roles):
    registerPermissions([(permission, [])], default_roles)


def initialize_content(context):
    from Products.AlphaFlow import instance
    import Products.AlphaFlow.activities
    content_types, constructors, ftis = process_types(
        listTypes(config.PROJECTNAME),
        config.PROJECTNAME)
    cmfcoreutils.ContentInit(
        config.PROJECTNAME+' Content',
        content_types=content_types,
        permission=config.ADD_CONTENT_PERMISSION,
        extra_constructors=constructors,
        fti=ftis,
        ).initialize(context)


def initialize_index(context):
    from Products.AlphaFlow import eventchannel
    context.registerClass(
        eventchannel.EventChannelIndex,
        permission='Add Pluggable Index',
        constructors=(eventchannel.manage_addEventChannelIndex,),
        icon='browser/resources/index.gif',
        visibility=None
        )

    context.registerClass(
        eventchannel.AllowedRolesAndUsersProxy,
        permission='Add Pluggable Index',
        constructors=(eventchannel.manage_addAllowedRolesAndUsersProxy,),
        icon='browser/resources/index.gif',
        visibility=None)


def initialize_tools(context):
    from Products.AlphaFlow import processmanager, process
    tool = cmfcoreutils.ToolInit('workflow_manager',
                                 tools=(processmanager.ProcessManager,
                                        ),
                                 icon='browser/resources/tool.gif')
    tool.initialize(context)

    context.registerClass(process.ProcessVersion,
                          constructors=(process.manage_addProcess,),
                          container_filter=ProcessManagerFilter,
                          )


def initialize(context):
    from Products.AlphaFlow import patch_plone_types

    DirectoryView.registerDirectory(config.SKINS_DIR, config.GLOBALS)
    initialize_tools(context)
    initialize_content(context)
    initialize_index(context)


def ProcessManagerFilter(objectManager):
    """Processes can only show up in Process Manager objects."""
    meta_type = getattr(objectManager.getParentNode(), 'meta_type', '')
    if meta_type not in ["AlphaFlow Process Manager"]:
        return False

    if objectManager.getId() != "processes":
        return False

    return True


ModuleSecurityInfo("Products.Archetypes.config").declarePublic(
  "UID_CATALOG")
ModuleSecurityInfo("Products.AlphaFlow.utils").declarePublic(
    "urlAppendToQueryString")
ModuleSecurityInfo("Products.AlphaFlow.interfaces").declarePublic(
    "ILifeCycleController")
