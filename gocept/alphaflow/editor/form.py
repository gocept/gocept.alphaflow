# -*- coding: latin-1 -*-
# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Activity forms"""

from datetime import datetime
import Acquisition

import zope.event
import zope.formlib.form
import zope.interface
from zope.publisher.browser import isCGI_NAME
from zope.i18n.interfaces import IUserPreferredCharsets

import zope.app.form.browser.boolwidgets
import zope.app.event.objectevent
from zope.app.i18n import ZopeMessageFactory as _

import Products.AlphaFlow.activities.interfaces
import Products.AlphaFlow.interfaces
import Products.AlphaFlow.aspects.interfaces
import Products.AlphaFlow.editor.interfaces
from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile

# taken and adapted from zope.publisher.browser.BrowserRequest
def _decode(text, charsets):
    """Try to decode the text using one of the available charsets.
    """
    for charset in charsets:
        try:
            text = unicode(text, charset)
            break
        except UnicodeError:
            pass
    return text

def processInputs(request, charsets=None):
    if charsets is None:
        envadapter = IUserPreferredCharsets(request)
        charsets = envadapter.getPreferredCharsets() or ['utf-8']

    for name, value in request.form.items():
        if not (isCGI_NAME(name) or name.startswith('HTTP_')):
            if isinstance(value, str):
                request.form[name] = _decode(value, charsets)
            elif isinstance(value, list):
                request.form[name] = [ _decode(val, charsets)
                                       for val in value
                                       if isinstance(val, str) ]
            elif isinstance(value, tuple):
                request.form[name] = tuple([ _decode(val, charsets)
                                             for val in value
                                             if isinstance(val, str) ])

def setPageEncoding(request):
    """Set the encoding of the form page via the Content-Type header.
    ZPublisher uses the value of this header to determine how to
    encode unicode data for the browser.
    """
    envadapter = IUserPreferredCharsets(request)
    charsets = envadapter.getPreferredCharsets() or ['utf-8']
    charset = charsets[0]
    print "Selected charset", charset
    request.RESPONSE.setHeader(
        'Content-Type', 'text/html; charset=%s' % charset) 


class EditForm(Acquisition.Explicit, zope.formlib.form.EditForm):

    # Overrides the formlib.form.FormBase.template attributes implemented 
    # using NamedTemplates. NamedTemplates using ZopeTwoPageTemplateFile (like
    # formlib does by default) cannot work in Zope2.

    # XXX Maybe we need to have Five-compatible NamedTemplates?

    template = ZopeTwoPageTemplateFile('activity.pt')

    # Overrides formlib.form.FormBase.update. Make sure user input is
    # decoded first and the page encoding is set before proceeding.

    zope.interface.implements(zope.formlib.interfaces.IPageForm)

    def __init__(self, context, request):
        super(EditForm, self).__init__(context, request)
        # This needs to stay here, otherwise the publisher falls
        # on its face. :/
        self.request.debug = None
        #setPageEncoding(self.request)

    def __call__(self, *a, **kw):
        return super(EditForm, self).__call__(*a, **kw)
        return unicode(result, 'iso-8859-15')

    def setUpWidgets(self, *args, **kw):
        super(EditForm, self).setUpWidgets(*args, **kw)
        # Some widget post-processing to support a better layout
        # - compact -> display the widget in front of the title
        for widget in self.widgets:
            widget.compact = False
            if isinstance(widget, zope.app.form.browser.boolwidgets.CheckBoxWidget):
                widget.compact = True

    def update(self):
        processInputs(self.request)
        super(EditForm, self).update()

    @zope.formlib.form.action(_("Apply"),
                              condition=zope.formlib.form.haveInputWidgets)
    def handle_edit_action(self, action, data):
        if zope.formlib.form.applyChanges(
            self.context, self.form_fields, data, self.adapters):

            zope.event.notify(
                zope.app.event.objectevent.ObjectModifiedEvent(self.context)
                )
            # TODO: Needs locale support. See also Five.form.EditView.
            self.status = _(
                "Updated on ${date_time}", 
                mapping={'date_time': str(datetime.utcnow())}
                )
        else:
            self.status = _('No changes')


