import sys
import unittest
from testfixtures       import (TempDirectory,
                                Replace,
                                test_datetime,
                               )

from datetime           import date

from ktl.swm_status     import SwmStatus


class TestSwmStatusCore(unittest.TestCase):

    if sys.version_info[:3] > (3, 0):
        def assertItemsEqual(self, a, b):
            return self.assertCountEqual(a, b)

class TestSwmStatus(TestSwmStatusCore):

    data_json = """{
        "trackers": {
            "123": {
                "cycle": "2020.03.16-1",
                "package": "linux"
            },
            "124": {
                "cycle": "202.03.16.-1",
                "package": "linux-deriv"
            }
        }
    }"""
    data_raw = {
            'trackers': {
                '123': None,
                '124': None,
            }
        }
    data_trackers = ['123', '124']

    def test_initialisation_data_json(self):
        ss = SwmStatus(data=self.data_json)

        self.assertEqual(sorted(ss.trackers.keys()), self.data_trackers)

    def test_initialisation_data_raw(self):
        ss = SwmStatus(data=self.data_raw)

        self.assertEqual(sorted(ss.trackers.keys()), self.data_trackers)

    def test_initialisation_url(self):
        with TempDirectory() as d:
            d.write('swm-status.json', self.data_json.encode('utf-8'))

            ss = SwmStatus(url='file://' + d.getpath('swm-status.json'))

        self.assertEqual(sorted(ss.trackers.keys()), self.data_trackers)


if __name__ == '__main__':
    unittest.main()
