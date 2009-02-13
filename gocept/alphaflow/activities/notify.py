# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Implement the email activities.
"""

import email.Header
import email.MIMEText

import zope.interface
from AccessControl import ClassSecurityInfo
from Persistence import Persistent
from Globals import InitializeClass
from Products.Archetypes.public import registerType
from Products.Archetypes import public as atapi

from Products.CMFCore.utils import getToolByName

import Products.AlphaFlow.utils
from Products.AlphaFlow import config
from Products.AlphaFlow.workitem import BaseAutomaticWorkItem
from Products.AlphaFlow.activity import BaseAutomaticActivity
from Products.AlphaFlow.interfaces import IActivityClass, IWorkItemClass
from Products.AlphaFlow.activities.interfaces import \
    IEMailActivity, IEMailWorkItem, IEMailRecipientMode


class EMailActivity(BaseAutomaticActivity):

    zope.interface.implements(IEMailActivity)
    zope.interface.classProvides(IActivityClass)

    meta_type = "AlphaFlow EMail Activity"
    activity_type = "email"
    icon = "misc_/AlphaFlow/email"

    recipient_modes = ()
    template = ""
    mailSubject = None

    schema_to_validate = IEMailActivity

    configurationSchema = atapi.Schema((
        atapi.LinesField("recipients",
            widget=atapi.TextAreaWidget(
                label="Email recipients",
                description="""Enter the email addresses of all persons """
                            """that should receive this notification.""",
                i18n_domain="alphaflow"
                )),
        ))

InitializeClass(EMailActivity)


class EMailWorkItem(BaseAutomaticWorkItem):

    zope.interface.implements(IEMailWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    security = ClassSecurityInfo()

    activity_type  = "email"

    _automatic_continue = False

    ######################
    # IAutomaticWorkItem

    security.declarePrivate('run')
    def run(self):
        """Send email."""
        activity = self.getActivity()
        instance = self.getInstance()
        wi_ids = self.passCheckpoint("continue")
        work_items = [instance[id] for id in wi_ids] + [self]
        _send_email(self, activity, work_items)


InitializeClass(EMailWorkItem)
registerType(EMailWorkItem, config.PROJECTNAME)


class AbstractRecipent(Persistent):
    """Abstract recipient class."""

    zope.interface.implements(IEMailRecipientMode)

    nodeName = "recipient"
    attributes = ()


class RecipientOwner(AbstractRecipent):
    """Recipient mode for notifying the owner of a process."""

    def getRecipientsForWorkItem(self, wi):
        """Returns list of users which are recipients for a specific
        workitem."""
        content = wi.getContentObject()
        if content:
            return [content.owner_info()['id']]
        else:
            return []


class RecipientNextAssignees(AbstractRecipent):
    """Recipient mode for notifying the assignee of the next workitems."""

    def getRecipientsForWorkItem(self, wi):
        """Returns list of users which are recipients for a specific
        workitem."""
        wis = wi.getGeneratedWorkItems()

        recipients = set()
        for wi in wis:
            if wi.state != 'active':
                continue
            if wi.activity_type == 'route':
                recipients.update(self.getRecipientsForWorkItem(wi))
            else:
                recipients.update(wi.listRelevantUsers())

        return list(recipients)


class RecipientCurrentAssignees(AbstractRecipent):
    """Recipient mode for notifying the assignee of the current workitem.

    This is meant to be used in the context of an email aspect. While it will
    work for an email work item, it doesn't make any sense there.
    """

    def getRecipientsForWorkItem(self, wi):
        """Returns list of users which are recipients for a specific
        workitem."""
        return wi.listRelevantUsers()


class RecipientPreviousAssignees(AbstractRecipent):
    """Recipient mode for notifying the assignee of the parent workitem."""

    def getRecipientsForWorkItem(self, wi):
        """Returns list of users which are recipients for a specific
        workitem."""
        wi = wi.getParent()
        if wi:
            return wi.listRelevantUsers()
        else:
            return []


class RecipientActualRole(AbstractRecipent):
    """Recipient mode for notifying users with one of the given roles."""

    def getRecipientsForWorkItem(self, wi):
        """Returns list of users with at least one of the given roles."""
        contentObject = wi.getContentObject()
        if contentObject is None:
            relevant = []
        else:
            relevant = Products.AlphaFlow.utils.listMembersWithLocalRoles(
                contentObject, self.roles)
        return list(relevant)

def _quoteAddressField(name, address, encoding):
    """Quote address field according to RFC 2822

    name ... real name of person
    address ... email address of the person
    encoding ... encoding used to encode name

    returns: string"""
    return '%s <%s>' % (email.Header.Header('%s' % name, encoding), address)


def _send_email(context, definition, work_items):
    portal_properties = getToolByName(context, 'portal_properties')
    wf_tool = getToolByName(context, 'workflow_manager')
    membertool = getToolByName(context, 'portal_membership')
    portal_url = getToolByName(context, 'portal_url')
    portal = portal_url.getPortalObject()
    workitem = context.getWorkItem()

    siteEncoding = portal_properties.site_properties.getProperty(
        'default_charset')

    template = wf_tool.email_templates[definition.template]
    subject_expr = definition.mailSubject
    subject_expr = "string:" + subject_expr
    subject = Products.AlphaFlow.utils.evaluateTales(
        subject_expr, workitem=workitem)
    mail_header_data = {
        'From': _quoteAddressField(portal_properties.email_from_name,
                                   portal_properties.email_from_address,
                                   siteEncoding),
        'To': '',
        'Errors-to': portal_properties.email_from_address,
        'Subject': email.Header.Header(subject, siteEncoding),
        'Content-Type': "text/plain; charset=%s" % siteEncoding,
        }
    recipients = []
    for mode in definition.recipient_modes:
        recipients.extend(mode.getRecipientsForWorkItem(workitem))
    email_recipients = set(recipients)

    # Send mail to all normal members
    for memberid in email_recipients:
        member = membertool.getMemberById(memberid)
        if member is None:
            # users which are defined outside of the portal
            continue
        address = member.getProperty('email')
        if not address:
            # XXX do not send email if member has no email address set.
            # XXX maybe we should log this.
            continue

        mail_variables = {'member': member,
                          'address': address,
                          'work_items': work_items}
        mail_body = template(context, context.REQUEST, **mail_variables)
        mail_header_data['To'] = _quoteAddressField(
            member.getProperty('fullname'),
            address,
            siteEncoding)
        mail = email.MIMEText.MIMEText(mail_body, 'plain', siteEncoding)
        for key, val in mail_header_data.items():
            mail[key] = val
        portal.MailHost._send(portal_properties.email_from_address,
                              member.getProperty('email'),
                              mail.as_string())

    # Send mail to all people that only have addresses:
    for address in context.getActivityConfiguration('recipients') or []:
        mail_variables = {'member': None,
                          'address': address,
                          'work_items': work_items}
        mail_body = template(context, context.REQUEST, **mail_variables)
        mail_header_data['To'] = address
        mail = email.MIMEText.MIMEText(mail_body, 'plain', siteEncoding)
        for key, val in mail_header_data.items():
            mail[key] = val
        portal.MailHost._send(portal_properties.email_from_address,
                              address,
                              mail.as_string())
