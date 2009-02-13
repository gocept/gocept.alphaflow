# -*- coding: iso-8859-1 -*-
# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Life cycle management"""

import os
import sys

import persistent
import zope.interface
import zope.component
import zope.event
import zope.app.event
import DateTime
import Acquisition
from AccessControl import getSecurityManager, ClassSecurityInfo
from zExceptions.ExceptionFormatter import format_exception
from Globals import InitializeClass

from Products.Archetypes.atapi import BaseFolder

from Products.AlphaFlow import config
from Products.AlphaFlow.interfaces import \
    ILifeCycleObject, ILifeCycleController, ILifeCycleEvent
from Products.AlphaFlow.compatibility.factory import factory
from Products.AlphaFlow.exception import LifeCycleError
from Products.AlphaFlow import utils


DEBUG_FAILURE = os.getenv('ALPHAFLOW_RAISE_ON_FAIL')


class LifeCycleEvent(zope.app.event.objectevent.ObjectEvent):
    """Event that gets triggered when a life cycle state changes."""

    zope.interface.implements(ILifeCycleEvent)


class CannotComplete(LifeCycleError):
    """A life cycle object could not complete."""


class LifeCycleObjectBase(BaseFolder):
    """Mix-in base class for objects that have a life cycle.

    In AlphaFlow, these happen to be just those objects that are instances of
    some definition, such as process instances and work items. They may have
    children (such as a process instance having a number of work items) and
    the association is implemented as containment.

    """

    zope.interface.implements(ILifeCycleObject)

    security = ClassSecurityInfo()

    log_name = "parent"
    log_children_name = "children"

    def createChild(self, definition, name=None):
        id = utils.generateUniqueId(name or definition.getId())
        instance = zope.component.getMultiAdapter((definition, id),
                                                  ILifeCycleObject)
        self._setObject(id, instance)
        return getattr(self, id)

    def onStart(self):
        """Trigger that gets called after the object is started."""

    def onCompletion(self):
        """Trigger that gets called before the object is completed."""

    def onTermination(self):
        """Trigger that gets called before the object is terminated."""
        for inst in self.objectValues():
            controller = ILifeCycleController(inst)
            if controller.state != 'ended':
                controller.terminate(
                    'Terminated due to termination of %s.' % self.log_name)

    def onReset(self):
        """Trigger that gets called after the object is reset."""
        for inst in self.objectValues():
            controller = ILifeCycleController(inst)
            if controller.state != 'ended':
                controller.terminate(
                    'Terminated due to reset of %s.' % self.log_name)

    def onFailure(self):
        """Trigger that gets called before the object is declared failed."""

    def onRecovery(self):
        """Trigger that gets called after the object is recovered."""
        for inst in self.objectValues():
            controller = ILifeCycleController(inst)
            if controller.state == 'failed':
                raise ValueError("Can't recover while failed %s are left." %
                                 self.log_children_name)

    # ZMI helper methods

    # XXX Refactor into its own base class?

    security.declareProtected(config.MANAGE_WORKFLOW, "manage_action")
    def manage_action(self, action, REQUEST, comment="no comment", ):
        """Multiplexes the actions."""
        controller = ILifeCycleController(self)
        if action == "start":
            controller.start(comment)
        elif action == "reset":
            controller.reset(comment)
        elif action == "terminate":
            controller.terminate(comment)
        elif action == "restart":
            controller.reset(comment)
            controller.start(comment)
        elif action == "recover":
            controller.recover(comment)
        elif action == "fail":
            controller.fail(comment)
        else:
            raise KeyError("Not a valid action.")
        REQUEST.RESPONSE.redirect(self.absolute_url() + "/manage_overview")

    # XXX Cataloging support :(

    @property
    def state(self):
        return ILifeCycleController(self).state


InitializeClass(LifeCycleObjectBase)


