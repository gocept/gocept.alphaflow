# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase
from Products.AlphaFlow.activities.interfaces import \
    IEMailWorkItem, IEMailActivity, IEMailRecipientMode, INTaskWorkItem, \
    ILifeCycleController
from Products.AlphaFlow.activities.notify import \
        EMailWorkItem, EMailActivity, RecipientOwner, RecipientNextAssignees, \
        RecipientCurrentAssignees, RecipientActualRole
from Products.AlphaFlow.aspects.interfaces import IEMailAspect
from Products.AlphaFlow import config


class EmailTest(AlphaFlowTestCase):

    interfaces_to_test = [
        (IEMailWorkItem, EMailWorkItem),
        (IEMailActivity, EMailActivity),
        (IEMailRecipientMode, RecipientOwner),
        (IEMailRecipientMode, RecipientNextAssignees),
        (IEMailRecipientMode, RecipientActualRole),
        ]

    def _init_object(self, workflow='workflows/email.alf'):
        # Creates a simple workflow
        portal = self.portal
        self._create_test_users()
        self.loginAsPortalOwner()
        self._import_wf(workflow)

        wftool = getToolByName(portal, 'workflow_manager')

        self.login("author")
        mtool = getToolByName(portal, 'portal_membership')
        home = mtool.getHomeFolder("author")
        # Create object for instanciation of this process
        home.createObject("testdocument", "DummyContent")

        # Initialize the process
        doc = home.testdocument
        doc.manage_addLocalRoles('editor1', ['Reviewer'])
        doc.manage_addLocalRoles('editor2', ['Reviewer'])
        doc.manage_addLocalRoles('editor3', ['Editor'])
        doc.assignProcess(self.test_process)
        return doc

    def test_recipient_owner(self):
        def _test_recipients(mode, expected_ids, wi):
            got_ids = mode.getRecipientsForWorkItem(wi)
            got_ids.sort()
            expected_ids.sort()
            self.assertEquals(expected_ids, got_ids)

        doc = self._init_object()
        instance = doc.getInstance()
        ILifeCycleController(instance).start("comment")
        wi = instance.getWorkItems(state="ended")[0]
        self.assert_(ILifeCycleController(wi).completed, True)
        self.assert_(IEMailWorkItem.providedBy(wi))

        ro = RecipientOwner('ro')
        rna = RecipientNextAssignees('rna')
        rar = RecipientActualRole('rar')
        rar.roles = ('Editor',)

        _test_recipients(ro, ['author'], wi)
        _test_recipients(rna, ['editor2'], wi)
        _test_recipients(rar, ['editor3'], wi)

        wi = instance.getWorkItems(state="active")[0]
        self.assert_(INTaskWorkItem.providedBy(wi))
        wi_start = wi.objectValues()[0]
        self.assertEquals(config.CHECKPOINT_START,
                          wi_start.getDefinition().getId())
        wi_start_email = wi_start.objectValues()[0]
        self.assert_(IEMailAspect.providedBy(wi_start_email))
        rc = RecipientCurrentAssignees('rc')
        _test_recipients(rc, ['editor2'], wi_start_email)

    def test_template_folder(self):
        # Ensure that after setting up a process manager there is a template
        # folder for emails
        self.failUnless(getToolByName(self.portal,
                                      'workflow_manager').email_templates)

    def test_early_continue(self):
        doc = self._init_object(workflow='workflows/early_continue.alf')
        instance = doc.getInstance()
        ILifeCycleController(instance).start("comment")
        wis = instance.getWorkItems(state="active")
        self.assertEquals(1, len(wis))
        self.assertEquals("ntask", wis[0].activity_type)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(EmailTest))
    return suite
