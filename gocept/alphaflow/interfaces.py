# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Interfaces of abstract entities in AlphaFlow, as opposed to those of
concrete activities and work items found in activities.interfaces.
"""

import zope.interface
import zope.schema

import zope.app.event.interfaces

import Products.AlphaFlow.sources

############
# management

class IRoleCache(zope.interface.Interface):

    def updateCacheByWorkItem(workitem):
        """updates cache for work item

        work item -- IWorkItem instance

        calculates work item -> user -> [roles] and caches it.
        Updates secondary cache, too
        """

    def updateCacheByContent(content):
        """update role cache for this content and related instance/work items
        """

    def updateCacheByInstance(instance):
        """update role cache for this instance and related content/work items
        """

    def getDynamicRolesForContent(content, user):
        """return cached roles for content object and user

            content - some IAlphaFlowed
            user - user id (str)

            raises KeyError if content object or user is unknown
        """

    def getDynamicRolesForInstance(instance, user):
        """return cached roles for instance and user
        """

    def getDynamicRolesForWorkItem(workitem, user):
        """return cached roles for work item and user
        """

    def listRelevantUsersForWorkItem(workitem):
        """return a list with all relevant users for a work item
        relevant are all assigned users

        returns empty list if there are no relevant users
        for this work item or the workitem doesn't exist
        """

    def listRelevantUsersForInstance(instance):
        """Return a list of relevant users for a process instance.

        Returns empty list if instance does not exist.

        """

    def listRelevantUsersForContent(content):
        """Return a list of relevant users for a content object.

        Returns an empty list if the content does not have an instance
        assigned.

        """


class IProcessManager(IRoleCache):
    """Manages workflow definitions and instances."""

    id = zope.interface.Attribute("Must be 'workflow_manager'.")

    instances = zope.interface.Attribute(
        "Folder-like object containing workflow instances.")

    processes = zope.interface.Attribute(
        "Folder-like object containing workflow definitions.")

    def initProcess(definition, object):
        """Create a new process instance for a content object.

        The definition is given as a process version (IProcessVersion) and the
        newly created process instance is returned.

        """

    def listProcessDefinitions():
        """Returns all processes (IProcess) defined in the portal."""

    def getStatistics():
        """Gather and return some statistical information.

        The data is returned as a dictionary with the keys:

          all_count -- Amount of instances
          active_count -- Amount of active instances
          failed_count -- Amount of failed instances

        """

    def listInstances(**search):
        """Return a list of instance objects found by the specified search.

        The list will be ordered by ascending activity age of the instance
        (read: last modified instance first).

        XXX Shouldn't this better sort by creation date?

        """

    def replaceInstances(old_version, new_process=None):
        """Terminate instances of old process version and restart with new
        process.

        All instances of the old process version are terminated and then
        started again with the current version of the given process.

        If the new process is not given, then the instances are restarted
        with the current version of the old process.

        old_process: IProcessVersion
        new_process: IProcess

        Returns a list of the new instances.

        """

    def cleanUpInstances():
        """Removes garbage process instances.

        A process instance is considered garbage if any of these is true:
        - The instance has been terminated.
        - The instance does not have an associated content object.
        - The instance's process definition does not exist.

        """

    def queryWorkItems(user):
        """Return a list of work items for the given user.

        The work items are given as catalog brains.

        """

    def pingCronItems():
        """Send a trigger to all time-dependent objects."""

    def doSanityCheck():
        """Perform a sanity check and cleanup.

        Detaches workflowed objects that reference process instances
        incorrectly, e.g. after ZEXP imports from the same portal.

        Returns a list of strings with the issues that were found (and
        handled.)

        """

    def restartHelper(process, activity):
        """Restarts all work items of the given process and activity
        that are currently fallen out.

        Returns how many instances were restarted.

        """

    def bulkDropin():
        """Recovers all instances that are currently fallen out.

        Instances that still have work items which are fallen out are ignored.

        Returns a tuple with the numbers of instances dropped in and ignored:
        (dropped_in, ignored).

        """

###############
# process stuff

class IProcess(zope.interface.Interface):
    """A versioned process definition."""

    id = zope.interface.Attribute("ID of this process definition.")

    def current():
        """Return the current process version or None."""

    def old():
        """Return a list of old process version, latest first."""

    def editable(base=None):
        """Return the editable version of the process or None.

        If no editable version exists and `base` is given,
        a new editable version will be created.

        `base` can be either a ProcessVersion instance which will be used as
        the editable version, or `base` can be the ID of an existing (current
        or old) version from which a copy will be made as the new editable
        version.

        Raises ValueError if `base` is given and an editable version already
        exists.

        """

    def update():
        """Make the currently editable version the new current version.

        Raises RuntimeError if no editable version exists.

        """


class IActivityContainer(zope.interface.Interface):
    pass


class IProcessVersion(IActivityContainer):
    """A process definition."""

    id = zope.interface.Attribute("Id of this process definition.")

    title = zope.schema.TextLine(title=u"Title")

    description = zope.schema.Text(title=u"Description")

    startActivity = zope.schema.Tuple(
        title=u"Start activities",
        default=(),
        description=u"Select the activities that should be started when this "
                    u"workflow is started.",
        value_type=zope.schema.Choice(
            source=Products.AlphaFlow.sources.ActivitySource()))

    object_name = zope.schema.TextLine(
        title=u"Context object variable",
        description=u"The variable name under which the content object can "
                    u"be accessed in TALES expressions.",
        default=u"object")

    validation_errors = zope.interface.Attribute(
        "String indicating validation errors.")

    groups = zope.interface.Attribute(
        "The list of groups that the activities are sorted into.")

    def listActivityIds():
        """Return a list of all activity ids used in this process definition."""

    def acquireProcess():
        """returns the process definition from the acquisition chain"""

    def validate():
        """Validates the configuration of the whole process.

        Sets the validation_errors attribute to a list of message strings.
        Returns a list of (object, message) pairs.

        """


class IAspectDefinitionClass(zope.interface.Interface):
    """A marker interface for registering all aspect definition classes."""


class IActivityClass(zope.interface.Interface):
    """A marker interface to allow registration of all activity classes."""


class IWorkItemClass(zope.interface.Interface):
    """A marker interface to allow registration of all work item classes."""


class IActivity(zope.interface.Interface):
    """A workflow activity.

       These are the building blocks for process definitions.
    """

    title = zope.schema.TextLine(title=u"Title")

    group = zope.schema.TextLine(title=u"Activity group",
        description=u"Name of the group this activity belongs to.",
        required=False)

    viewUrlExpression = zope.schema.TextLine(
        title=u"View URL expression",
        description=u"A TALES expression that computes the URL of the "
                    u"view that should be used to display work items of "
                    u"this activity.",
        required=True)

    configurationSchema = zope.interface.Attribute(
        "An AT schema that can be used to configure a process instance "
        "including this activity.")

    nonEditableFields = zope.interface.Attribute(
        "list of configurationSchema field names that can't be edited")

    validation_errors = zope.interface.Attribute(
        "String indicating validation errors.")

    def getExits():
        """Return the list of all exit checkpoints."""

    def getConfigurationSchema(content):
        """Return the configuration schema. XXX of what?

           This also allows for different activities to have programatic
           influence on what configuration schemas look like. XXX how?

           content: the content object XXX does not seem to be used
        """

    def graphGetPossibleChildren():
        """Return a list of possible successor activities as dictionaries.

           The returned list of dictionaries has the following form:
           [{'id': activity_id, ....}]
           where everything apart from id will be used as attributes for the
           edges of a graph of parent-child relationships between activities.
        """

    def graphGetStartActivities():
        """Return list of activities id which are startActivities of this activity.
        """

    def acquireActivity():
        """returns the activity instance from the acquisition chain"""

    def validate():
        """Validates the configuration of the whole activity.

        Sets the validation_errors attribute to a list of message strings.
        Returns a list of (object, message) pairs.

        """


class IAspectDefinition(zope.interface.Interface):
    """Configuration data for an aspect."""

    id = zope.interface.Attribute("ID")

    title = zope.schema.TextLine(title=u"Title")

    validation_errors = zope.interface.Attribute(
        "String indicating validation errors.")

    def validate():
        """Validates the configuration of the whole aspect definition.

        Sets the validation_errors attribute to a list of message strings.
        Returns a list of (object, message) pairs.

        """

    def graphGetPossibleChildren():
        """Return a list of possible successor activities as dictionaries.

           The returned list of dictionaries has the following form:
           [{'id': activity_id, ....}]
           where everything apart from id will be used as attributes for the
           edges of a graph of parent-child relationships between activities.
        """


class ICheckpointDefinition(zope.interface.Interface):

    id = zope.interface.Attribute("ID")

    title = zope.schema.TextLine(title=u"Title", readonly=True)
    title.order = 10

    activities = zope.schema.Tuple(
        title=u"Start activities",
        default=(),
        description=u"Select the activities that should be started when this "
                    u"checkpoint is passed.",
        value_type=zope.schema.Choice(
            source=Products.AlphaFlow.sources.ActivitySource()))
    activities.order = 20

    validation_errors = zope.interface.Attribute(
        "String indicating validation errors.")

    def validate():
        """Validates the configuration of the whole checkpoint definition.

        Sets the validation_errors attribute to a list of message strings.
        Returns a list of (object, message) pairs.

        """


class IExitDefinition(ICheckpointDefinition):
    """An exit."""

    title = zope.schema.TextLine(title=u"Title")
    title.order = 10

    condition = zope.schema.TextLine(
        title=u"Condition",
        description=u"A TALES expression that returns a boolean value.")


#######################
# content related stuff

class IAlphaFlowed(zope.interface.Interface):
    """A content object manageable by AlphaFlow."""

    instance_id = zope.interface.Attribute("Process instance this object is assigned to.")

    def getSuitableProcesses():
        """Return a list of suitable process definitions."""

    def hasInstanceAssigned():
        """Return whether a process is already assigned to this object
           or not.
        """

    def assignProcess(process_version):
        """Assign a new instance of the process definition with the given id to
           this object.

           Does nothing if the object already has a process instance assigned.

           Returns nothing.

        """

    def getInstance():
        """Return the currently assigned process instance or None.

           XXX should raise an exception if no instance is assigned.
        """

    def getAllInstances():
        """Return a list of all assigned process instances, both completed and
           running.
        """

    def getWorkItemsForCurrentUser():
        """Returns a list of work items for this object."""

    def getWorkItem(id):
        """Return the work item with the given id from the currently to this
           content object attached process instance.

           raises AttributeError if there is no work item with given id
           raises ValueError if no active process instance is attached
           raises Unauthorized if the current user does not have the
               WORK_WITH_PROCESS permission on the requested work item
        """

    def alf_clearInstances():
        """detach all (current and old) instances"""


class IContentObjectRetriever(zope.interface.Interface):
    """Get the content object in various representations."""

    def getContentObject():
        """Return the associated content object or None."""

    def getContentObjectUID():
        """Return the associated content object's UID."""

    def getUrl():
        """Return the URL of the associated content object."""

    def getContentObjectPath():
        """Return the path of the associated content object"""

    def getContentObjectUIDBrain():
        """return brain from uid catalog for content object of self

        returns catalog brain or None
        """

    def getContentObjectPortalCatalogBrain():
        """return the portal_catalog brain for the content object

        returns catalog brain or None
        """


