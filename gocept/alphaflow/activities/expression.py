# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Execute a TALES expression -- activity and work item."""

import zope.interface 
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.Archetypes.public import registerType

from Products.AlphaFlow import config
from Products.AlphaFlow.workitem import BaseAutomaticWorkItem
from Products.AlphaFlow.activity import BaseAutomaticActivity
from Products.AlphaFlow.interfaces import IActivityClass, IWorkItemClass
from Products.AlphaFlow.activities.interfaces import \
    IExpressionActivity, IExpressionWorkItem

from Products.AlphaFlow.utils import evaluateTales, evaluateTalesAs


class ExpressionActivity(BaseAutomaticActivity):

    zope.interface.implements(IExpressionActivity)
    zope.interface.classProvides(IActivityClass)

    meta_type = "AlphaFlow Expression Activity"
    activity_type = "expression"
    icon = "misc_/AlphaFlow/expression"

    runAs = u"alphaflow/systemUser"
    expression = "nothing"

    schema_to_validate = IExpressionActivity


InitializeClass(ExpressionActivity)


class ExpressionWorkItem(BaseAutomaticWorkItem):

    zope.interface.implements(IExpressionWorkItem)
    zope.interface.classProvides(IWorkItemClass)

    security = ClassSecurityInfo()

    activity_type  = "expression"

    ######################
    # ITalesWorkItem

    security.declarePrivate('run')
    def run(self):
        """Performs the actual automatic activity"""
        evaluate_expression(self, self.getActivity())


InitializeClass(ExpressionWorkItem)
registerType(ExpressionWorkItem, config.PROJECTNAME)


def evaluate_expression(context, definition):
    workitem = context.getWorkItem()
    run_as = evaluateTales(definition.runAs, workitem=workitem)
    if isinstance(run_as, (str, unicode)):
        acl_users = context.getContentObject().acl_users
        run_as = acl_users.getUser(run_as)
    try:
        run_as.getUserName()
    except AttributeError:
        raise ValueError('The runAs expression %r did not return a proper '
                         'user but %r' % (definition.runAs, run_as))

    evaluateTalesAs(definition.expression, run_as, workitem=workitem)
