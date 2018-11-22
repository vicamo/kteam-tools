#!/usr/bin/python3

from datetime           import datetime
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

    def test_deployment_blackout_present_empty(self):
        data = """
            deployment-blackout:
        """
        sc = SwmConfig(data=data)

        self.assertIsNotNone(sc)
        now = datetime(year=2018, month=1, day=1, hour=10, minute=0)
        self.assertFalse(sc.in_blackout(now))

    def test_deployment_blackout_present_one(self):
        data = """
            deployment-blackout:
                - ['2018-01-02 08:00', '2018-01-07 08:00']
        """
        sc = SwmConfig(data=data)
        self.assertIsNotNone(sc)
        now = datetime(year=2018, month=1, day=1, hour=10, minute=0)
        self.assertFalse(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=2, hour=10, minute=0)
        self.assertTrue(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=8, hour=10, minute=0)
        self.assertFalse(sc.in_blackout(now))

    def test_deployment_blackout_present_one_edges(self):
        data = """
            deployment-blackout:
                - ['2018-01-02 08:00', '2018-01-07 08:00']
        """
        sc = SwmConfig(data=data)
        self.assertIsNotNone(sc)
        now = datetime(year=2018, month=1, day=2, hour=7, minute=59)
        self.assertFalse(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=2, hour=8, minute=0)
        self.assertTrue(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=7, hour=7, minute=59)
        self.assertTrue(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=7, hour=8, minute=0)
        self.assertFalse(sc.in_blackout(now))

    def test_deployment_blackout_present_multiple(self):
        data = """
            deployment-blackout:
                - ['2018-01-02 08:00', '2018-01-07 08:00']
                - ['2018-01-09 08:00', '2018-01-12 08:00']
        """
        sc = SwmConfig(data=data)
        self.assertIsNotNone(sc)
        now = datetime(year=2018, month=1, day=1, hour=10, minute=0)
        self.assertFalse(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=2, hour=10, minute=0)
        self.assertTrue(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=8, hour=10, minute=0)
        self.assertFalse(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=9, hour=10, minute=0)
        self.assertTrue(sc.in_blackout(now))
        now = datetime(year=2018, month=1, day=12, hour=10, minute=0)
        self.assertFalse(sc.in_blackout(now))

    def test_deployment_blackout_short_entry(self):
        data = """
            deployment-blackout:
                - '2018-01-01 10:00'
        """
        with self.assertRaises(SwmConfigError):
            sc = SwmConfig(data=data)

    def test_deployment_blackout_junk_start_entry(self):
        data = """
            deployment-blackout:
                - ['junk', '2018-01-07 08:00']
        """
        with self.assertRaises(SwmConfigError):
            sc = SwmConfig(data=data)

    def test_deployment_blackout_junk_end_entry(self):
        data = """
            deployment-blackout:
                - ['2018-01-02 08:00', 'junk']
        """
        with self.assertRaises(SwmConfigError):
            sc = SwmConfig(data=data)

if __name__ == '__main__':
    unittest.main()
