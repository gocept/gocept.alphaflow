# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

# for making an application's content types AlphaFlow-aware:

from Products.AlphaFlow.workflowedobject import AlphaFlowed

# for extending AlphaFlow with new activity types:

from activity import \
    BaseActivity, \
    BaseAutomaticActivity, \
    BaseAssignableActivity

from workitem import \
    BaseWorkItem, \
    BaseAutomaticWorkItem, \
    BaseAssignableWorkItem
