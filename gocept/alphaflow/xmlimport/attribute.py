# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
"""WorkflowAttribute definitions and helpers"""

import zope.interface

from Products.AlphaFlow import utils
from Products.AlphaFlow.exception import ConfigurationError
from Products.AlphaFlow.xmlimport.interfaces import IWorkflowAttribute
from Products.AlphaFlow.xmlimport.utils import \
    configure_attributes, import_child_elements

UNSET = object()


class WorkflowAttribute(object):
    """Attribute on objects in workflow (activity, process, ...)

    data used for import
    """

    zope.interface.implements(IWorkflowAttribute)

    classAttr = None
    domAttr = None
    description = ""
    required = False
    encoding = None
    datatype = unicode
    vocabulary = None

    def __init__(self, classAttr, domAttr, description,
                 required=False, encoding=None, datatype=unicode,
                 vocabulary=None):

        if not isinstance(classAttr, str):
            raise ValueError, "classAttr must be a string."
        self.classAttr = classAttr
        if not isinstance(domAttr, str):
            raise ValueError, "domAttr must be a string."
        self.domAttr = domAttr
        self.description = description
        if not isinstance(datatype, type):
            raise ValueError, "datatype must be a python type."
        self.datatype = datatype
        if not (isinstance(encoding, str) or encoding is None):
            raise ValueError, "encoding must be a string encoding or None."
        self.encoding = encoding
        if encoding is not None and datatype == unicode:
            raise ValueError, \
                  "If encoding is not None, datatype must not be unicode."
        if not isinstance(required, bool):
            raise ValueError, "required must be a boolean."
        self.required = required
        if not isinstance(vocabulary, (list, tuple, type(None))):
            raise ValueError, "vocabulary must be a list or None."
        self.vocabulary = vocabulary

    def __repr__(self):
        return "WorkflowAttribute(%s, %s, %s)" % (self.classAttr,
                                                  self.domAttr)

    def apply(self, node, obj):
        "Import this attribute from the given node to the object."
        input = UNSET
        if node.hasAttribute(self.domAttr):
            input = node.getAttribute(self.domAttr)
        if input is UNSET:
            if self.required:
                raise ConfigurationError(
                    "'%s' element requires attribute '%s'." %
                    (node.nodeName, self.domAttr))
            else:
                # Not required and no input given: just don't do anything.
                return

        # Preparatory steps
        if self.encoding is not None:
            input = input.encode(self.encoding)

        # Convert the input into the correct data type
        if self.datatype in [list, tuple]:
            value = self.datatype(utils.flexSplit(input))
            if not value:
                # XXX This allows giving no input even when input is required.
                return

        elif self.datatype == bool:
            try:
                value = utils.makeBoolFromUnicode(input)
            except ValueError:
                import sys
                raise ConfigurationError(str(sys.exc_info()[1]))
        else:
            # do not try to convert strings or empty values
            if not (issubclass(self.datatype, basestring) or input == ''):
                try:
                    value = self.datatype(input)
                except ValueError:
                    raise ConfigurationError, \
                          "%s.%s must be of %s" % (node.nodeName, self.domAttr,
                                                   self.datatype)
            else:
                value = input

            if value == '':
                return

        # After conversion: check for containment in vocabulary
        if self.vocabulary is not None and value not in self.vocabulary:
            raise ConfigurationError, \
                  "%s.%s must be one of %s" % (node.nodeName, self.domAttr,
                                               self.vocabulary)

        setattr(obj, self.classAttr, value)


class WorkflowAttributeList(WorkflowAttribute):
    """Imports child nodes as elements of one list attribute.

    If domAttr is set to anything `true`, then only import child nodes
    whose nodeName equals domAttr.

    """

    def apply(self, node, obj):
        "Import all child nodes as elements of one list attribute."
        setattr(obj, self.classAttr,
                self.datatype(import_child_elements(
                    node, obj, utils.flexSplit(self.domAttr))))


class ConfiguresAttribute(WorkflowAttribute):

    def apply(self, node, obj):
        if node.hasAttribute('configures_all'):
            setattr(obj, self.classAttr, None) # None is marker for "all"
        elif node.hasAttribute('configures'):
            super(ConfiguresAttribute, self).apply(node, obj)
        else:
            raise ConfigurationError(
                "%r: Attribute configures or configures_all needed." %
                node.nodeName)


class AssigneesAttribute(object):

    assigneesKind = (WorkflowAttribute(
        'assigneesKind', 'kind',
        'Defines the user assignment method, either "possible" or "actual".',
        required=True,
        vocabulary=['actual', 'possible']),)

    assigneesExpression = (WorkflowAttribute(
        'assigneesExpression', 'expression',
        'Tales Expression returning a list of member ids, may be None.'),)

    roles = (WorkflowAttribute(
        'roles', 'roles', 'Roles to compute which members are assignees',
        encoding='ascii', datatype=tuple),)

    groups = (WorkflowAttribute(
        'groups', 'groups', 'Groups to lookup which members are assignees',
        encoding='ascii', datatype=tuple),)

    def apply(self, node, obj):
        assignees = node.getElementsByTagName('assignees')
        # defaults will be used if assignees is empty
        if len(assignees) == 1:
            self._parse_assignee(assignees[0], obj)
        elif len(assignees) > 1:
            raise ConfigurationError(
                '<assignees> is only allowed once per activity.')

    def _parse_assignee(self, assignee, obj):
        has = assignee.hasAttribute
        get = assignee.getAttribute

        configure_attributes(assignee, obj, self.assigneesKind)
        kind = obj.assigneesKind

        statements = has('roles') + has('expression') + has('groups')

        if statements > 1:
            raise ConfigurationError(
                '<assignees> can only have one of roles or expression.')
        if statements < 1:
            raise ConfigurationError(
                '<assignees> must have one of roles or expression.')
        if has('roles'):
            configure_attributes(assignee, obj, self.roles)
        elif has('groups'):
            configure_attributes(assignee, obj, self.groups)
        elif has('expression'):
            if kind == 'possible':
                raise NotImplementedError(
                    "Can not combine `possible` and `expression`.")
            configure_attributes(assignee, obj, self.assigneesExpression)
