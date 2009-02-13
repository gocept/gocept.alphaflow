# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Gates to support routing mechanisms
"""

import zope.interface
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from Products.AlphaFlow.workitem import BaseWorkItem
from Products.AlphaFlow.activity import BaseAutomaticActivity
from Products.AlphaFlow.interfaces import \
    IActivityClass, IWorkItemClass, ILifeCycleController
from Products.AlphaFlow.activities.interfaces import \
    IDaemonActivity, IGateActivity, IGateWorkItem
from Products.AlphaFlow import config


DELAYED_DISCRIMINATE = config.DELAYED_DISCRIMINATE
DISCRIMINATE = config.DISCRIMINATE
MULTI_MERGE = config.MULTI_MERGE
SYNCHRONIZING_MERGE = config.SYNCHRONIZING_MERGE


class GateActivity(BaseAutomaticActivity):

    zope.interface.implements(IDaemonActivity, IGateActivity)
    zope.interface.classProvides(IActivityClass)

    meta_type = "AlphaFlow Gate Activity"
    activity_type = "gate"
    icon = "misc_/AlphaFlow/gate"

    # - Multimerge is like "OR" (trigger on each)
    # - Discriminate is like "XOR" (trigger on first, ignore others)
    # - Delayed-Discriminate is like "XOR" but waits with trigger until
    #   all other routes are completed on their own.    
    # - Synchronize is like "AND" (trigger once when all completed)

    mode = ""

    schema_to_validate = IGateActivity


InitializeClass(GateActivity)


class GateWorkItem(BaseWorkItem):

    security = ClassSecurityInfo()

    zope.interface.implements(IGateWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    activity_type  = "gate"

    completing_work_item = None

    ####################
    # IWorkItem

    security.declarePrivate('onStart')
    def onStart(self):
        super(GateWorkItem, self).onStart()
        self.closed_routes = []
        self.delayed_discriminator = False

    security.declarePrivate("beforeCreationItems")
    def beforeCreationItems(self, items, parent):
        vote_no = []
        my_parent = self.getParent()

        # Do the new items belong to a route?
        route = self._findRouteForWI(parent)
        if route is None:
            return []

        all_routes = self._getAllRoutes()

        for wi in items:
            if wi == self.activity_id:
                vote_no.append(wi)
                self._rememberTrigger(parent, route)

            # XXX This is some special stuff to make the delayed trigger work
            if self.getActivity().mode == DELAYED_DISCRIMINATE:
                process = self.getProcess()
                new_activity = process[wi]
                if isinstance(new_activity, GateActivity):
                    closed_routes = self.closed_routes
                    if not route in self.closed_routes:
                        closed_routes.append(route)
                    if len(closed_routes) == len(all_routes) and self.delayed_discriminator:
                        self._doTrigger(parent, route)
                        self.completing_work_item = parent
                        ILifeCycleController(self).complete(
                            "Gate '%s' triggered and completed after route "
                            "'%s'" % (self.activity_id, route))
                        self.delayed_discriminator = False
                    self.closed_routes = closed_routes

        return vote_no

    #########
    # private

    security.declarePrivate('_findRouteForWI')
    def _findRouteForWI(self, workitem):
        """Identifies to which route this workitem belongs that leads to this gate.

        Returns one of self.getParent().getActivity().routes or None
        """
        routing_start = self.getParent()
        if not workitem.isChildOf(workitem=routing_start):
            return None

        instance = self.getInstance()
        for candidate_id in routing_start.opened_routes:
            candidate = instance[candidate_id]
            if (workitem == candidate) or \
                    workitem.isChildOf(workitem=candidate):
                return candidate_id

    security.declarePrivate('_rememberTrigger')
    def _rememberTrigger(self, triggering_workitem, route):
        mode = self.getActivity().mode
        all_routes = self._getAllRoutes()
        closed_routes = self.closed_routes
        if route in closed_routes:
            return
        controller = ILifeCycleController(self)
        if mode == MULTI_MERGE:
            closed_routes.append(route)
            self._doTrigger(triggering_workitem, route)
            if len(closed_routes) == len(all_routes):
                self.completing_work_item = triggering_workitem
                # XXX no test for this
                controller.complete("Gate '%s' found by route '%s'" %
                                    (self.activity_id, route))
        elif mode == DISCRIMINATE:
            if len(closed_routes) == 0:
                self._doTrigger(triggering_workitem, route)
                self.completing_work_item = triggering_workitem
                controller.complete("Gate '%s' found by route '%s'" %
                                    (self.activity_id, route))
            closed_routes.append(route)
        elif mode == DELAYED_DISCRIMINATE:
            self.delayed_discriminator = True
        elif mode == SYNCHRONIZING_MERGE:
            closed_routes.append(route)
            if len(closed_routes) == len(all_routes):
                self._doTrigger(triggering_workitem, route)
                self.completing_work_item = triggering_workitem
                controller.complete("Gate '%s' completed via route '%s'"
                                    % (self.activity_id, route))
        else:
            # XXX no tests for this
            controller.fail("Unknown gate mode: '%s'" % mode)
        self.closed_routes = closed_routes

    security.declarePrivate('_doTrigger')
    def _doTrigger(self, triggering_workitem, route):
        self.passCheckpoint("continue")
        ILifeCycleController(self).recordEvent(
            "Gate triggered", "active", 
            "Route '%s' triggered '%s-gate' by workitem '%s'" % 
            (route, self.getActivity().mode, triggering_workitem.getId()))

    security.declarePrivate('_getAllRoutes')
    def _getAllRoutes(self):
        return list(tuple(self.getParent().opened_routes))

    security.declareProtected(config.WORK_WITH_PROCESS, 'getActions')
    def getActions(self):
        """Return a list of actions the user may perform on this work item.
        """
        return ()


InitializeClass(GateWorkItem)
registerType(GateWorkItem, config.PROJECTNAME)