class IInstance(IContentObjectRetriever):
    """A workflow instance.
    """

    process_uid = zope.interface.Attribute(
        "The uid of the process version this is an instance of.")

    def getWorkItem(id):
        """Return the work item with the given id.

           raises AttributeError if WI doesn't exist
           raises Unauthorized if current user does not have the
               WORK_WITH_PROCSES permission on the requested work item
        """

    def unrestrictedGetWorkItem(id):
        """Return the work item with the given id

           raises AttributeError if WI doesn't exist
        """

    def getWorkItems(state="active", activity_id=None):
        """Return a list of all work items in the given state.

           If state is None, all work items are returned.

           If activity_id is not None, all work items that belong to the
           activity with the given id are returned.
        """

    def getWorkItemIds(state="active"):
        """Return a list of the ids of all work items in the given state.

           If state is None, the ids of all work items are returned.
        """

    def createWorkItems(activity_ids, source, content_object=None):
        """Create new work items for the activities with the given ids.

           Raises KeyError if no activity with this id is known.

           activity_ids: sequence of activity ids
           source: work item that is used as "parent" or "source" of the new
                   work items
           content_object: content object to use as context for the work items
                           (if different from the instance)

           Returns a tuple containing the ids of the created work items.
        """

    def getInstance():
        """Return self."""

    def updateWorkitemsAndContentObjects():
        """Update everything affected after editing the workflow configuration.

           Returns nothing.
        """

    def getActivityConfiguration(field, activity_id):
        """Return the configuration for this activity in the context of this
           process instance.
        """


