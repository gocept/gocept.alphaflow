##parameters=process_uid
# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# af_assign_process.py,v 1.5.6.2 2005/05/02 10:08:52 zagy Exp
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.config import UID_CATALOG
from Products.AlphaFlow.interfaces import ILifeCycleController
request = context.REQUEST

uids = getToolByName(context, UID_CATALOG)
process = uids(UID=process_uid)[0].getObject()
context.assignProcess(process.current())
instance = ILifeCycleController(context.getInstance())
instance.start("started through plone ui")

context.af_redirect_to_workitem_view(context.translate("Workflow started.",
                                                       domain="alphaflow"))
