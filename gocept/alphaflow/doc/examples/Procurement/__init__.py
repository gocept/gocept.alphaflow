# Copyright (c) 2004-2006 gocept. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.CMFCore import utils as cmfcoreutils
from Products.CMFCore.DirectoryView import registerDirectory

from Products.Archetypes import public as atapi

from Products.Procurement import config


def initialize_content(context):
    from Products.Procurement import request
    
    types = atapi.listTypes(config.PROJECTNAME)
    content_types, constructors, ftis = atapi.process_types(
        types, config.PROJECTNAME)

    cmfcoreutils.ContentInit(
        config.PROJECTNAME + "Content",
        content_types = content_types,
        permission = config.ADD_CONTENT_PERMISSION,
        extra_constructors = constructors,
        fti = ftis,
        ).initialize(context)

def initialize(context):
    registerDirectory(config.SKINS_DIR, config.GLOBALS)
    initialize_content(context)
