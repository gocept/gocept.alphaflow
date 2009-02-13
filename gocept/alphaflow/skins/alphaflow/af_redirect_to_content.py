# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

request = context.REQUEST
response = request.RESPONSE
message = request.get('portal_status_message', '')

content_object = context.getContentObject()
if content_object is None:
    # redirect to self
    content_object = context

if context.state == 'initiated':
    context.start('Auto start after editing config ...')

return response.redirect('%s/view?portal_status_message=%s' % (
    content_object.absolute_url(), message))

