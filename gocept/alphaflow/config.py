# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$


# your site encoding
# NOTE: this must be the same as set in plone (verbose explanation see below)
SITE_ENCODING = "UTF8"

# Why site_encoding here? 
# We have a *lot* of calls to archetype fields, even in security
# relevant parts resulting in a *vast* amount of getCharset calls.
# Being a skin method getCharset is utterly slow. Defining the site encoding
# here too speeds up *a lot*.


# Do you want to patch your default content types to use alphaflow?
PATCH_PLONE_TYPES = True

# Enable ZODB commits for the process manager? 
ENABLE_ZODB_COMMITS = True

try:
    from Products.AlphaFlow.custom_config import *
except ImportError:
    pass

#### NO USER SERVICABLE PARTS AFTER THAT LINE ####

# AT initialization

SKINS_DIR = "skins"
GLOBALS = globals()
PROJECTNAME = PKG_NAME = "AlphaFlow"
WORKFLOW_DIRS = ['workflow', 'workflows']

# Permission definitions
ADD_CONTENT_PERMISSION = "Add portal content"
EDIT_CONTENT_PERMISSION = "Modify portal content"

MANAGE_WORKFLOW = "Manage workflows"
INIT_PROCESS = "Initialize workflow process"

# Permission to protect informative methods
WORK_WITH_PROCESS = "Work with process instance"

# Permission to protect workitem actions
HANDLE_WORKITEM = "Handle Workitem" 

# I need to know where I live
import os
LOCATION = os.path.split(__file__)[0]
del(os)


# meta type defs

mtAllowedRolesAndUsersProxy = 'AllowedRolesAndUsersProxy'

CHECKPOINT_START = "CHECKPOINT_START"
CHECKPOINT_COMPLETE = "CHECKPOINT_COMPLETE"

# Gate modes
DELAYED_DISCRIMINATE = "delayed-discriminate"
DISCRIMINATE = "discriminate"
MULTI_MERGE = "multi-merge"
SYNCHRONIZING_MERGE = "synchronizing-merge"