class IWorkItem(IContentObjectRetriever):
    """A work item.

       This is an instance of an activity.
    """

    generated_by = zope.interface.Attribute(
        "Id of the parent work item, None if this is a root work item.")

    generated_workitems = zope.interface.Attribute(
        "A list of work item ids this work item has generated.")

    completed_by = zope.interface.Attribute(
        "Username of the user who completed this work item.")

    checkpoints_passed = zope.interface.Attribute(
        "List of checkpoint names that were passed.")

    def getGeneratedWorkItems():
        """Return a list of work items this work item has generated."""

    def getActions():
        """Return a list of actions the user may perform on this work item.

           This can be used for the Plone action menu.
        """

    def getActionById(id):
        """Return the action with the given id.

           Raises KeyError if an action with the given id does not exist.
        """

    def isRelevant(user):
        """Return whether this work item is relevant for the given user."""

    def listRelevantUsers():
        """Return a list of relevant user ids."""

    def isChildOf(workitem_id=None, workitem=None):
        """Return whether the given work item is a predecessor of this work item
           in terms of generation.

           You may pass only one out of work item_id or workitem.
        """

    def getActivityTitleOrId():
        """Return the title or id of the activity this is an instance of."""

    def getParent():
        """Return the parent work item or None if this is a root work item."""

    def getShortInfo():
        """Return a short information text."""

    def createWorkItems(activity_names):
        """Create new work items for the activities with the given names.

           The created work item ids are remembered.

           Raises KeyError if no activity with this name is known.

           Returns list of ids of the created work items.
        """

    def notifyAssigneesChange():
        """notifies the work item that the assignees might have changed
        to ensure an up-to-date cache.
        """

    def beforeCreationItems(items, parent):
        """Trigger that gets called before new work items get active.

           Other work items can veto on the creation of those items and
           return a list of ids as a veto.

           After all work items have been triggered, the vetoed work items
           get removed again and never become active.
        """

    def notifyWorkItemStateChange(workitem):
        """Receive a notification that the work item <work item> has changed its
           state.
        """

    def passCheckpoint(name):
        """Perform all operations to be done when passing a check point such
        as the start or an exit of a work item.

        returns list of IDs of work items created
        """

    def notifyWorkItemStateChange(workitem):
        """Notify the process instance that the work item <work item> has changed
           its state.

           Returns nothing.
        """


