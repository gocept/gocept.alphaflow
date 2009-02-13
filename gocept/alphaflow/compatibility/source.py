##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Source widgets support

$Id$
"""

from itertools import imap

from zope.component import adapts, getMultiAdapter
from zope.interface import implements
from zope.schema.interfaces import IVocabularyTokenized, IIterableSource

import zope.app.form.browser.interfaces
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form.browser import \
     OrderedMultiSelectWidget, MultiSelectSetWidget


class IterableSourceVocabulary(object):

    """Adapts an iterable source into a legacy vocabulary.

    This can be used to wrap sources to make them usable with widgets that
    expect vocabularies. Note that there must be an ITerms implementation
    registered to obtain the terms.
    """

    implements(IVocabularyTokenized)
    adapts(IIterableSource);

    def __init__(self, source, request):
        self.source = source
        self.terms = getMultiAdapter(
            (source, request), zope.app.form.browser.interfaces.ITerms)

    def getTerm(self, value):
        return self.terms.getTerm(value)

    def getTermByToken(self, token):
        value = self.terms.getValue(token)
        return self.getTerm(value)

    def __iter__(self):
        return imap(
            lambda value: self.getTerm(value), self.source.__iter__())

    def __len__(self):
        return self.source.__len__()

    def __contains__(self, value):
        return self.source.__contains__(value)


class SourceMultiSelectSetWidget(MultiSelectSetWidget):
    """Provide a selection list for the set to be selected."""

    def __init__(self, field, source, request):
        super(SourceMultiSelectSetWidget, self).__init__(
            field, IterableSourceVocabulary(source, request), request)


class OrderedMultiSelectWidget(OrderedMultiSelectWidget):
    """A multi-selection widget with ordering support."""

    _missing = []
    template = ViewPageTemplateFile("orderedSelectionList.pt")

    def _toFieldValue(self, input):
        value = super(OrderedMultiSelectWidget, self)._toFieldValue(input)
        return tuple(value)


class SourceOrderedMultiSelectWidget(OrderedMultiSelectWidget):
    """A multi-selection widget with ordering support."""

    def __init__(self, field, source, request):
        super(SourceOrderedMultiSelectWidget, self).__init__(
            field, IterableSourceVocabulary(source, request), request)
