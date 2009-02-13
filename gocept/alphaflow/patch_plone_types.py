# Copyright (c) 2004-2006 gocept. All rights reserved.
# See also LICENSE.txt
# $Id$

from Products.AlphaFlow.config import PATCH_PLONE_TYPES

import zope.interface

_already_patched = False


def patch_plone_types():
    if not PATCH_PLONE_TYPES:
        return
    from Products.ATContentTypes.content import document, event,\
                    file, image, link, newsitem, folder, topic
    from Products.AlphaFlow.workflowedobject import AlphaFlowed
    from Products.AlphaFlow.interfaces import IAlphaFlowed

    class ATDocument(AlphaFlowed, document.ATDocument):
        zope.interface.implements(IAlphaFlowed)

    class ATEvent(AlphaFlowed, event.ATEvent):
        zope.interface.implements(IAlphaFlowed)

    class ATFile(AlphaFlowed, file.ATFile):
        zope.interface.implements(IAlphaFlowed)

    class ATImage(AlphaFlowed, image.ATImage):
        zope.interface.implements(IAlphaFlowed)

    class ATLink(AlphaFlowed, link.ATLink):
        zope.interface.implements(IAlphaFlowed)

    class ATNewsItem(AlphaFlowed, newsitem.ATNewsItem):
        zope.interface.implements(IAlphaFlowed)

    class ATFolder(AlphaFlowed, folder.ATFolder):
        zope.interface.implements(IAlphaFlowed)

    class ATTopic(AlphaFlowed, topic.ATTopic):
        zope.interface.implements(IAlphaFlowed)

    class ATBTreeFolder(AlphaFlowed, folder.ATBTreeFolder):
        zope.interface.implements(IAlphaFlowed)

    document.ATDocument = ATDocument
    document.ATDocument.__module__ = \
                'Products.ATContentTypes.content.document'

    event.ATEvent = ATEvent
    event.ATEvent.__module__ = \
        'Products.ATContentTypes.content.event'

    file.ATFile = ATFile
    file.ATFile.__module__ = \
        'Products.ATContentTypes.content.file'

    image.ATImage = ATImage
    image.ATImage.__module__ = \
        'Products.ATContentTypes.content.image'

    link.ATLink = ATLink
    link.ATLink.__module__ = \
        'Products.ATContentTypes.content.link'

    newsitem.ATNewsItem = ATNewsItem
    newsitem.ATNewsItem.__module__ = \
        'Products.ATContentTypes.content.newsitem'

    folder.ATFolder = ATFolder
    folder.ATFolder.__module__ = \
        'Products.ATContentTypes.content.folder'

    folder.ATBTreeFolder = ATBTreeFolder
    folder.ATBTreeFolder.__module__ = \
        'Products.ATContentTypes.content.folder'

    topic.ATTopic = ATTopic
    topic.ATTopic.__module__ = \
        'Products.ATContentTypes.content.topic'

if not _already_patched:
    patch_plone_types()
    _already_patched = True
