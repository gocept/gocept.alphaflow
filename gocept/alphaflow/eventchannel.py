# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

from traceback import extract_stack

from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem

from Products.PluginIndexes.common.PluggableIndex import \
        PluggableIndexInterface
from Products.PluginIndexes.KeywordIndex.KeywordIndex import KeywordIndex
    
from Products.CMFCore.utils import getToolByName

from Products.AlphaFlow import config

_marker = object()

# XXX:
#manage_addProxyIndexForm = DTMLFile('ui/ProxyIndexAddForm', globals())

def manage_addEventChannelIndex(self, id, extra=None, REQUEST=None, **kw):
    """Add a event channel index"""

    return self.manage_addIndex(id,
                                'EventChannelIndex',
                                extra=extra,
                                REQUEST=REQUEST)

        
class EventChannelIndex(SimpleItem):

    __implements__ = PluggableIndexInterface

    meta_type = 'EventChannelIndex'

    manage_options = (
        
        {'label':'Overview',
         'action':'index_overview'},
        
        {'label':'Index',
         'action':'idx/manage_workspace'}
        
        )

    # XXX
    #index_overview = DTMLFile('ui/ProxyIndexView', globals())

    security = ClassSecurityInfo()

    def __init__(self, id, extra, caller=None):
        self.id = id

    def getId(self):
        return self.id

    def clear(self):
        return

    def getIndexSourceNames(self):
        return []

    def index_object(self, documentId, obj, threshold=None):
        return 1

    def unindex_object(self, documentId):
        pass

    def _apply_index(self, request, cid=''):
        return None
        
    def numObjects(self):
        return 0
    
    def __len__(self):
        """ len """
        return self.numObjects()

    def getEntryForObject(self, documentId, default=_marker):
        return None  # XXX?

    #needed to satisfy interface
    def indexSize(self):
        return self.numObjects()


def manage_addAllowedRolesAndUsersProxy(self, id, extra=None, REQUEST=None,
                                        **kw):
    """Add a event channel index"""

    return self.manage_addIndex(id,
                                'AllowedRolesAndUsersProxy',
                                extra=extra,
                                REQUEST=REQUEST)

class AllowedRolesAndUsersProxy(KeywordIndex):
    
    meta_type = config.mtAllowedRolesAndUsersProxy

    def index_object(self, documentId, obj, threshold=None):
        if not self._called_from_cache():
            alf = getToolByName(self, 'workflow_manager')
            alf.updateCacheByContent(obj)

        return AllowedRolesAndUsersProxy.inheritedAttribute('index_object')(
            self, documentId, obj, threshold)


    def _called_from_cache(self):
        stack = extract_stack()
        stack.reverse()  # innermost first
        for (filename, line_number, function_name, text) in stack:
            if function_name == 'updateCacheByWorkItem':
                return True
            elif function_name == 'updateCacheByInstance':
                return True

        return False


