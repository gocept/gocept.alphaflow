from AccessControl import getSecurityManager
from Products.CMFCore.utils import getToolByName

cat = getToolByName(context, 'workflow_catalog')
userid = getSecurityManager().getUser().getId()
objects = cat(Creator=userid, meta_type="Instance", state="active")
objects = [ x.getObject() for x in objects ]
objects = [ x for x in objects if
            x is not None and x.getContentObject() is not None ]

return len(objects)
