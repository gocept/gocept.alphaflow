# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""DOM importers for the built-in workflow objects."""

import zope.interface

from Products.AlphaFlow.interfaces import \
     IActivityContainer, IActivity, IActivityClass, IAspectDefinitionClass, \
     ICheckpointDefinition
from Products.AlphaFlow.xmlimport.attribute import \
    WorkflowAttribute, WorkflowAttributeList, ConfiguresAttribute, \
    AssigneesAttribute
from Products.AlphaFlow.xmlimport.child import \
     CheckpointFromNode, ExitFromNode, MultipleExitsFromNodes
from Products.AlphaFlow.xmlimport.interfaces import IDOMImporter
import Products.AlphaFlow.activities.notify
from  Products.AlphaFlow.activities.interfaces import IGateActivity
from Products.AlphaFlow.aspects.interfaces import IPermissionAspectDefinition
from Products.AlphaFlow.xmlimport.utils import \
     configure_attributes, import_child_elements, add_child_elements
from Products.AlphaFlow import config
import Products.AlphaFlow.checkpoint
from Products.AlphaFlow.exception import ConfigurationError

class DOMImporterBase(object):
    """Base class for adapters that provide child node importers for
    definition objects, registered by child node name.
    """

    zope.interface.implements(IDOMImporter)

    parent = None

    def __init__(self, parent):
        self.parent = parent


class Checkpoint(DOMImporterBase):

    zope.component.adapts(IActivity)

    attributes = (
        WorkflowAttribute('id', 'id',
                          'Id of the exit.',
                          encoding="ascii", datatype=str),
        WorkflowAttribute('title', 'title',
                          'Title of the exit.'),
        WorkflowAttribute('activities', 'activities',
                          'Continue activities if this exit gets chosen.',
                          encoding='ascii', datatype=tuple),
        )

    def factory(self):
        return Products.AlphaFlow.checkpoint.CheckpointDefinition()

    def __call__(self, node, checkpoint=None):
        if not checkpoint:
            checkpoint = self.factory()
        configure_attributes(node, checkpoint, self.attributes)
        add_child_elements(node, checkpoint, "Aspect")
        return [checkpoint]


class Exit(Checkpoint):

    attributes = Checkpoint.attributes + (
        WorkflowAttribute("condition", "condition",
                          "TALES expression returning True or False."),)

    def factory(self):
        return Products.AlphaFlow.interfaces.IExitDefinition(self.parent)


class Aspect(DOMImporterBase):

    zope.component.adapts(ICheckpointDefinition)

    attributes = (
        WorkflowAttribute('id', 'id',
                          'Id of the activity',
                          encoding="utf-8", datatype=str),
        WorkflowAttribute('title', 'title',
                          'Title of the activity.'),
        WorkflowAttribute('sortPriority', 'sort',
                          'Lower priority activities will be shown first.',
                          datatype=int),
        WorkflowAttribute('nonEditableFields', 'nonEditableFields',
                          'Fields in schema which are not to be edited '
                          'aka configured by user of workflow.',
                          datatype=tuple),
        WorkflowAttribute('commentfield', 'commentfield',
                          'Should the commentfield be hidden or have '
                          'required input?',
                          datatype=str),
        )

    def __call__(self, node, aspect=None):
        name = self.__class__.__name__.lower()
        if name.endswith("aspect"):
            name = name[:-len("aspect")]
        factory = zope.component.getUtility(IAspectDefinitionClass, name=name)
        aspect = factory()
        configure_attributes(node, aspect, self.attributes)
        return [aspect]


class BaseActivity(DOMImporterBase):

    zope.component.adapts(IActivityContainer)

    attributes = (
        WorkflowAttribute('id', 'id',
                          'Id of the activity',
                          required=True, encoding="utf-8", datatype=str),
        WorkflowAttribute('title', 'title',
                          'Title of the activity.'),
        WorkflowAttribute('sortPriority', 'sort',
                          'Lower priority activities will be shown first.',
                          datatype=int),
        WorkflowAttribute('nonEditableFields', 'nonEditableFields',
                          'Fields in schema which are not to be edited '
                          'aka configured by user of workflow.',
                          datatype=tuple),
        WorkflowAttribute('commentfield', 'commentfield',
                          'Should the commentfield be hidden or have '
                          'required input?',
                          datatype=str),
        WorkflowAttribute('group', 'group',
                          'The group this activity belongs to.',
                          datatype=str)
        )

    checkpoints = (
        CheckpointFromNode("start", config.CHECKPOINT_START),
        CheckpointFromNode("end", config.CHECKPOINT_COMPLETE),
        )

    def __call__(self, node, activity=None):
        name = self.__class__.__name__.lower()
        factory = zope.component.getUtility(IActivityClass, name=name)
        activity = factory()
        configure_attributes(node, activity, self.attributes)

        for descriptor in self.checkpoints:
            descriptor.apply(node, activity)

        return [activity]


