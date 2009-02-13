# Copyright (c) 2004-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

class AlphaFlowException(Exception):
    """Common base for all AlphaFlow exceptions"""

class ConfigurationError(AlphaFlowException):
    """raised in case of miss-configurations"""

class UnknownActivityError(AlphaFlowException):
    """Exception that signals that a referenced activity does not exist."""

class UnknownActivityTypeError(AlphaFlowException):
    """Exception that signals that a referenced activity type does not exist."""


class LifeCycleError(AlphaFlowException):
    """Exception that signals that error occured while going through
    the life cycle.

    """
