# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Configuration activity and work item."""

import zope.interface
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

import Products.AlphaFlow.workitem
from Products.AlphaFlow.interfaces import \
    IActivityClass, IWorkItemClass, ILifeCycleController
from Products.AlphaFlow.activities.interfaces import \
    IConfigurationActivity, IConfigurationWorkItem
from Products.AlphaFlow.workitem import BaseAssignableWorkItem, Group
from Products.AlphaFlow.activity import BaseAssignableActivity
from Products.AlphaFlow import config
from Products.AlphaFlow.action import Action


class ConfigurationActivity(BaseAssignableActivity):

    zope.interface.implements(IConfigurationActivity)
    zope.interface.classProvides(IActivityClass)

    security = ClassSecurityInfo()

    meta_type = "AlphaFlow Configuration Activity"
    activity_type = "configuration"
    icon = "misc_/AlphaFlow/configuration"

    viewUrlExpression = (
        u'string:${content/absolute_url}/af_edit_workitem?'
         'workitem=${workitem/getId}&action=configure')

    schema_to_validate = IConfigurationActivity

    # Provide invalid default so that the validation in the editor points the
    # user to edit it but doesn't break the edit forms.
    configures = ()

    def __init__(self, *args, **kwargs):
        ConfigurationActivity.inheritedAttribute("__init__")(
            self, *args, **kwargs)
        self._setExit("complete",
                      u"Complete")

InitializeClass(ConfigurationActivity)


class ConfigurationWorkItem(BaseAssignableWorkItem):

    zope.interface.implements(IConfigurationWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    security = ClassSecurityInfo()

    activity_type  = "configuration"

    # XXX security declaration?
    def Schema(self):
        schema = self.schema.copy()
        try:
            instance = self.getInstance()
        except AttributeError:
            # Not yet in context. Ignore this.
            pass
        else:
            other = instance.Schema()

            activity = self.getActivity()
            configures = activity.configures
            for field in other.fields():
                # field.group is the activity_id
                if getattr(field, 'group', '') in configures:
                    schema.addField(field)
        return schema

    #####################
    # IAssignableWorkItem

    security.declareProtected(config.WORK_WITH_PROCESS, "getGroupedSchema")
    def getGroupedSchema(self):
        """returns sequence of IFieldGroup instances

        Aggregates configuration schemas from all activities which are
        configured by this workitem + own schema and returns a 
        schema, grouped by activity

        Every group returned contains at least one field.
        """
        activity = self.getActivity()
        instance = self.getInstance()
        own = ConfigurationWorkItem.inheritedAttribute('getGroupedSchema')(self)
        other = self._group_schema(instance.Schema())
        filtered_other = []
        for group in other:
            if group.activity_id in activity.configures:
                filtered_other.append(group)
        other = filtered_other
        return other + own

    #################
    # IWorkItem

    security.declareProtected(config.WORK_WITH_PROCESS, "getActions")
    def getActions(self):
        """Determine all possible actions."""
        return [Action('configure',
                       'Configure Workflow',
                       self.absolute_url(inner=True)+"/configure",
                       self.configure),
                ]

    ########################
    # IConfigurationWorkItem

    security.declareProtected(config.HANDLE_WORKITEM, "configure")
    def configure(self, REQUEST=None):
        """Do the configuration of the other activities."""
        if self.state != "active":
            raise ValueError("Can't configure when not active.")
        self.passCheckpoint("complete")
        ILifeCycleController(self).complete(self.getComment())
        self.notifyAssigneesChange()
        self._update_ui_after_action('Configuration complete.', REQUEST)

    #########
    # private

    security.declarePrivate('_group_schema')
    def _group_schema(self, schema):
        groups = {}
        instance = self.getInstance()
        for x in schema.fields():
            if not hasattr(x, 'group'):
                continue
            group = x.group
            if not groups.has_key(group):
                groups[group] = []
            groups[group].append(x)
        groups = [ Group(instance, *item) for item in groups.items() ]
        groups.sort()
        return groups


InitializeClass(ConfigurationWorkItem)
registerType(ConfigurationWorkItem, config.PROJECTNAME)