class BaseAutomaticActivity(BaseActivity):

    checkpoints = BaseActivity.checkpoints + (
        ExitFromNode("continue"),
        )


class BaseAssignableActivity(BaseActivity):

    attributes = BaseActivity.attributes + (
        WorkflowAttribute('viewUrlExpression', 'view_url_expr',
                          '(TALES expression) URL to "view" a  workitem, '
                          'e.g. "Edit document" points to the edit-tab'),
        WorkflowAttribute('showInWorkList', 'show_in_work_list',
                          'Whether to include the work item in work lists.',
                          datatype=bool),
        WorkflowAttribute('contentRoles', 'content_roles',
                          'Roles which assigned users get on the '
                          'content object.',
                          encoding='ascii', datatype=tuple),
        AssigneesAttribute(),
        WorkflowAttribute('completionUrlExpression', 'completion_url_expr',
                          '(TALES Expression) URL to redirect a user to after completing the workitem.'
                          'If empty or unspecified the URL will be determined the default algorithms.')
        )



class Alarm(BaseAutomaticActivity):

    attributes = BaseAutomaticActivity.attributes + (
        WorkflowAttribute('due', 'due',
                          'TALES expression that determines the date when '
                          'this alarm is due.',
                          required=True),)


class Configuration(BaseAssignableActivity):

    attributes = BaseAssignableActivity.attributes + (
        # viewUrlExpression overwrites existing viewUrlExpression
        WorkflowAttribute('viewUrlExpression', 'view_url_expr',
                          '(TALES expression) URL to "view" a  workitem, '
                          'e.g. "Edit document" points to the edit-tab'),
        ConfiguresAttribute('configures', 'configures',
                          'Other activities which are configured by this '
                          'activity or None as marker for all activities.',
                          encoding='ascii', datatype=tuple),
        )

    checkpoints = BaseAssignableActivity.checkpoints + (
        ExitFromNode("complete"),
        )


class DCWorkflow(Aspect):

    attributes = Aspect.attributes + (
        WorkflowAttribute('status', 'status',
                          'Status which is set as DCWorkFlow status.',
                          required=True, encoding='ascii', datatype=str),
        )


class Decision(BaseAssignableActivity):

    known_decision_modi = ['first_yes', 'all_yes']

    attributes = BaseAssignableActivity.attributes + (
        WorkflowAttribute('decision_notice', 'decision_notice',
                          'Describing the task for the decision.'),
        WorkflowAttribute('decision_modus', 'decision_modus',
                          'One of self.known_decision_modi',
                          required=True,
                          vocabulary=known_decision_modi),
        )

    checkpoints = BaseAssignableActivity.checkpoints + (
        ExitFromNode("accept"),
        ExitFromNode("reject"),
        )


expression_attributes = (
    WorkflowAttribute('expression', 'expression',
                      'TALES expression which is to be executed.',
                      required=True),
    WorkflowAttribute('runAs', 'runAs',
                      'TALES expression returning the user to run as.',
                      required=False),
    )


class Expression(BaseAutomaticActivity):

    attributes = BaseAutomaticActivity.attributes + expression_attributes


class ExpressionAspect(Aspect):

    attributes = Aspect.attributes + expression_attributes


from Products.AlphaFlow.activities.gates import \
    MULTI_MERGE, DISCRIMINATE, DELAYED_DISCRIMINATE, SYNCHRONIZING_MERGE

class Gate(BaseAutomaticActivity):

    mode_types = (MULTI_MERGE, DISCRIMINATE, DELAYED_DISCRIMINATE,
            SYNCHRONIZING_MERGE,)

    attributes = BaseAutomaticActivity.attributes + (
        WorkflowAttribute('mode', 'mode',
                          'Mode the gate works, values see self.mode_types',
                          required=True, encoding='ascii', datatype=str,
                          vocabulary=mode_types),
        )


email_attributes = (
    WorkflowAttribute('template', 'template',
                      'ID of a DTML-Method-Object being available from '
                      'portal root.',
                      required=True, encoding='ascii', datatype=str),
    WorkflowAttribute('mailSubject', 'mailSubject',
                      'Static subject line for the mails sent.',
                      required=True),
    WorkflowAttributeList('recipient_modes', 'recipient',
                          'Who will get the email. (possible values see'
                          'default of mode_name in subclasses of '
                          'AbstractRecipent)',
                          required=True, datatype=tuple),
    )


class EMail(BaseAutomaticActivity):

    attributes = BaseAutomaticActivity.attributes + email_attributes


class EMailAspect(Aspect):

    attributes = Aspect.attributes + email_attributes