class IWorkItemLogEntry(zope.interface.Interface):
    """A log entry that represents various work item status data in a
    user-comprehensible way.
    """

    state = zope.interface.Attribute(
        "Life cycle state. ")

    users = zope.interface.Attribute(
        "The users that worked or are working on this item.")

    task = zope.interface.Attribute(
        "A textual description of the task.")

    results = zope.interface.Attribute(
        "A textual description of the outcome (for example the triggered "
        "checkpoints).")

    date = zope.interface.Attribute(
        "The reference date for this entry.")

    comment = zope.interface.Attribute(
        "The work item comment.")

    annotation = zope.interface.Attribute(
        "A textual annotation that a work item may provide.")


class IAspect(IContentObjectRetriever):
    """An aspect.

    Aspects are executed by checkpoints. They are similar to automatic work
    items in that they have a life cycle which is short-circuited: aspects
    perform their task complete immediately when they are started.
    """

    def __call__():
        """Worker method that does whatever the aspect is supposed to do.
        """


class ICheckpoint(zope.interface.Interface):
    """A checkpoint.

    Checkpoints are executed when a work item starts, completes or triggers an
    exit.
    """

    id = zope.interface.Attribute("ID")

    generated_workitems = zope.interface.Attribute("Generated work items")


class IWorkItemFactory(zope.interface.Interface):
    """A factory that creates work items for an activity.
    """

    def __call__(source, content_object=None):
        """Create and return work items.
        """


