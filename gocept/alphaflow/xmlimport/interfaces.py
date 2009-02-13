# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Interfaces related to the import and export process definitions from
resp. to ALF.
"""

import zope.interface


class IDOMImporter(zope.interface.Interface):
    """DOM importer

    Creates one or more workflow objects (e.g. a process, activity or
    similary) from a DOM node that comes from an ALF.

    """

    def __call__(dom_node):
        """Import the DOM node.

        Returns a sequence of objects.

        """


class IWorkflowAttribute(zope.interface.Interface):
    """Attribute on objects in workflow (activity, process, ...)

    data used for import and export
    """

    classAttr = zope.interface.Attribute("Name of the attribute in the python class.")
    domAttr = zope.interface.Attribute("Name of the attribute in the dom.")
    description = zope.interface.Attribute("Description for the attribute.")
    required = zope.interface.Attribute("Is this Attribute required?")
    encoding = zope.interface.Attribute("Encode value with this encoding before converting to "
                         "datatype. May be None if no encoding needed.")
    datatype = zope.interface.Attribute("Datatype of value as type.")
    vocabulary = zope.interface.Attribute("List or tuple of allowed values or None.")

    def apply(node, obj):
        """Apply the node's configuration to the object.
        """
