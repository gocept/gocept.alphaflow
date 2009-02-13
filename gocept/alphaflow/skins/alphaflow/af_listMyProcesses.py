from AccessControl import getSecurityManager
from Products.CMFCore.utils import getToolByName

cat = getToolByName(context, 'workflow_catalog')
userid = getSecurityManager().getUser().getId()

objects = [ x.getObject() for x in cat(Creator=userid, meta_type="Instance", state="active")]
objects = filter(lambda x: x is not None and x.getContentObject() is not None, objects)

data = []

for object in objects:
    request = {}
    content = object.getContentObject()
    request['object_title'] = content.title_or_id()
    request['object_icon'] = content.getIcon()
    request['url'] = content.absolute_url()
    request['workitems'] = []
    request['users'] = []
    for workitem in object.getWorkItems():
        request['users'].extend(workitem.listRelevantUsers())
        request['workitems'].append(workitem.getActivity().title_or_id())

    # Make users unique
    users_ = []
    for user in request['users']:
        if user not in users_:
            users_.append(user)
    request['users'] = ', '.join(users_)

    request['workitems'] = ', '.join(request['workitems'])

    data.append(request)
return data


