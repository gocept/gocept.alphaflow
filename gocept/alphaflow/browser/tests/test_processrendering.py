# Copyright (c) 2007 gocept gmbh & co. kg
# See also LICENSE.txt
# $Id$

import unittest

from Products.AlphaFlow.tests.AlphaFlowTestCase import AlphaFlowTestCase


class RenderingTest(AlphaFlowTestCase):

    interfaces_to_test = []

    def test_png_format(self):
        self._import_wf('../tests/workflows/permission.alf')
        pm = self.portal.workflow_manager
        test_process = pm.processes['test'].current()
        path = self._get_path(test_process) + "/graph.png"
        response = self.publish(path, basic="manager:secret")
        self.assertEquals("image/png", response.headers.get("content-type"))
        self.assertEquals('\x89PNG', response.body[0:4])

    def test_svg_format(self):
        self._import_wf('../tests/workflows/permission.alf')
        pm = self.portal.workflow_manager
        test_process = pm.processes['test'].current()
        path = self._get_path(test_process) + "/graph.svg"
        response = self.publish(path, basic="manager:secret")
        self.assertEquals("image/svg+xml", response.headers.get("content-type"))
        self.assertEquals('<?xm', response.body[0:4])

    def test_map_format(self):
        self._import_wf('../tests/workflows/permission.alf')
        pm = self.portal.workflow_manager
        test_process = pm.processes['test'].current()
        path = self._get_path(test_process) + "/map"
        response = self.publish(path, basic="manager:secret")
        self.assert_(
            response.headers.get("content-type").startswith("text/xml"))
        self.assertEquals('<map ', response.body[0:5])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RenderingTest))
    return suite
