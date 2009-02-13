# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""A workflow template for parallel reviews."""

import zope.interface
import zope.schema

import Products.AlphaFlow.editor.templates


class ParallelReviewSchema(zope.interface.Interface):


    title = zope.schema.TextLine(title=u"Title")

    reviews = zope.schema.Int(
        title=u"Parallel reviews",
        description=u"The number of reviews to start in parallel.",
        default=3)


class ParallelReview(Products.AlphaFlow.editor.templates.TemplateForm):

    form_fields = zope.formlib.form.FormFields(ParallelReviewSchema)

    title = u"Parallel review"

    description = (u"""A parallel review exists of multiple decision
                   activities that are combined together in a route. When one
                   decision is negative the other decisions are cancelled.
                   Only if all decisions are positive the overall result will
                   be positive.""")

    def create(self, data):
        title = data['title']
        # Gates
        yes_gate = self._add_activity(
            Products.AlphaFlow.activities.gates.GateActivity,
            "%s (Result is yes)" % title)
        yes_gate.mode = 'synchronizing-merge'
        no_gate = self._add_activity(
            Products.AlphaFlow.activities.gates.GateActivity,
            "%s (Result is no)" % title)
        no_gate.mode = 'discriminate'
        # Route
        route = self._add_activity(Products.AlphaFlow.activities.routing.RouteActivity,
                                   title)
        route.gates = (yes_gate.getId(), no_gate.getId())

        for i in range(data['reviews']):
            review = self._add_activity(
                Products.AlphaFlow.activities.decision.DecisionActivity,
                "%s (Decision %i)" % (title, i+1))
            review['accept'].activities = (yes_gate.getId(),)
            review['reject'].activities = (no_gate.getId(),)
            route.routes += (review.getId(),)