###############################################
# specialized activity and work item interfaces

class IAssignableActivity(IActivity):
    """A workflow activity instances of which may be assigned to a member."""

    showInWorkList = zope.schema.Bool(
        title=u"Show in work list",
        default=True)

    assigneesKind = zope.schema.Choice(
      title=u"Assignment mode",
      values=['possible', 'actual'])

    assigneesExpression = zope.schema.TextLine(
      required=False,
      title=u"Assigned users or groups",
      description=u"A TALES expression that returns a list of user names or "
                  u"groups that are assigned.")

    roles = zope.schema.Tuple(
      required=False,
      title=u"Assigned roles",
      value_type=zope.schema.Choice(
        title=u"Assigned roles",
        source=Products.AlphaFlow.sources.RoleSource()))

    groups = zope.schema.Tuple(
      required=False,
      title=u"Assigned groups",
      value_type=zope.schema.Choice(
        title=u"Assigned groups",
        source=Products.AlphaFlow.sources.GroupSource()))

    def getPossibleAssignees():
        """Return a list of users that may be assigned this activity.

           Depending on the workflow definition, the result depends on a list of
           roles or an expression.

           Returns a sequence of tuples (username, 'Fullname (username)'),
                   sorted by full name.

           NOTE: if the workflow definition does not allow the user to
           select the assignees but defines them itself, this method returns
           the actual assignees.
        """


class IAutomaticActivity(IActivity):
    """Activity which automatically performes an action and continues
    the workflow."""


class IDaemonActivity(IActivity):
    """Marker Interface for daemon activities. Daemon activities are
       completed when only daemon activities are left."""


class IAssignableWorkItem(IWorkItem):
    """Workitem for assignable activities."""

    def getGroupedSchema():
        """returns sequence of IFieldGroup instances

        Aggregates configuration schemas from all activities which are
        configured by this work item + own schema and returns a
        schema, grouped by activity

        Every group returned contains at least one field.
        """

    def getViewUrl():
        """return url to view appropriate the page to handle the work item
        """

    def listMembersWithRolesOnContentObject(roles):
        """get members who have one of the given roles on the content object

        roles: sequence of roles
        return sequence of user ids
        """


class IAutomaticWorkItem(IWorkItem):
    """Implements the automatic activity.

    Automatic WorkItems should subclass BaseAutomaticWorkItem so they
    only need to implement the run-method."""

    def run():
        """Method performing the actual activity."""


##############
# helper stuff

class IFieldGroup(zope.interface.Interface):
    """Helper class to support a specific sort order when
       grouping multiple schemas into a single schema.
    """

    instance = zope.interface.Attribute("IInstance this schema relates to")
    activity_id = zope.interface.Attribute("Id of activity the fields originate from")
    fields = zope.interface.Attribute("sequence of archetype fields")

    def __cmp__(other):
        """compares IFieldGroups by getSortPriority()"""

    def Title():
        """returns the title of the activity"""

    def getProcess():
        """return IProcessVersion of instance"""

    def getActivity():
        """returns activity with id of self.activity_id"""

    def getSortPriority():
        """returns sort priority of activity"""


class IAction(zope.interface.Interface):
    """An action to be performed on a work item."""

    id = zope.interface.Attribute('ID of the action. Must be unique for each work item.')
    title = zope.interface.Attribute('Title of the action. May be unicode.')
    url = zope.interface.Attribute('URL to trigger the action.')
    enabled = zope.interface.Attribute(
        'Flag whether this action is enabled and may be called')

    def __call__():
        """Execute the action.

           Semantics are the same as in calling the url.
        """


