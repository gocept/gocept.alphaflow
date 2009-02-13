# Copyright (c) 2004-2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Permission change aspect and definition."""

import zope.interface
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from OFS.Folder import Folder
from Products.Archetypes.public import registerType

import zc.sourcefactory.basic

from Products.AlphaFlow.interfaces import IAspectDefinitionClass
from Products.AlphaFlow.aspect import AspectDefinition, Aspect
from Products.AlphaFlow.aspects.interfaces import \
    IPermissionAspectDefinition, IPermissionAspect, IPermissionSetting
from Products.AlphaFlow.utils import \
    modifyRolesForPermission, addPermissionsToRoles, removePermissionsFromRoles
from Products.AlphaFlow import config, utils


class PermissionSetting(SimpleItem):

    zope.interface.implements(IPermissionSetting)

    permission = ""
    roles = None
    acquire = False

    # XXX This is UI code and should be refactored
    verb = "Set roles to"

    def __init__(self, permission, roles, acquire):
        self.permission = permission
        self.roles = roles
        self.acquire = acquire

    def apply(self, content):
        """Apply the permission setting on the content object."""
        modifyRolesForPermission(content, self.permission, self.roles,
                                         acquire=self.acquire)


class PermissionAddSetting(PermissionSetting):

    # XXX This is UI code and should be refactored
    verb = "Add roles"

    def apply(self, content):
        """Apply the permission setting on the content object."""
        addPermissionsToRoles(content, self.roles, [self.permission])


class PermissionRemoveSetting(PermissionSetting):

    # XXX This is UI code and should be refactored
    verb = "Remove roles"

    def apply(self, content):
        """Apply the permission setting on the content object."""
        removePermissionsFromRoles(content, self.roles, [self.permission])


class PermissionAspectDefinition(Folder, AspectDefinition):

    zope.interface.implements(IPermissionAspectDefinition)
    zope.interface.classProvides(IAspectDefinitionClass)

    security = ClassSecurityInfo()

    meta_type = "AlphaFlow Permission Aspect Definition"
    aspect_type = "permission-change"
    icon = "misc_/AlphaFlow/permission-change"

    title = u"" # must be unicode, which it isn't on Folder

    schema_to_validate = IPermissionAspectDefinition

    def validate(self):
        """Validate the permission configuration.

        - Permissions are required to exist
        """
        errors = super(PermissionAspectDefinition, self).validate()
        for setting in self.objectValues():
            if IPermissionSetting.providedBy(setting):
                utils.validateFields(IPermissionSetting, setting, errors)
            else:
                errors.append(
                    (self,
                     "A PermissionAspect can only contain PermissionSettings, "
                     "but found %r." % setting))
        utils.log_validation_errors(self, errors)
        return errors


InitializeClass(PermissionAspectDefinition)


class PermissionAspect(Aspect):

    zope.interface.implements(IPermissionAspect)

    security = ClassSecurityInfo()

    aspect_type  = "permission-change"

    security.declarePrivate('__call__')
    def __call__(self):
        "Changes the permission configuration"
        permission_changes = self.getDefinition().objectValues()
        ob = self.getContentObject()
        if ob is not None:
            for permset in permission_changes:
                permset.apply(ob)
            ob.aq_inner.reindexObjectSecurity()


InitializeClass(PermissionAspect)
registerType(PermissionAspect, config.PROJECTNAME)


class PermissionSettingSource(
    zc.sourcefactory.basic.BasicSourceFactory):
    """This source returns all permission setting classes.
    """

    def getValues(self):
        return [PermissionSetting, PermissionAddSetting, PermissionRemoveSetting]

    def getToken(self, value):
        return value.__name__

    def getTitle(self, value):
        return value.verb
