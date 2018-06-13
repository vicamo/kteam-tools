import unittest
from testfixtures       import (TempDirectory,
                                Replace,
                                test_datetime,
                               )

from datetime           import date

from sru_cycle          import (SruCycle,
                                SruCycleEntry,
                               )

class TestSruCycle(unittest.TestCase):

    data_yaml = """
    '2018.05.21':
        release-date: '2018-06-11'
    '2018.06.11':
        release-date: '2018-07-02'
    """
    data_cycle_names = [ '2018.05.21', '2018.06.11' ]

    def test_initialisation_data(self):
        ks = SruCycle(data=self.data_yaml)

        count = 0
        for cycle in ks.cycles:
            self.assertTrue(isinstance(cycle, SruCycleEntry))
            count += 1
        self.assertEqual(count, 2)

    def test_initialisation_url(self):
        with TempDirectory() as d:
            d.write('sru-cycle.yaml', self.data_yaml)

            ks = SruCycle(url='file://' + d.getpath('sru-cycle.yaml'))

        count = 0
        for cycle in ks.cycles:
            self.assertTrue(isinstance(cycle, SruCycleEntry))
            count += 1
        self.assertEqual(count, 2)

    def test_lookup_cycle(self):
        sc = SruCycle(data=self.data_yaml)
        cycle = sc.lookup_cycle('2018.05.21')

        self.assertEqual(cycle.name, '2018.05.21')
        self.assertEqual(cycle.release_date, date(2018, 06, 11))

    def test_cycles(self):
        sc = SruCycle(data=self.data_yaml)
        cycle_names = [ s.name for s in sc.cycles ]

        self.assertItemsEqual(cycle_names, self.data_cycle_names)


class TestSruCycleEntry(unittest.TestCase):

    def test_equal_true(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        cycle1 = sc.lookup_cycle('2018.01.02')
        cycle2 = sc.lookup_cycle('2018.01.02')

        self.assertEqual(cycle1, cycle2)

    def test_equal_false(self):
        data = """
        '2018.01.02':
        '2018.02.03':
        """
        sc = SruCycle(data=data)
        cycle1 = sc.lookup_cycle('2018.01.02')
        cycle2 = sc.lookup_cycle('2018.02.03')

        self.assertNotEqual(cycle1, cycle2)

    def test_equal_none(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        cycle1 = sc.lookup_cycle('2018.01.02')

        self.assertNotEqual(cycle1, None)
        self.assertNotEqual(None, cycle1)

    def test_release_date_present_valid(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
        """
        sc = SruCycle(data=data)
        cycle = sc.lookup_cycle('2018.01.02')

        self.assertEqual(cycle.release_date, date(2018, 2, 3))

    def test_release_date_present_empty(self):
        data = """
        '2018.01.02':
            release-date:
        """
        sc = SruCycle(data=data)
        cycle = sc.lookup_cycle('2018.01.02')

        self.assertEqual(cycle.release_date, None)

    def test_release_date_present_invalid(self):
        data = """
        '2018.01.02':
            release-date: 'next-monday'
        """
        sc = SruCycle(data=data)
        cycle = sc.lookup_cycle('2018.01.02')
        with self.assertRaises(ValueError):
            rdate = cycle.release_date

    def test_release_date_absent(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        cycle = sc.lookup_cycle('2018.01.02')

        self.assertEqual(cycle.release_date, None)

    def test_ready_to_release_before(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
        """
        sc = SruCycle(data=data)
        cycle = sc.lookup_cycle('2018.01.02')

        with Replace('sru_cycle.datetime', test_datetime(2018, 2, 1, 0, 0)):
            self.assertEqual(cycle.ready_to_release, False)

    def test_ready_to_release_today(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
        """
        sc = SruCycle(data=data)
        cycle = sc.lookup_cycle('2018.01.02')

        with Replace('sru_cycle.datetime', test_datetime(2018, 2, 3, 0, 0)):
            self.assertEqual(cycle.ready_to_release, True)

    def test_ready_to_release_after(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
        """
        sc = SruCycle(data=data)
        cycle = sc.lookup_cycle('2018.01.02')

        with Replace('sru_cycle.datetime', test_datetime(2018, 2, 5, 0, 0)):
            self.assertEqual(cycle.ready_to_release, True)


if __name__ == '__main__':
    unittest.main()
