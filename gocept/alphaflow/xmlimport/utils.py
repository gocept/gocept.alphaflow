# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Helper functions that support the import/export"""


import zope.component

from Products.AlphaFlow.exception import ConfigurationError
import Products.AlphaFlow.utils
import Products.AlphaFlow.xmlimport.interfaces


def configure_attributes(node, obj, schema):
    "Configure attributes on this obj as given by the schema"
    for attr in schema:
        attr.apply(node, obj)


def get_element_children(dom_node):
    for node in dom_node.childNodes:
        if node.nodeType == node.ELEMENT_NODE:
            yield node


def import_child_elements(node, context, node_names=None, ignore=(),
                          default=None):
    seen_ids = set(context.objectIds())
    if default and default.getId():
        seen_ids.remove(default.getId())
    children = []
    for node in get_element_children(node):
        if (node_names is not None and node.nodeName not in node_names
            or node.nodeName in ignore):
            continue
        element_importer = zope.component.getAdapter(context,
            Products.AlphaFlow.xmlimport.interfaces.IDOMImporter,
            name=node.nodeName)
        for element in element_importer(node, default):
            element_id = getattr(element, "id", None)
            if element_id:
                if element_id in seen_ids:
                    raise ConfigurationError(
                        "Multiple element id: %s" % element_id)
                else:
                    seen_ids.add(element_id)
            children.append(element)
    return children


def add_child_elements(node, context, name):
    for child in import_child_elements(node, context):
        if not getattr(child, "id", None):
            child.id = Products.AlphaFlow.utils.generateUniqueId(name)
        context._setObject(child.getId(), child)
