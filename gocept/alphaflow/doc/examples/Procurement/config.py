# Copyright (c) 2004-2006 gocept. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.CMFCore import permissions

from Products.Archetypes import public as atapi

PROJECTNAME = "Procurement"

GLOBALS = globals()

ADD_CONTENT_PERMISSION = permissions.AddPortalContent

SKINS_DIR = "skins"

accounts = atapi.DisplayList([
        ("6815", "Office supplies"),
        ("0651", "IT: Hardware"),
        ("0135", "IT: Software"),
        ("0620", "Tools"),
        ("0650", "Office equipment"),
        ("6820", "Books and journals"),
        ("", "Unspecified"),
        ])

wf_states = atapi.DisplayList([
        ("private", "Not yet submitted or returned"),
        ("pending", "Pending review"),
        ("accepted", "Accepted"),
        ("bought", "Bought"),
        ("rejected", "Rejected"),
        ])