class IWorkflowImporter(zope.interface.Interface):
    """An importer that imports a workflow form a file."""

    def __call__(file):
        """Imports a workflow form a file."""


class ILifeCycleController(zope.interface.Interface):
    """Controller that manages the life cycle of an ILifeCycleInstance
    object.

    """

    state = zope.interface.Attribute(
        "Current state of the object. Can be one of ('new', 'active', "
        "'ended', 'failed').")

    event_log = zope.interface.Attribute(
        "A log of events for this life cycle instance. A list of the form "
        " (DateTime, user, state, action, comment).")

    begin = zope.interface.Attribute("DateTime when this life cycle was created.")

    end = zope.interface.Attribute("DateTime when this life cycle ended.")

    completed = zope.interface.Attribute(
        "Tells whether the life cycle completed. (Boolean)")


    def start(comment):
        """Start the life cycle instance object.

        Will trigger `onStart` on the instance as the last step of starting
        it.

        Raises LifeCycleError if starting is not possible, e.g. because it is
        in a state that doesn't allow starting.

        """

    def complete(comment):
        """Complete the life cycle instance object.

        Will trigger `onCompletion` on the instance as the first step of
        completing it.

        Raises LifeCycleError if completing it is not possible, e.g. because
        it is not active.

        """

    def terminate(comment):
        """Terminate the life cycle instance object.

        Will trigger `onTermination` on the instance as the first step of
        terminating it.

        Raises LifeCycleError if termination is not possible, e.g. because it
        is already ended.

        """

    def reset(comment):
        """Reset the life cycle back to `new`.

        Triggers `onReset` on the instance after resetting the state.

        An instance can always be reset.

        """

    def fail(comment, exception=None):
        """Put the life cycle instance object into `failed` state.

        Will trigger `onFailure` on the instance as the first step of changing
        the state.

        Raises LifeCycleError if failing is not possible, e.g. because it
        is not currently active.

        """

    def recover(comment):
        """Recover a failed life cycle instance into `active` state.

        Will trigger `onRecovery` on the instance as the last step of changing
        the state.

        Raises LifeCycleError if failing is not possible, e.g. because it
        is not currently active.

        """

    def recordEvent(action, state, comment, user):
        """Record an action and a comment to the event log.

           Returns nothing.
        """


class ILifeCycleObject(zope.interface.Interface):
    """An object that is part of a workflow and has a life cycle."""

    alphaflow_type = zope.interface.Attribute(
        """States the abstract type of this life cycle object. (I.e.
        `instance`, `workitem`, `checkpoint`, `aspect`, ...)""")

    def onStart():
        """Trigger that gets called after the object is started."""

    def onCompletion():
        """Trigger that gets called before the object is completed."""

    def onTermination():
        """Trigger that gets called before the object is terminated."""

    def onReset():
        """Trigger that gets called after the object is reset."""

    def onFailure():
        """Trigger that gets called before the object is declared failed."""

    def onRecovery():
        """Trigger that gets called after the object is recovered."""


class ILifeCycleEvent(zope.app.event.interfaces.IObjectEvent):
    """Event that gets triggered when a life cycle state changes."""


class IProcessStatistics(zope.interface.Interface):

    def cycle_time(begin, end):
        """Compute the average workflow cycle time from the beginning of work
        items `begin` to the end of work items of `end`.
        """


class IWorkflowGraph(zope.interface.Interface):
    """A workflow object as graph."""

    def render(format):
        """Render the workflow as a graph.

        The output format depends on the rendering engine used in the
        background. This could be something like 'png', 'gif' or similar.

        Returns image data.
        """


class ICronPing(zope.interface.Interface):
    """An event that signals a time-based trigger.

    Works like a heartbeat: comes at more or less regular intervals but
    doesn't promise any specific time to have passed.

    """

    process_manager = zope.interface.Attribute(
        "The process manager which was pinged.")

class CronPing(object):
    """An event that signals a time-based trigger."""

    zope.interface.implements(ICronPing)

    def __init__(self, process_manager):
        self.process_manager = process_manager
