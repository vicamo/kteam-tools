#!/usr/bin/python3

import os
import sys
from testfixtures       import (
                            TempDirectory,
                            Replace,
                            test_datetime,
                            )
import unittest
import yaml

#sys.path.append(os.path.realpath(os.path.join(os.path.dirname(sys.argv[0]), '..', '..', 'py3')))
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(sys.argv[0]), '..')))

from swm_config         import (
                            SwmConfig,
                            SwmConfigError,
                            )

class TestSwmConfigCore(unittest.TestCase):

    if sys.version_info[:3] > (3, 0):
        def assertItemsEqual(self, a, b):
            return self.assertCountEqual(a, b)


class TestSwmConfig(TestSwmConfigCore):

    data_yaml = """
        gcp-nvidia-packages: true
    """
    def test_initialisation_direct(self):
        data = yaml.safe_load(self.data_yaml)
        sc = SwmConfig(data=data)

        self.assertIsNotNone(sc)

    def test_initialisation_data(self):
        sc = SwmConfig(data=self.data_yaml)

        self.assertIsNotNone(sc)

    def test_initialisation_data_empty(self):
        data = ""
        sc = SwmConfig(data=data)

        self.assertIsNotNone(sc)

    def test_gcp_nvidia_packages_absent(self):
        data = ""
        sc = SwmConfig(data=data)

        self.assertIsNotNone(sc)
        self.assertFalse(sc.gcp_nvidia_packages)

    def test_gcp_nvidia_packages_present_false(self):
        data = "gcp-nvidia-packages: false"
        sc = SwmConfig(data=data)

        self.assertIsNotNone(sc)
        self.assertFalse(sc.gcp_nvidia_packages)

    def test_gcp_nvidia_packages_present_true(self):
        data = "gcp-nvidia-packages: true"
        sc = SwmConfig(data=data)

        self.assertIsNotNone(sc)
        self.assertTrue(sc.gcp_nvidia_packages)

if __name__ == '__main__':
    unittest.main()