class DisplayForm(Acquisition.Explicit, zope.formlib.form.DisplayForm):

    template = ZopeTwoPageTemplateFile('display.pt')


class EditExpressionActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IExpressionActivity)

class ViewExpressionActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IExpressionActivity).omit('title')

class EditAlarmActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IAlarmActivity)

class ViewAlarmActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IAlarmActivity).omit('title')

class EditDecisionActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IDecisionActivity)

    def setUpWidgets(self, *args, **kw):
        super(EditDecisionActivity, self).setUpWidgets(*args, **kw)
        self.widgets['decision_notice'].width = 35
        self.widgets['decision_notice'].height = 7

class ViewDecisionActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IDecisionActivity).omit('title')

class EditConfigurationActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IConfigurationActivity)

class EditGateActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IGateActivity)

class ViewGateActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IGateActivity).omit('title')

class ViewConfigurationActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IConfigurationActivity).omit('title')

class EditSwitchActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.ISwitchActivity)

class ViewSwitchActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.ISwitchActivity).omit('title')

class EditNTaskActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.INTaskActivity)

class ViewNTaskActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.INTaskActivity).omit('title')

class EditRouteActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IRouteActivity)

class ViewRouteActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IRouteActivity).omit('title')

class EditSimpleDecisionActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.ISimpleDecisionActivity)

class ViewSimpleDecisionActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.ISimpleDecisionActivity).omit('title')


class EditEMailActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IEMailActivity,
        Products.AlphaFlow.editor.interfaces.ISimpleRecipientSchema).omit('recipient_modes')


class ViewEMailActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.IEMailActivity,
        Products.AlphaFlow.editor.interfaces.ISimpleRecipientSchema).omit('recipient_modes')


class EditTerminationActivity(EditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.ITerminationActivity)


class ViewTerminationActivity(DisplayForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.activities.interfaces.ITerminationActivity)


class EditCheckpoint(EditForm):

    template = ZopeTwoPageTemplateFile('checkpoint.pt')

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.interfaces.ICheckpointDefinition).omit('title')

    def getAspectTypes(self):
        """Returns a generator obj of addable aspects to this
           process.
        """
        aspects = zope.component.getUtilitiesFor(
            Products.AlphaFlow.interfaces.IAspectDefinitionClass)
        return sorted(map(lambda x:x[0], aspects))


class EditExit(EditCheckpoint):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.interfaces.IExitDefinition)


class EditWorkflow(EditForm):

    template = ZopeTwoPageTemplateFile('workflow.pt')

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.interfaces.IProcessVersion)


class AspectEditForm(EditForm):

    template = ZopeTwoPageTemplateFile('aspect.pt')


class EditExpressionAspect(AspectEditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.aspects.interfaces.IExpressionAspectDefinition)


class EditDCWorkflowAspect(AspectEditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.aspects.interfaces.IDCWorkflowAspectDefinition)


class EditParentAspect(AspectEditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.aspects.interfaces.IParentAspectDefinition)


class EditEMailAspect(AspectEditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.aspects.interfaces.IEMailAspectDefinition,
        Products.AlphaFlow.editor.interfaces.ISimpleRecipientSchema).omit('recipient_modes')


class EditPermissionAspect(AspectEditForm):

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.aspects.interfaces.IPermissionAspectDefinition)

    template = ZopeTwoPageTemplateFile('permission.pt')


class EditPermissionSetting(EditForm):

    template = ZopeTwoPageTemplateFile('permissionsetting.pt')

    form_fields = zope.formlib.form.FormFields(
        Products.AlphaFlow.editor.interfaces.IPermissionSettingEdit)

    def __init__(self, context, request):
        context = Products.AlphaFlow.editor.interfaces.IPermissionSettingEdit(
            context)
        super(EditPermissionSetting, self).__init__(context, request)
