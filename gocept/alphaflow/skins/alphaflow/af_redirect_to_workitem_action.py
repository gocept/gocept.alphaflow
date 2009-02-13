# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

from Products.AlphaFlow.utils import urlAppendToQueryString

request = context.REQUEST
response = request.RESPONSE
message = request.get('portal_status_message', 'Performed work item action')


selected_action = context.getAction()

try:
    action = context.getActionById(selected_action).url
except KeyError:
    # No action was selected. Just return to the content object.
    content_object = context.getContentObject()
    if content_object is None:
        # redirect to self
        content_object = context
    action = content_object.absolute_url()+"/view"

url = urlAppendToQueryString(action,
                             "portal_status_message=%s" % message)

return response.redirect(url)
