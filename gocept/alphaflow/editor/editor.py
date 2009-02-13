# -*- coding: iso-8859-1 -*-
# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Process instance views"""

import zope.component

import Products.Five

import Products.AlphaFlow.config
import Products.AlphaFlow.interfaces
import Products.AlphaFlow.process


class Editor(Products.Five.BrowserView):

    def canRenderWorkflow(self):
        """Returns True if activities can be found and it's possible to render
           the workflow graph.
        """
        ids = self.context.listActivityIds()
        for id in ids:
            if self.context[id][Products.AlphaFlow.config.CHECKPOINT_START
                                ].activities:
                return True

        return False


class VersionedEditor(Products.Five.BrowserView):

    def __call__(self):
        editable = self.context.editable()
        if editable is None:
            current = self.context.current()
            if current:
                base = current.getId()
            else:
                 base = Products.AlphaFlow.process.ProcessVersion()
            editable = self.context.editable(base)
        self.request.response.redirect(
            editable.absolute_url() + "/editor.html")


class ActivityPanel(Products.Five.BrowserView):

    def getActivities(self):
        """Returns a generator obj of addable activities to this process."""
        return sorted(list(self.context.listPossibleActivities()))

    def listProcessActivities(self):
        """Returns a list of dictionaries with information about activities in
        this process.

        """
        # XXX Unify using the corresponding source.
        activities = self.context.objectValues()
        activities.sort(key=lambda x:x.title_or_id())
        result = []

        for act in activities:
            __traceback_info__ = {'activity':act}
            info = {'title': act.title or act.getId(),
                    'id' : act.getId(),
                    'type': act.activity_type,
                    'url': act.absolute_url(),
            }
            result.append(info)

        return result


class EditActivity(Products.Five.BrowserView):

    def add(self, activity):
        """Add a new activity to the process."""
        uid = Products.AlphaFlow.utils.generateUniqueId(activity)
        factory = zope.component.getUtility(
            Products.AlphaFlow.interfaces.IActivityClass, name=activity)
        activity = factory()
        # XXX Why isn't the request decoded already?
        # (Probably because this is Zope 2)
        activity.id = uid
        self.context[uid] = activity
        activity = self.context[uid]
        return zope.component.getMultiAdapter((activity, self.request),
                                              name='workflow_relative_url')()

    def delete(self):
        parent = self.context.aq_inner.getParentNode()
        parent.manage_delObjects([self.context.getId()])
        return 'loadActivityPanel'


class EditExit(Products.Five.BrowserView):

    def add(self):
        exit = Products.AlphaFlow.interfaces.IExitDefinition(self.context)
        exit.id = Products.AlphaFlow.utils.generateUniqueId('exit')
        self.context._setObject(exit.id, exit)
        exit = self.context[exit.id]
        return zope.component.getMultiAdapter((exit, self.request),
                                              name='workflow_relative_url')()

    def delete(self):
        parent = self.context.aq_inner.getParentNode()
        parent.manage_delObjects([self.context.getId()])
        return 'loadActivityDetailsPanel/' + zope.component.getMultiAdapter(
          (parent, self.request), name='workflow_relative_url')()


class EditAspect(Products.Five.BrowserView):

    def add(self, aspect_type):
        factory = zope.component.getUtility(
            Products.AlphaFlow.interfaces.IAspectDefinitionClass, name=aspect_type)
        aspect = factory()
        aspect.id = Products.AlphaFlow.utils.generateUniqueId(aspect_type)
        self.context[aspect.id] = aspect
        aspect = self.context[aspect.id]
        return zope.component.getMultiAdapter((aspect, self.request),
                                              name='workflow_relative_url')()

    def delete(self):
        parent = self.context.aq_inner.getParentNode()
        parent.manage_delObjects([self.context.getId()])
        return 'loadEditPanel/' + zope.component.getMultiAdapter(
          (parent, self.request), name='workflow_relative_url')()


class EditPermissionSetting(Products.Five.BrowserView):

    def add(self):
        setting = Products.AlphaFlow.aspects.permission.PermissionSetting(
            "View", (), False)
        i = 0
        while str(i) in self.context.objectIds():
            i += 1
        setting.id = str(i)
        self.context[setting.id] = setting
        # Make sure setting is acquisition-wrapped
        setting = self.context[setting.id]
        return zope.component.getMultiAdapter((setting, self.request),
                                              name='workflow_relative_url')()

    def delete(self):
        # We need to get rid of that editing adapter...
        context = self.context.context
        parent = context.aq_inner.getParentNode()
        parent.manage_delObjects([context.getId()])
        return 'loadEditPanel/' + zope.component.getMultiAdapter(
          (parent, self.request), name='workflow_relative_url')()


class WorkflowRelativeURL(object):
    """Computes the relative path of a given object to a workflow process
    definition."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
      path = []
      obj = self.context.aq_inner
      while not Products.AlphaFlow.interfaces.IProcessVersion.providedBy(obj):
          path.insert(0, obj.getId())
          obj = obj.aq_inner.getParentNode()
      return '/'.join(path)