class Recipient(DOMImporterBase):

    # Distinguish the various recipient modes and create
    # recipient objects

    actual_role = (WorkflowAttribute('roles', 'roles',
                                     'Members with this roles get an e-mail.',
                                     required=True, encoding="ascii",
                                     datatype=tuple),
                   )

    def __call__(self, node, recipient=None):
        notify = Products.AlphaFlow.activities.notify
        recipient_type = node.getAttribute("type")
        if recipient_type == "owner":
            recipient = notify.RecipientOwner()
        elif recipient_type == "next_assignees":
            recipient = notify.RecipientNextAssignees()
        elif recipient_type == "current_assignees":
            recipient = notify.RecipientCurrentAssignees()
        elif recipient_type == "previous_assignees":
            recipient = notify.RecipientPreviousAssignees()
        elif recipient_type == "actual_role":
            recipient = notify.RecipientActualRole()
            configure_attributes(node, recipient, self.actual_role)
        else:
            raise ConfigurationError(
                "Unknown recipient type: " + recipient_type)
        return [recipient]


class NTask(BaseAssignableActivity):

    checkpoints = BaseAssignableActivity.checkpoints + (
        MultipleExitsFromNodes("exit"),
        )


class Parent(Aspect):

    attributes = Aspect.attributes + (
        WorkflowAttribute('parentOf', 'continue_with_parent_of',
                          'Continue with parent of this activity.',
                          required=True, encoding='ascii', datatype=str,
                          ),
        )


class PermissionSetting(DOMImporterBase):

    zope.component.adapts(IPermissionAspectDefinition)

    attributes = (WorkflowAttribute('permission', 'name',
                                    'The permission affected.',
                                    encoding="ascii", datatype=str),
                  WorkflowAttribute('roles', 'roles',
                                    'Sequence of affected roles.',
                                    encoding="ascii", datatype=tuple),
                  WorkflowAttribute('acquire', 'acquire',
                                    '(bool) acquire permission or not.',
                                    datatype=bool),
                  )

    _factory = Products.AlphaFlow.aspects.permission.PermissionSetting

    def __call__(self, node, setting=None):
        # XXX feed the factory with dummy values, should be refactored
        setting = self._factory(None, None, None)
        configure_attributes(node, setting, self.attributes)
        return [setting]


class PermissionAddSetting(PermissionSetting):

    zope.component.adapts(IPermissionAspectDefinition)

    attributes = (WorkflowAttribute('permission', 'name',
                                    'The permission affected.',
                                    encoding="ascii", datatype=str),
                  WorkflowAttribute('roles', 'roles',
                                    'Sequence of affected roles.',
                                    encoding="ascii", datatype=tuple),
                  )

    _factory = Products.AlphaFlow.aspects.permission.PermissionAddSetting


class PermissionRemoveSetting(PermissionSetting):

    zope.component.adapts(IPermissionAspectDefinition)

    attributes = (WorkflowAttribute('permission', 'name',
                                    'The permission affected.',
                                    encoding="ascii", datatype=str),
                  WorkflowAttribute('roles', 'roles',
                                    'Sequence of affected roles.',
                                    encoding="ascii", datatype=tuple),
                  )

    _factory = \
             Products.AlphaFlow.aspects.permission.PermissionRemoveSetting


class PermissionAspect(Aspect):

    attributes = Aspect.attributes

    def __call__(self, node, permission=None):
        (permission,) = super(PermissionAspect, self).__call__(node,
                                                               permission)
        settings = import_child_elements(node, permission)
        for i, setting in enumerate(settings):
            setting.id = str(i)
            permission[setting.id] = setting
        return (permission,)


class Route(BaseAutomaticActivity):

    def __call__(self, node, route=None):
        (route,) = super(Route, self).__call__(node, route)
        activities = [route]

        for activity in import_child_elements(
            node, route, ignore=("start", "end")):
            activities.append(activity)
            if IGateActivity.providedBy(activity):
                route.gates += (activity.getId(),)
            else:
                route.routes += (activity.getId(),)

        return activities


class SimpleDecision(BaseAssignableActivity):

    attributes = BaseAssignableActivity.attributes + (
        WorkflowAttribute('decision_notice', 'decision_notice',
                          'Describing the task for the decision.'),
        )

    checkpoints = BaseAssignableActivity.checkpoints + (
        ExitFromNode("accept"),
        ExitFromNode("reject"),
        )


class Switch(BaseActivity):

    attributes = BaseAutomaticActivity.attributes + (
        WorkflowAttribute('mode', 'mode',
                          'Whether to create WorkItems for only the '
                          'first or all cases yielding True.',
                          required=True, datatype=str,
                          vocabulary=('first', 'all')),
        )

    checkpoints = BaseAssignableActivity.checkpoints + (
        MultipleExitsFromNodes('case'),
        )


class Termination(BaseAutomaticActivity):
    pass
