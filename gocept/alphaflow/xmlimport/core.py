# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""Core components that drive the import/export"""

from xml.dom import minidom

import zope.interface
import zope.component

from Products.AlphaFlow.process import ProcessVersion
from Products.AlphaFlow.interfaces import \
     IWorkflowImporter
from Products.AlphaFlow.xmlimport.interfaces import IDOMImporter
from Products.AlphaFlow.xmlimport.attribute import WorkflowAttribute
from Products.AlphaFlow.xmlimport.utils import \
    configure_attributes, get_element_children


class XMLImporter(object):
    """Import AlphaFlow processes from XML."""

    zope.interface.implements(IWorkflowImporter)

    def __call__(self, xmlfile):
        """Parse given XML and import the process."""
        if not hasattr(xmlfile, "read"):
            raise ValueError("Only files are allowed for importing XML data.")
        wf = minidom.parse(xmlfile).documentElement
        assert wf.tagName == "workflow", "This is not a workflow definition"
        process_importer = zope.component.getUtility(
            IDOMImporter, name=wf.nodeName)
        (process,) = process_importer(wf)
        return process


class ProcessVersionImporter(object):

    zope.interface.implements(IDOMImporter)

    attributes = (
        WorkflowAttribute('id', 'id',
                          'Id of the process',
                          encoding="utf-8", datatype=str),
        WorkflowAttribute('title', 'title',
                          'Title of this process definition.'),
        WorkflowAttribute('startActivity', 'startActivity',
                          'List of activity ids to instantiate at start.',
                          encoding='ascii', datatype=tuple),
        WorkflowAttribute('description', 'description',
                          'Description of this process definition.'),
        WorkflowAttribute('roles', 'onlyAllowRoles',
                          'Only members with this roles my start this workflow.',
                          encoding='ascii', datatype=list),
        WorkflowAttribute('object_name', 'object_name',
                          'Name the content object is bound to in expressions.',
                          encoding='ascii', datatype=str),
        )

    def __call__(self, process_node):
        process = ProcessVersion()

        # Configure the process' simple attributes
        configure_attributes(process_node, process, self.attributes)

        # Import all activities
        for node in get_element_children(process_node):
            activity_importer = zope.component.getAdapter(
                process, IDOMImporter, name=node.nodeName)
            for activity in activity_importer(node):
                process[activity.getId()] = activity

        return [process]
