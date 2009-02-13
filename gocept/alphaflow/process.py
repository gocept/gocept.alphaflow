# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Process definitions"""

import zope.component
import zope.interface

from OFS.Folder import Folder
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

import Products.Archetypes.Referenceable

from Products.AlphaFlow.interfaces import IProcess, IProcessVersion, \
     IActivityClass, IActivity, ILifeCycleController
from Products.AlphaFlow import utils, config


def manage_addProcess(self, id, REQUEST=None):
    self.manage_addProcess(id, REQUEST)


class Process(Products.Archetypes.Referenceable.Referenceable, Folder):
    """A business process.

    Contains different process versions and manages them.

    """

    zope.interface.implements(IProcess)

    meta_type = "AlphaFlow Process"

    meta_types = ({"name": "AlphaFlow ProcessVersion",
                   "action": "",
                   "permission": "Add Folders"},)

    security = ClassSecurityInfo()

    id = None

    editable_id = "1"
    current_id = None

    def __init__(self, id):
        Process.inheritedAttribute("__init__")(self)
        self.id = id

    def manage_afterAdd(self, *args, **kw):
        Process.inheritedAttribute("manage_afterAdd")(self, *args, **kw)

    def title_or_id(self):
        current = self.current()
        if current:
            return current.title_or_id()

        return self.getId()

    security.declareProtected(config.MANAGE_WORKFLOW, "update")
    def update(self):
        if not self.editable():
            raise RuntimeError("This process has no version to update to.")
        self.current_id = self.editable_id
        self.editable_id = str(int(self.editable_id) + 1)

    security.declareProtected(config.MANAGE_WORKFLOW, "editable")
    def editable(self, base=None):
        """Return the editable version of the process or None."""
        editable_version = self.get(self.editable_id, None)

        if base:
            if editable_version:
                raise ValueError(
                    "An editable version already exists: `base` may not be given.")

            if isinstance(base, str):
                editable_version = self.manage_clone(self[base],
                                                     self.editable_id)
            elif Products.AlphaFlow.interfaces.IProcessVersion.providedBy(
                    base):
                base.id = self.editable_id
                self._setObject(self.editable_id, base)
                # Acquisition wrapping
                editable_version = self[self.editable_id]
            else:
                raise TypeError(
                    "`base` must be either a string or IProcessVersion, "
                    "not %r." % base)

        return editable_version

    def current(self):
        if self.current_id is not None:
            return self[self.current_id]

    def old(self):
        old = [version
               for version in self.objectValues()
               if version.getId() not in (self.current_id, self.editable_id)]
        old.reverse()
        return old

    def revert(self):
        """Forget any changes that were made on the current editable version.

        Can only be used if the editable version is not the first version.

        After applying `revert`, the editable version will be `None`.

        """
        if self.current_id is None:
            raise Exception("Can not revert initial version.")
        if not self.editable_id in self.objectIds():
            return
        self.manage_delObjects([self.editable_id])

InitializeClass(Process)


class ProcessVersion(Products.Archetypes.Referenceable.Referenceable, Folder):

    zope.interface.implements(IProcessVersion)

    meta_type = "AlphaFlow ProcessVersion"
    security = ClassSecurityInfo()

    object_name = u'object'
    startActivity = ()
    title = None
    description = None

    validation_errors = None

    def __init__(self, *args, **kwargs):
        ProcessVersion.inheritedAttribute("__init__")(self, *args, **kwargs)
        self.roles = []
        self.validation_errors = []

    def groups(self):
        groups = set()
        for activity in self.objectValues():
            if not activity.group:
                continue
            groups.add(activity.group)
        return groups

    #########################
    # ZMI convenience methods

    security.declareProtected(config.MANAGE_WORKFLOW, 'manage_addActivity')
    def manage_addActivity(self, activity, REQUEST):
        """Add a new activity"""
        uid = REQUEST.get('id', '')
        if not uid:
            uid = utils.generateUniqueId(activity)
        factory = zope.component.getUtility(IActivityClass, name=activity)
        self[uid] = factory()
        self[uid].id = uid
        return self[uid]

    #################
    # IProcessVersion

    security.declareProtected(config.MANAGE_WORKFLOW, "listActivityIds")
    def listActivityIds(self):
        """Returns a list of activity ids from this process."""
        ids = self.objectIds()
        ids.sort()
        return ids

    security.declareProtected(config.MANAGE_WORKFLOW, "listPossibleActivities")
    def listPossibleActivities(self):
        return zope.component.getUtilitiesFor(IActivityClass)

    security.declareProtected(config.MANAGE_WORKFLOW, "acquireProcess")
    def acquireProcess(self):
        """returns the process instance from the acquisition chain"""
        return self.aq_inner

    security.declareProtected(config.MANAGE_WORKFLOW, "countInstances")
    def countInstances(self):
        brains = self.workflow_catalog(
            meta_type="Instance",
            process_uid=self.UID())
        # XXX should be done in a cheaper way
        return sum(1 for brain in brains
                   if ILifeCycleController(brain.getObject()).state != "ended")

    security.declareProtected(config.MANAGE_WORKFLOW, "countInstances")
    def copyToCurrent(self):
        """Create a copy of this process version that becomes
        the currently editable version.
        """
        process = self.acquireProcess()
        process.revert()
        process.editable(self.getId())

    #########
    # private

    security.declarePrivate('_set_allowed_roles_restriction')
    def _set_allowed_roles_restriction(self, roles):
        roles = tuple(roles)  # do not acquire
        utils.modifyRolesForPermission(self, config.INIT_PROCESS, roles)

    security.declarePrivate("validate")
    def validate(self):
        errors = utils.validateFields(IProcessVersion, self)
        for activity in self.objectValues():
            if IActivity.providedBy(activity):
                errors.extend(activity.validate())
            else:
                errors.append(
                    (self,
                     "A Process can only contain Activities, but found %r." %
                     activity))
        utils.log_validation_errors(self, errors)
        return errors


InitializeClass(ProcessVersion)
