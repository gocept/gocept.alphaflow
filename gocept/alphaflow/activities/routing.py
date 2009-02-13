# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Complex routing mechanisms
"""

import zope.interface 
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

import Products.AlphaFlow.workitem
from Products.AlphaFlow.workitem import BaseWorkItem
from Products.AlphaFlow.activity import BaseActivity
from Products.AlphaFlow import config
from Products.AlphaFlow.utils import killWorkItemRecursively
from Products.AlphaFlow.interfaces import \
    IActivityClass, IWorkItemClass, ILifeCycleController
from Products.AlphaFlow.activities.interfaces import \
    IRouteActivity, IRouteWorkItem


class RouteActivity(BaseActivity):
    """Routing activity

    A routing activity  controls complex routing within a workflow over
    multiple work items and work item branches.

    The start checkpoint starts one or more routes. When a route reaches a
    gate (by calling createWorkItems with a gate as an activity) the gate
    notices that and might trigger. When a gate triggers all active routes and
    all other active gates are terminated. Only routes and gates that are
    offsprings from this routing activity will be controlled by the gates of
    this routing activity.  
    """

    zope.interface.implements(IRouteActivity)
    zope.interface.classProvides(IActivityClass)

    security = ClassSecurityInfo()

    meta_type = "AlphaFlow Routing Activity"
    icon = "misc_/AlphaFlow/route"
    activity_type = "route"

    _properties = BaseActivity._properties + \
        ({'id': 'gates', 'type': 'multiple selection', 'mode': 'w',
          'select_variable': 'listActivityIds'},
         {'id': 'routes', 'type': 'multiple selection', 'mode': 'w',
          'select_variable': 'listActivityIds'},
         )

    routes = ()
    gates = ()

    schema_to_validate = IRouteActivity

    def graphGetPossibleChildren(self):
        possible_children = super(RouteActivity,
                                  self).graphGetPossibleChildren()
        for route in self.routes:
            possible_children.append({'id':route,
                                      'exit': 'route',
                                      'label': 'Route'})
        return possible_children


InitializeClass(RouteActivity)


class RouteWorkItem(BaseWorkItem):

    zope.interface.implements(IRouteWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    security = ClassSecurityInfo()

    ######################
    # IWorkItem

    opened_routes = ()

    security.declarePrivate("onStart")
    def onStart(self):
        """Start the gate daemons and route work items
        """
        super(RouteWorkItem, self).onStart()
        self.createWorkItems(self.getActivity().gates)
        self.opened_routes = self.createWorkItems(self.getActivity().routes)

    security.declarePrivate("notifyWorkItemStateChange")
    def notifyWorkItemStateChange(self, workitem):
        """Check if routes have to be closed."""
        # check if workitem is one of our gates
        if workitem.getId() not in self.generated_workitems:
            return
        if workitem.activity_type != "gate":
            return

        # check if gate is completed
        if not ILifeCycleController(workitem).completed:
            return

        finished_gate = workitem.activity_id

        workitems = self.getGeneratedWorkItems()
        # kill other gates
        for wi in workitems:
            if wi.activity_type != "gate":
                continue
            if wi.state != "active":
                continue
            ILifeCycleController(wi).terminate(
                "Competing gate '%s' successfully completed." % finished_gate)

        # kill open routes
        for wi in workitems:
            if wi.activity_type == "gate":
                continue
            # XXX Do not kill the work item that triggered all this ...
            # Our assumption is, that the work item is successfull and
            # either will try to complete in a moment, or may still be
            # relevant as it was 'successfull'. That's the ignore= flag.
            killWorkItemRecursively(
                wi, "Competing route successfully completed at gate '%s'." %
                finished_gate, ignore=[workitem.completing_work_item])

        # complete routing
        ILifeCycleController(self).complete(
            "Gate %s completed" % workitem.activity_id)

    security.declareProtected(config.WORK_WITH_PROCESS, 'getShortInfo')
    def getShortInfo(self):
        """Short information"""     #XXX
        return "Route is open"

    security.declareProtected(config.WORK_WITH_PROCESS, 'getStatusInfo')
    def getStatusInfo(self):
        """Short status information"""  # XXX
        return "Route is open"

    security.declareProtected(config.WORK_WITH_PROCESS, 'getActions')
    def getActions(self):
        """Return a list of actions the user may perform on this work item.
        """
        return ()


InitializeClass(RouteWorkItem)
registerType(RouteWorkItem, config.PROJECTNAME)


class RouteLogEntry(Products.AlphaFlow.workitem.GenericLogEntry):
    """Routes use a different reference date than other work items."""

    zope.component.adapts(RouteWorkItem)

    @property
    def date(self):
        return self.controller.started
