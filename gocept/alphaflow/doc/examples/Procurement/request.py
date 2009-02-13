# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

from AccessControl import getSecurityManager
import zope.interface

from Products.CMFCore.utils import getToolByName
from Products.Archetypes import public as atapi
from Products.ATContentTypes.content.base import ATCTContent as BaseContent
from Products.AlphaFlow import public as afapi
from Products.AlphaFlow.interfaces import IAlphaFlowed

from Products.Procurement import utils, config


class ProcurementRequest(afapi.AlphaFlowed, BaseContent):
    """A procurement request.
    """

    zope.interface.implement(IAlphaFlowed)

    schema = atapi.BaseSchema.copy() + atapi.Schema((
        atapi.StringField(
            "article",
            required=True,
            widget=atapi.StringWidget(
                label="Article",
                description="XXX",
                ),
            ),

        atapi.StringField(
            "account",
            required=False,
            vocabulary=config.accounts,
            widget=atapi.SelectionWidget(
                label="Account",
                description="XXX",
                ),
            ),

        atapi.TextField(
            "reason",
            required=False,
            widget=atapi.TextAreaWidget(
                label="Reason",
                description="XXX",
                ),
            ),

        atapi.FloatField(
            "price",
            required=True,
            ),

        atapi.DateTimeField(
            "due",
            required=True,
            ),
        ))

    schema["id"].widget.visible = \
    schema["title"].widget.visible = {
        'edit':'hidden',
        'view':'hidden'
        }
    schema["title"].required = False

    content_icon = "file_icon.gif" # XXX
    global_allow = 0
    archetype_name = "Procurement Request"
    portal_type = meta_type = "ProcurementRequest"

    include_default_actions = False
    actions = ({
            'id': 'view',
            'name': 'View',
            'action': 'string:${object_url}/base_view',
            },{
            'id': 'edit',
            'name': 'Edit',
            'action': 'string:${object_url}/base_edit',
            },
        )

    def Title(self):
        """DC title."""
        return self.getArticle()

    def manage_afterAdd(self, item, container):
        ProcurementRequest.inheritedAttribute('manage_afterAdd')(self, item, container)

        if len(self.getAllInstances()) > 0:
            return
        wftool = getToolByName(self, "workflow_manager")
        process = wftool.processes['procurement'].current()
        self.assignProcess(process)
        self.getInstance().start("Workflow started by request creation.")

    def getAccountGroup(self):
        """Return the name of the group responsible for this request's
        account."""
        return utils.getGroupFromAccount(self.getAccount())

atapi.registerType(ProcurementRequest)


class RequestManager(atapi.BaseFolder):
    """Container for procurement requests.
    """

    allowed_content_types = ["ProcurementRequest"]
    filter_content_types = True
    content_icon = "folder_icon.gif" # XXX
    global_allow = 1
    archetype_name = "Procurement Request System"
    portal_type = meta_type = "ProcurementRequestSystem"

    right_slots = ("here/portlet_worklist/macros/portlet",)

    include_default_actions = False
    actions = ({
            'id': 'view',
            'name': 'All requests',
            'action': 'string:${object_url}/all_requests',
            },{
            'id': 'requests_for_user',
            'name': 'My requests',
            'action': 'string:${object_url}/requests_for_user',
            },{
            'id': 'accepted_requests',
            'name': 'Accepted requests',
            'action': 'string:${object_url}/accepted_requests',
            },{
            'id': 'rejected_requests',
            'name': 'Rejected requests',
            'action': 'string:${object_url}/rejected_requests',
            },)

    def displayContentsTab(self):
        """Don't display the request manager's contents tab."""
        return False

    def getRequestsForCurrentUser(self):
        """Return a dict containing lists of request objects created by
        the current user for each DCWorkflow state.
        """
        user =  getSecurityManager().getUser().getUserName()
        requests = [r for r in self.contentValues("ProcurementRequest")
                    if r.Creator() == user]
        return self._groupRequestsByState(requests)

    def getAllRequests(self):
        """Return a dict containing lists of request objects created by
        the current user for each DCWorkflow state.
        """
        requests = self.contentValues("ProcurementRequest")
        return self._groupRequestsByState(requests)

    def getRequestsForState(self, state):
        """Return a dict containing lists of request objects in a
        certain DCWorkflow state for each account.
        """
        wf_tool = getToolByName(self, "portal_workflow")
        requests = [r for r in self.contentValues("ProcurementRequest")
                    if wf_tool.getInfoFor(r, "review_state") == state]

        rlists = {}

        if requests:
            for request in requests:
                account = request.getAccount()
                rlists.setdefault(account, []).append(request)

        rlists = [(v, rlists[k])
                  for k, v in config.accounts.items()
                  if rlists.has_key(k)]
        return rlists

    def _groupRequestsByState(self, requests):
        rlists = {}

        if requests:
            wf_tool = getToolByName(self, "portal_workflow")
            for request in requests:
                state = wf_tool.getInfoFor(request, "review_state")
                rlists.setdefault(state, []).append(request)

        rlists = [(v, rlists[k])
                  for k, v in config.wf_states.items()
                  if rlists.has_key(k)]
        return rlists

atapi.registerType(RequestManager)
