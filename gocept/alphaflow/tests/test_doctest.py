# -*- coding: latin1 -*-
# Copyright (c) 2005-2006 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$
import unittest

from Products.PloneTestCase import PloneTestCase
from Testing import ZopeTestCase

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager

from Products.AlphaFlow.Extensions import dcworkflow

PloneTestCase.setupPloneSite()

modules = [dcworkflow]

def test_suite():
    suite = unittest.TestSuite()

    def login(self, name):
        '''Logs in.'''
        uf = self.portal.acl_users
        user = uf.getUserById(name)
        if not hasattr(user, 'aq_base'):
            user = user.__of__(uf)
        newSecurityManager(None, user)

    def logout():
        '''Logs out.'''
        noSecurityManager()

    extraglobs = {
        'login': login,
        'logout': logout,
    }

    for mod in modules:
        suite.addTest(ZopeTestCase.FunctionalDocTestSuite(
            mod, extraglobs=extraglobs,
            test_class=PloneTestCase.FunctionalTestCase))
    return suite
