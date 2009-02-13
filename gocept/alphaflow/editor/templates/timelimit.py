# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""A workflow template for time-limited assignments."""

import zope.formlib.form
import zope.interface
import zope.schema

import Products.AlphaFlow.activities.gates
import Products.AlphaFlow.activities.alarm
import Products.AlphaFlow.activities.routing
import Products.AlphaFlow.sources


class TimeLimitedAssignmentSchema(zope.interface.Interface):

    title = zope.schema.TextLine(title=u"Title")

    assignment = zope.schema.Choice(
        title=u"Assignment activity",
        source=Products.AlphaFlow.sources.PossibleActivitiesSource())


class TimeLimitedAssignment(Products.AlphaFlow.editor.templates.TemplateForm):

    form_fields = zope.formlib.form.FormFields(TimeLimitedAssignmentSchema)

    title = u"Time-limited assignment"

    description = (u"""A time-limited assignment consists of an assignment and
                   a deadline that limits when the assignment must be done.
                   Different activities can be started when the assignment is
                   done or the deadline is reached. The assignment activity might
                   have to be configured further.""")

    def create(self, data):
        title = data['title']

        # Setup gates
        gate1 = self._add_activity(Products.AlphaFlow.activities.gates.GateActivity,
                                   "%s (Task done)" % title)
        gate1.mode = "discriminate"
        gate2 = self._add_activity(Products.AlphaFlow.activities.gates.GateActivity,
                                   "%s (Time-limit reached)" % title)
        gate2.mode = "discriminate"

        # Create alarm
        alarm = self._add_activity(Products.AlphaFlow.activities.alarm.AlarmActivity,
                                   "%s (Time-limit alarm)" % title)
        alarm['CHECKPOINT_COMPLETE'].activities = (gate2.getId(),)

        # Create the assignment activity
        task = self._add_activity(data['assignment'],
                                  "%s (Assigned task)" % title)
        task['CHECKPOINT_COMPLETE'].activities = (gate1.getId(),)

        # Create the route
        route = self._add_activity(Products.AlphaFlow.activities.routing.RouteActivity,
                                   title)
        route.routes = (task.getId(), alarm.getId())
        route.gates = (gate1.getId(), gate2.getId())
