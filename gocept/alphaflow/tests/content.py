# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

# test content type

from AccessControl import getSecurityManager

from Products.Archetypes import public as atapi
from Products.AlphaFlow.workflowedobject import AlphaFlowed
from Products.AlphaFlow import config


class DummyContent(AlphaFlowed, atapi.BaseContent):

    portal_type = archetype_name = meta_type = 'DummyContent'

    def set(self, name, value):
        setattr(self, name, value)

    def getCurrentUserName(self):
        security = getSecurityManager()
        return security.getUser().getUserName()


class DummyFolder(AlphaFlowed, atapi.BaseFolder):

    portal_type = archetype_name = meta_type = 'DummyFolder'


class DefaultTestContent(AlphaFlowed, atapi.BaseContent):

    portal_type = archetype_name = meta_type = 'DefaultTestContent'

    schema = atapi.BaseSchema + atapi.Schema((
          atapi.TextField('body', default='foo'),))

    def manage_afterAdd(self, item, container):
        super(DefaultTestContent, self).manage_afterAdd(item, container)
        self.body = 'during_add'
 
       
atapi.registerType(DefaultTestContent, config.PROJECTNAME)
atapi.registerType(DummyContent, config.PROJECTNAME)
atapi.registerType(DummyFolder, config.PROJECTNAME)
