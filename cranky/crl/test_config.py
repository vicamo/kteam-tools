#!/usr/bin/python3

import os
import sys
from testfixtures               import TempDirectory
import unittest

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'libs')))

from config                     import Config
from ktl.kernel_series          import KernelSeries


class TestConfig(unittest.TestCase):

    data_yaml = """
    simple: data
    paths:
        default: something
    clone:
        reference: '~/git2/linux-linus'
    """

    def test_config_data_simple_present(self):
        config = Config(data=self.data_yaml)
        self.assertNotEqual(config, None)

        data = config.lookup(['simple'])
        self.assertEqual(data, 'data')

    def test_config_data_paths_default_present(self):
        config = Config(data=self.data_yaml)
        self.assertNotEqual(config, None)

        data = config.lookup(['paths', 'default'])
        self.assertEqual(data, 'something')

    def test_config_data_simple2_absent(self):
        config = Config(data=self.data_yaml)
        self.assertNotEqual(config, None)

        data = config.lookup(['simple2'])
        self.assertIsNone(data)

    def test_config_filename_present(self):
        with TempDirectory() as d, unittest.mock.patch.dict(os.environ, {'HOME': '/non-existant'}):
            d.write('cranky.conf', self.data_yaml.encode('utf-8'))

            config = Config(filename=d.getpath('cranky.conf'))
            self.assertNotEqual(config, None)

            data = config.lookup(['simple'])
            self.assertEqual(data, 'data')

    def test_config_filename_absent(self):
        with TempDirectory() as d, unittest.mock.patch.dict(os.environ, {'HOME': '/non-existant'}):
            config = Config(filename=d.getpath('cranky.conf'))
            self.assertNotEqual(config, None)

            data = config.lookup(['simple'])
            self.assertIsNone(data)

    def test_config_home_cranky(self):
        with TempDirectory() as d, unittest.mock.patch.dict(os.environ, {'HOME': d.path}):
            d.write('.cranky', self.data_yaml.encode('utf-8'))

            config = Config()
            self.assertNotEqual(config, None)

            data = config.lookup(['simple'])
            self.assertEqual(data, 'data')

    def test_config_home_cranky_dot_yaml(self):
        with TempDirectory() as d, unittest.mock.patch.dict(os.environ, {'HOME': d.path}):
            d.write('.cranky.yaml', self.data_yaml.encode('utf-8'))

            config = Config()
            self.assertNotEqual(config, None)

            data = config.lookup(['simple'])
            self.assertEqual(data, 'data')

    def test_config_home_cranky(self):
        with TempDirectory() as d, unittest.mock.patch.dict(os.environ, {'HOME': d.path}):
            d.write('.cranky', self.data_yaml.encode('utf-8'))

            config = Config()
            self.assertNotEqual(config, None)

            data = config.lookup(['simple'])
            self.assertEqual(data, 'data')

    def test_config_home_cranky_dot_yaml(self):
        with TempDirectory() as d, unittest.mock.patch.dict(os.environ, {'HOME': d.path}):
            d.write('.cranky.yaml', self.data_yaml.encode('utf-8'))

            config = Config()
            self.assertNotEqual(config, None)

            data = config.lookup(['simple'])
            self.assertEqual(data, 'data')


if __name__ == '__main__':
    unittest.main()
