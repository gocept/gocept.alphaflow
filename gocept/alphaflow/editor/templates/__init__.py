# Make this a Python package

import Acquisition
import zope.interface
import zope.formlib.interfaces
import zope.formlib.form

from Products.Five.browser.pagetemplatefile import ZopeTwoPageTemplateFile

import Products.AlphaFlow.utils


class TemplateForm(Acquisition.Explicit, zope.formlib.form.AddForm):

    zope.interface.implements(zope.formlib.interfaces.IPageForm)

    template = ZopeTwoPageTemplateFile('template.pt')

    title = u"Template"

    description = u""

    def __init__(self, context, request):
        super(TemplateForm, self).__init__(context, request)
        # This needs to stay here, otherwise the publisher falls
        # on its face. :/
        self.request.debug = None

    def _add_activity(self, class_, title):
        # XXX This is a repeating pattern and should be refactored.
        uid = Products.AlphaFlow.utils.generateUniqueId(class_.__name__)
        activity = class_()
        activity.title = title
        activity.id = uid
        self.context[uid] = activity
        return self.context[uid]

    @zope.formlib.form.action(zope.formlib.form._("Apply"),
                              condition=zope.formlib.form.haveInputWidgets)
    def handle_save(self, action, data):
        self.create(data)
        return """<a href="call-function://loadActivityPanel">
                  Load activity panel</a>"""
