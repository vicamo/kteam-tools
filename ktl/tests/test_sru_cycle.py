import sys
import unittest
from testfixtures       import (TempDirectory,
                                Replace,
                                test_datetime,
                               )

from datetime           import date

from ktl.sru_cycle      import (SruCycle,
                                SruCycleSpinEntry,
                               )

class TestSruCycleCore(unittest.TestCase):

    if sys.version_info[:3] > (3, 0):
        def assertItemsEqual(self, a, b):
            return self.assertCountEqual(a, b)

class TestSruCycle(TestSruCycleCore):

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
            self.assertTrue(isinstance(cycle, SruCycleSpinEntry))
            count += 1
        self.assertEqual(count, 2)

    def test_initialisation_url(self):
        with TempDirectory() as d:
            d.write('sru-cycle.yaml', self.data_yaml.encode('utf-8'))

            ks = SruCycle(url='file://' + d.getpath('sru-cycle.yaml'))

        count = 0
        for cycle in ks.cycles:
            self.assertTrue(isinstance(cycle, SruCycleSpinEntry))
            count += 1
        self.assertEqual(count, 2)

    def test_lookup_cycle(self):
        sc = SruCycle(data=self.data_yaml)
        cycle = sc.lookup_cycle('2018.05.21')

        self.assertEqual(cycle.name, '2018.05.21')
        self.assertEqual(cycle.release_date, date(2018, 6, 11))

    def test_cycles(self):
        sc = SruCycle(data=self.data_yaml)
        cycle_names = [ s.name for s in sc.cycles ]

        self.assertItemsEqual(cycle_names, self.data_cycle_names)


class TestSruCycleSpinEntry(TestSruCycleCore):

    def test_equal_true(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.01.02-1')
        spin2 = sc.lookup_spin('2018.01.02-1')

        self.assertEqual(spin1, spin2)

    def test_equal_false(self):
        data = """
        '2018.01.02':
        '2018.02.03':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.01.02-1')
        spin2 = sc.lookup_spin('2018.02.03-1')

        self.assertNotEqual(spin1, spin2)

    def test_equal_none(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.01.02-1')

        self.assertNotEqual(spin1, None)
        self.assertNotEqual(None, spin1)

    def test_lookup_spin_present_spin1(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.01.02-1')
        self.assertEqual(spin1.cycle, '2018.01.02')

    def test_lookup_spin_present_spin99(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.01.02-99')
        self.assertEqual(spin1.cycle, '2018.01.02')

    def test_lookup_spin_absent_spin1(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.02.03-1')
        self.assertIsNone(spin1)

    def test_lookup_spin_absent_spin1_allow_missing(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.02.03-1', allow_missing=True)
        self.assertEqual(spin1.cycle, '2018.02.03')

    def test_lookup_spin_present_spin99(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.01.02-99')
        self.assertEqual(spin1.cycle, '2018.01.02')

    def test_lookup_cycle_present(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_cycle('2018.01.02')
        self.assertEqual(spin1.cycle, '2018.01.02')

    def test_lookup_cycle_absent(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_cycle('2018.02.03')
        self.assertIsNone(spin1)

    def test_lookup_cycle_absent_allow_missing(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_cycle('2018.02.03', allow_missing=True)
        self.assertEqual(spin1.cycle, '2018.02.03')

    def test_known_present(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.01.02-1')
        self.assertTrue(spin1.known)

    def test_known_absent(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.02.03-1')
        self.assertIsNone(spin1)

    def test_known_absent_allow_missing(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin('2018.02.03-1', allow_missing=True)
        self.assertFalse(spin1.known)

    def test_release_date_present_valid(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        self.assertEqual(spin.release_date, date(2018, 2, 3))

    def test_release_date_present_empty(self):
        data = """
        '2018.01.02':
            release-date:
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        self.assertEqual(spin.release_date, None)

    def test_release_date_present_invalid(self):
        data = """
        '2018.01.02':
            release-date: 'next-monday'
        """
        sc = SruCycle(data=data)
        with self.assertRaises(ValueError):
            spin = sc.lookup_spin('2018.01.02-1')
            rdate = spin.release_date

    def test_release_date_absent(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        self.assertEqual(spin.release_date, None)

    def test_hold_present_true(self):
        data = """
        '2018.01.02':
            hold: true
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        self.assertTrue(spin.hold)

    def test_hold_present_false(self):
        data = """
        '2018.01.02':
            hold: false
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        self.assertFalse(spin.hold)

    def test_hold_present_empty(self):
        data = """
        '2018.01.02':
            hold:
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        self.assertFalse(spin.hold)

    def test_hold_absent(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        self.assertFalse(spin.hold)

    def test_hold_absent_in_unknown(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.02.03-1')

        self.assertIsNone(spin)

    def test_hold_absent_in_unknown_allow_missing(self):
        data = """
        '2018.01.02':
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.02.03-1', allow_missing=True)

        self.assertTrue(spin.hold)

    def test_ready_to_release_before(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        with Replace('ktl.sru_cycle.datetime', test_datetime(2018, 2, 1, 0, 0)):
            self.assertEqual(spin.ready_to_release, False)

    def test_ready_to_release_today(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        with Replace('ktl.sru_cycle.datetime', test_datetime(2018, 2, 3, 0, 0)):
            self.assertEqual(spin.ready_to_release, True)

    def test_ready_to_release_after(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        with Replace('ktl.sru_cycle.datetime', test_datetime(2018, 2, 5, 0, 0)):
            self.assertEqual(spin.ready_to_release, True)

    def test_ready_to_release_hold(self):
        data = """
        '2018.01.02':
            release-date: '2018-02-03'
            hold: true
        """
        sc = SruCycle(data=data)
        spin = sc.lookup_spin('2018.01.02-1')

        with Replace('ktl.sru_cycle.datetime', test_datetime(2018, 2, 5, 0, 0)):
            self.assertEqual(spin.ready_to_release, False)


if __name__ == '__main__':
    unittest.main()