class LifeCycleController(persistent.Persistent,
                          zope.app.container.contained.Contained,
                          Acquisition.Implicit):
    """Controller that manages the life cycle of an ILifeCycleInstance
    object.

    """

    # XXX handle exceptions during triggers and fall out

    zope.interface.implements(ILifeCycleController)
    zope.component.adapts(ILifeCycleObject)

    state = 'new'
    event_log = ()

    @property
    def begin(self):
        try:
            begin = self._find_last_event_log_entry("start")[0]
        except TypeError:
            begin = None
        return begin

    @property
    def end(self):
        try:
            end = self._find_last_event_log_entry(state="ended")[0]
        except TypeError:
            end = None
        return end

    @property
    def completed(self):
        complete = False
        for time, user, state, action, comment in self.event_log:
            if action == 'complete':
                complete = True
            else:
                complete = False
        return complete

    @property
    def completed_by(self):
        for time, user, state, action, comment in self.event_log:
            if action == 'complete':
                return user

    def __init__(self):
        self.event_log = persistent.list.PersistentList()

    def start(self, comment):
        """Start the life cycle instance object."""
        if self.state != 'new':
            raise LifeCycleError("Can't start instance that is not `new`.")
        self.state = 'active'
        self.recordEvent("start", "active", comment)
        self.__parent__.aq_inner.onStart()
        zope.event.notify(LifeCycleEvent(self.__parent__))

    def complete(self, comment):
        """Complete the life cycle instance object."""
        if self.state in ("terminating", "resetting"):
            return
        if self.state != "active":
            raise CannotComplete(
                "Can't complete instance that is `%s`." % self.state)
        self.__parent__.aq_inner.onCompletion()
        self.state = "ended"
        self.recordEvent("complete", "ended", comment)
        zope.event.notify(LifeCycleEvent(self.__parent__))

    def terminate(self, comment):
        """Terminate the life cycle instance object."""
        if self.state == "ended":
            raise LifeCycleError(
                "Can't terminate instance that is already `ended`.")
        self.state = "terminating"
        self.__parent__.aq_inner.onTermination()
        self.state = "ended"
        self.recordEvent("terminate", "ended", comment)
        zope.event.notify(LifeCycleEvent(self.__parent__))

    def reset(self, comment):
        """Reset the life cycle back to `new`."""
        self.state = "resetting"
        self.__parent__.aq_inner.onReset()
        self.state = "new"
        self.recordEvent("reset", "new", comment)
        zope.event.notify(LifeCycleEvent(self.__parent__))

    def fail(self, comment, exception=None):
        """Put the life cycle instance object into `failed` state."""
        if self.state in ['ended', 'failed']:
            # Ignore failure requests when we are failed already, or ended.
            return
        self.__parent__.aq_inner.onFailure()

        if DEBUG_FAILURE:
            raise

        self.state = 'failed'

        if exception is not None:
            # XXX This should be changed to derive the exception information
            # from the exception instance, as soon as python has this feature.
            exc_info = sys.exc_info()
            comment = comment + "<br/><b>Exception details:</b><br/>" + \
                    ''.join(format_exception(*exc_info, **{'as_html':1}))

        self.recordEvent("failed", "failed", "A failure occured:<br/>" + comment)
        zope.event.notify(LifeCycleEvent(self.__parent__))

    def recover(self, comment):
        """Recover a failed life cycle instance into `active` state."""
        if self.state != "failed":
            raise ValueError("Can't drop in when in `%s` state." % self.state)
        self.state = "active"
        self.recordEvent("recover", "active", comment)
        self.__parent__.aq_inner.onRecovery()
        zope.event.notify(LifeCycleEvent(self.__parent__))

    def recordEvent(self, action, state, comment):
        """Record an action and a comment to the event log."""
        sm = getSecurityManager()
        logitem = (DateTime.DateTime(), sm.getUser().getUserName(), state, action,
                   comment)
        self.event_log.append(logitem)

    def _find_last_event_log_entry(self, action=None, state=None):
        for entry in reversed(self.event_log):
            if action and entry[3] == action:
                return entry
            if state and entry[2] == state:
                return entry


# Make the life cycle controller a persistent adapter / an annotation factory.
def LifeCycleControllerFactory(context):
    controller = factory(LifeCycleController)(context)
    return controller.__of__(context)
