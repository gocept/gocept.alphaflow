# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Activity definitions"""

import zope.interface
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, getSecurityManager, Unauthorized
from OFS.Folder import Folder

from Products.CMFCore.utils import getToolByName
from Products.Archetypes import public as atapi

from Products.AlphaFlow.interfaces import \
    IActivity, IAutomaticActivity, IAssignableActivity, \
    ICheckpointDefinition, IExitDefinition
from Products.AlphaFlow import config, utils
from Products.AlphaFlow.checkpoint import CheckpointDefinition


class BaseActivity(Folder):
    """A base class to implement activities"""

    zope.interface.implements(IActivity)

    security = ClassSecurityInfo()

    activity_type = None
    configurationSchema = None
    icon = "misc_/AlphaFlow/generic"
    sortPriority = 0
    title = None
    commentfield = ""
    group = None

    nonEditableFields = ()
    viewUrlExpression = u'string:${content/absolute_url}/view'

    schema_to_validate = IActivity


    def __init__(self, *args, **kwargs):
        BaseActivity.inheritedAttribute("__init__")(self, *args, **kwargs)
        self._setObject(config.CHECKPOINT_START,
                        CheckpointDefinition(self, config.CHECKPOINT_START,
                                             u"When this activity starts..."))
        self._setObject(config.CHECKPOINT_COMPLETE,
                        CheckpointDefinition(self, config.CHECKPOINT_COMPLETE,
                                             u"When this activity ends..."))

    security.declareProtected(config.MANAGE_WORKFLOW, "acquireActivity")
    def acquireActivity(self):
        """returns the activity instance from the acquisition chain"""
        return self.aq_inner

    security.declarePrivate("getConfigurationSchema")
    def getConfigurationSchema(self, content):
        """Getter method to retrieve the configuration schema. This also 
           allows for different activities to have programmatic influence 
           over how configuration schemas look like.
        """
        schema = self.configurationSchema
        if schema is not None:
            schema = schema.copy()
        return schema

    security.declarePrivate("getExits")
    def getExits(self):
        return [checkpoint for checkpoint in self.objectValues()
                if IExitDefinition.providedBy(checkpoint)]

    security.declareProtected(config.MANAGE_WORKFLOW, 
                              "graphGetPossibleChildren")
    def graphGetPossibleChildren(self):
        "Return a list of possible successor activities as dictionaries."
        possible_children = []
        for exit in self.objectValues():
            possible_children.extend({'id': activity,
                                      'exit': exit.id,
                                      'label': exit.title or exit.id,
                                      } for activity in exit.activities)
            for aspect in exit.objectValues():
                possible_children.extend(aspect.graphGetPossibleChildren())
        return possible_children

    security.declareProtected(config.MANAGE_WORKFLOW, 'graphGetStartActivities')
    def graphGetStartActivities(self):
        "Return list of activities titles which are startActivities of this one."
        res = []
        process = self.acquireProcess()
        for activity_id in self[config.CHECKPOINT_START].activities:
            res.append(process[activity_id].getId())
        return res

    security.declarePrivate("validate")
    def validate(self):
        errors = utils.validateFields(self.schema_to_validate, self)
        for checkpoint in self.objectValues():
            if ICheckpointDefinition.providedBy(checkpoint):
                errors.extend(checkpoint.validate())
        utils.log_validation_errors(self, errors)
        return errors

    security.declarePrivate("_setExit")
    def _setExit(self, id=None, title=None):
        exit = IExitDefinition(self)
        exit.id = id
        exit.title = title
        self._setObject(id, exit)


@zope.component.adapter(BaseActivity,
                        zope.app.container.interfaces.IObjectAddedEvent)
def added_base_activity(ob, event):
    if ob is event.object:
        ob.__parent__ = event.newParent


InitializeClass(BaseActivity)


class BaseAutomaticActivity(BaseActivity):
    """A base class for automatic activities (single exit)"""

    zope.interface.implements(IAutomaticActivity)

    meta_type = "AlphaFlow Automatic Activity"
    security = ClassSecurityInfo()
    icon = "misc_/AlphaFlow/baseautomaticactivity"

    manage_options = (Folder.manage_options)

    schema_to_validate = IAutomaticActivity

    def __init__(self, *args, **kwargs):
        BaseAutomaticActivity.inheritedAttribute("__init__")(
            self, *args, **kwargs)
        self._setExit("continue", u"When this activity has run...")


InitializeClass(BaseAutomaticActivity)


class BaseAssignableActivity(BaseActivity):
    "Workflow activity instances of which may be assigned to a member."

    zope.interface.implements(IAssignableActivity)

    contentRoles = ()
    completionUrlExpression = ""

    security = ClassSecurityInfo()

    configurationSchema = atapi.Schema((
        atapi.LinesField("assignees",
             vocabulary="getPossibleAssignees",
             enforceVocabulary=True,
             required=True,
             default_method='_get_assignees_default',
             widget=atapi.MultiSelectionWidget(label="Assigned users",
                                 description="Select one or more users for this task",
                ),
            ),
        ))

    showInWorkList = True

    assigneesKind = "possible"
    assigneesExpression = None
    groups = ()
    roles = ()

    schema_to_validate = IAssignableActivity

    security.declareProtected(config.WORK_WITH_PROCESS, "getPossibleAssignees")
    def getPossibleAssignees(self):
        """Returns a list of possible users.

        Works only for roles and groups!
        """
        if self.roles:
            member_ids = list(self._get_assignees_by_roles())
        elif self.groups:
            gt = getToolByName(self, 'portal_groups')
            member_ids = utils.expandGroups(gt, self.groups)
        else:
           member_ids = []

        member_ids.sort()
        return zip(member_ids, member_ids)

    security.declarePrivate("getConfigurationSchema")
    def getConfigurationSchema(self, content):
        """Getter method to retrieve the configuration schema. This also 
           allows for different activities to have programmatic influence 
           over how configuration schemas look like.
        """
        schema = self.configurationSchema
        if schema is not None:
            schema = schema.copy()
            if self.assigneesKind == 'actual':
                # if assigneesKind is actual this field can't get configured
                schema.delField('assignees')
        return schema

    #########
    # private
    security.declarePrivate('_get_assignees_default')
    def _get_assignees_default(self):
        return [getSecurityManager().getUser().getUserName()]

    security.declarePrivate('_get_assignees_by_roles')
    def _get_assignees_by_roles(self):
        content_object = self.getContentObject()
        if content_object is None:
            role_context = self
            roles = ()
        else:
            role_context = content_object
            roles = self.roles
        members = utils.listMembersWithLocalRoles(role_context, roles)
        return members


InitializeClass(BaseAssignableActivity)
