import sys
import unittest
from testfixtures       import (TempDirectory,
                                Replace,
                                test_datetime,
                               )

from datetime           import date

from swm_status         import SwmStatus


class TestSwmStatusCore(unittest.TestCase):

    if sys.version_info[:3] > (3, 0):
        def assertItemsEqual(self, a, b):
            return self.assertCountEqual(a, b)

class TestSwmStatus(TestSwmStatusCore):

    data_yaml = """
    trackers:
        '123':
            cycle: 2020.03.16-1
            package: linux
        '124':
            cycle: 2020.03.16-1
            package: linux-deriv
    """
    data_trackers = ['123', '124']

    def test_initialisation_data(self):
        ss = SwmStatus(data=self.data_yaml)

        self.assertEqual(sorted(ss.trackers.keys()), self.data_trackers)

    def test_initialisation_url(self):
        with TempDirectory() as d:
            d.write('swm-status.yaml', self.data_yaml.encode('utf-8'))

            ss = SwmStatus(url='file://' + d.getpath('swm-status.yaml'))

        self.assertEqual(sorted(ss.trackers.keys()), self.data_trackers)


if __name__ == '__main__':
    unittest.main()
