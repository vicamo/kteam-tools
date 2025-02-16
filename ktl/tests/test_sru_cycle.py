import sys
import unittest
from testfixtures import (
    TempDirectory,
    Replace,
    test_datetime,
)

from datetime import date

from ktl.sru_cycle import (
    SruCycle,
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
    data_dict = {
        "2018.05.21": {
            "release-date": "2018-06-11",
        },
        "2018.06.11": {
            "release-date": "2018-07-02",
        },
    }
    data_cycle_names = ["2018.05.21", "2018.06.11"]

    def test_initialisation_data(self):
        ks = SruCycle(data=self.data_dict)

        count = 0
        for cycle in ks.cycles:
            self.assertTrue(isinstance(cycle, SruCycleSpinEntry))
            count += 1
        self.assertEqual(count, 2)

    def test_initialisation_url(self):
        with TempDirectory() as d:
            d.write("sru-cycle.yaml", self.data_yaml.encode("utf-8"))

            ks = SruCycle(data="local:" + d.getpath("sru-cycle.yaml"))

        count = 0
        for cycle in ks.cycles:
            self.assertTrue(isinstance(cycle, SruCycleSpinEntry))
            count += 1
        self.assertEqual(count, 2)

    def test_init_file_add_cycle(self):
        cycle_name = "2023.10.30"
        cycle_data = {"release-date": "2023-12-04", "stream": 1}
        with TempDirectory() as d:
            d.write("sru-cycle.yaml", self.data_yaml.encode("utf-8"))

            url = "local:" + d.getpath("sru-cycle.yaml")
            sc1 = SruCycle(data=url)
            sc1.add_cycle(SruCycleSpinEntry(cycle_name, data=cycle_data))
            sc1.write()

            sc2 = SruCycle(data=url)

        count = 0
        for cycle in sc2.cycles:
            self.assertTrue(isinstance(cycle, SruCycleSpinEntry))
            count += 1
        self.assertEqual(count, 3)

    def test_lookup_cycle(self):
        sc = SruCycle(data=self.data_dict)
        cycle = sc.lookup_cycle("2018.05.21")

        self.assertEqual(cycle.name, "2018.05.21")
        self.assertEqual(cycle.release_date, date(2018, 6, 11))

    def test_cycles(self):
        sc = SruCycle(data=self.data_dict)
        cycle_names = [s.name for s in sc.cycles]

        self.assertItemsEqual(cycle_names, self.data_cycle_names)

    def test_add_cycle_duplicate(self):
        sc = SruCycle(data=self.data_dict)
        new_cycle = SruCycleSpinEntry("2018.06.11", data=None)

        with self.assertRaises(ValueError):
            sc.add_cycle(new_cycle)

    def test_add_cycle_success(self):
        sc = SruCycle(data=self.data_dict)
        data = {"release_date": "2019.01.28", "stream": 1}
        new_cycle = SruCycleSpinEntry("2019.01.01", data=data)

        sc.add_cycle(new_cycle)
        cycle = sc.lookup_cycle(new_cycle.name)
        self.assertEqual(new_cycle.name, cycle.name)
        self.assertEqual(new_cycle.release_date, cycle.release_date)


class TestSruCycleSpinEntry(TestSruCycleCore):

    def test_equal_true(self):
        data = {
            "2018.01.02": {},
            "2018.01.02-1": {},
            "2018.01.02-2": {},
        }
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.01.02-1")
        spin2 = sc.lookup_spin("2018.01.02-1")

        self.assertEqual(spin1, spin2)

    def test_equal_false(self):
        data = {
            "2018.01.02": {},
            "2018.02.03": {},
        }
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.01.02-1")
        spin2 = sc.lookup_spin("2018.02.03-1")

        self.assertNotEqual(spin1, spin2)

    def test_equal_none(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.01.02-1")

        self.assertNotEqual(spin1, None)
        self.assertNotEqual(None, spin1)

    def test_lookup_spin_present_spin1(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.01.02-1")
        self.assertEqual(spin1.cycle, "2018.01.02")

    def test_lookup_spin_present_spin99(self):
        data = {"2018.01.02-99": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.01.02-99")
        self.assertEqual(spin1.cycle, "2018.01.02")

    def test_lookup_spin_absent_spin1(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.02.03-1")
        self.assertIsNone(spin1)

    def test_lookup_spin_absent_spin1_allow_missing(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.02.03-1", allow_missing=True)
        self.assertEqual(spin1.cycle, "2018.02.03")

    def test_lookup_spin_absent_spin99(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.01.03-99")
        self.assertIsNone(spin1)

    def test_lookup_cycle_present(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_cycle("2018.01.02")
        self.assertEqual(spin1.cycle, "2018.01.02")

    def test_lookup_cycle_absent(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_cycle("2018.02.03")
        self.assertIsNone(spin1)

    def test_lookup_cycle_absent_allow_missing(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_cycle("2018.02.03", allow_missing=True)
        self.assertEqual(spin1.cycle, "2018.02.03")

    def test_known_present(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.01.02-1")
        self.assertTrue(spin1.known)

    def test_known_absent(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.02.03-1")
        self.assertIsNone(spin1)

    def test_known_absent_allow_missing(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin1 = sc.lookup_spin("2018.02.03-1", allow_missing=True)
        self.assertFalse(spin1.known)

    def test_release_date_present_valid(self):
        data = {
            "2018.01.02": {
                "release-date": "2018-02-03",
            }
        }
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        self.assertEqual(spin.release_date, date(2018, 2, 3))

    def test_release_date_present_empty(self):
        data = {
            "2018.01.02": {
                "release-date": None,
            }
        }
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        self.assertEqual(spin.release_date, None)

    def test_release_date_present_invalid(self):
        data = {
            "2018.01.02": {
                "release-date": "next-monday",
            }
        }
        sc = SruCycle(data=data)
        with self.assertRaises(ValueError):
            spin = sc.lookup_spin("2018.01.02-1")
            rdate = spin.release_date

    def test_release_date_absent(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        self.assertEqual(spin.release_date, None)

    def test_hold_present_true(self):
        data = {
            "2018.01.02": {
                "hold": True,
            }
        }
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        self.assertTrue(spin.hold)

    def test_hold_present_false(self):
        data = {
            "2018.01.02": {
                "hold": False,
            }
        }
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        self.assertFalse(spin.hold)

    def test_hold_present_empty(self):
        data = {
            "2018.01.02": {
                "hold": None,
            }
        }
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        self.assertFalse(spin.hold)

    def test_hold_absent(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        self.assertFalse(spin.hold)

    def test_hold_absent_in_unknown(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.02.03-1")

        self.assertIsNone(spin)

    def test_hold_absent_in_unknown_allow_missing(self):
        data = {"2018.01.02": {}}
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.02.03-1", allow_missing=True)

        self.assertTrue(spin.hold)

    def test_ready_to_release_before(self):
        data = {
            "2018.01.02": {
                "release-date": "2018-02-03",
            }
        }
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        with Replace("ktl.sru_cycle.datetime", test_datetime(2018, 2, 1, 0, 0)):
            self.assertEqual(spin.ready_to_release, False)

    def test_ready_to_release_today(self):
        data = {
            "2018.01.02": {
                "release-date": "2018-02-03",
            }
        }
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        with Replace("ktl.sru_cycle.datetime", test_datetime(2018, 2, 3, 0, 0)):
            self.assertEqual(spin.ready_to_release, True)

    def test_ready_to_release_after(self):
        data = {
            "2018.01.02": {
                "release-date": "2018-02-03",
            }
        }
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        with Replace("ktl.sru_cycle.datetime", test_datetime(2018, 2, 5, 0, 0)):
            self.assertEqual(spin.ready_to_release, True)

    def test_ready_to_release_hold(self):
        data = {"2018.01.02": {"release-date:": "2018-02-03", "hold": True}}
        sc = SruCycle(data=data)
        spin = sc.lookup_spin("2018.01.02-1")

        with Replace("ktl.sru_cycle.datetime", test_datetime(2018, 2, 5, 0, 0)):
            self.assertEqual(spin.ready_to_release, False)

    def test_previous_cycle(self):
        data = {
            "d2023.11.01": {
                "previous-cycle": "d2023.10.05",
            },
            "2023.10.30": {
                "release-date": "2023-12-04",
            },
            "d2023.10.05": {},
            "s2023.10.02": {
                "start-date": "2023-10-30",
                "release-date": "2023-11-20",
            },
            "2023.10.02": {
                "release-date": "2023-10-30",
            },
        }
        sc = SruCycle(data=data)
        for spin, expect in (
            ("2023.10.30-1", "s2023.10.02"),
            ("s2023.10.02-1", "2023.10.02"),
            ("2023.10.02-1", None),
            ("d2023.11.01-1", "d2023.10.05"),
            ("d2023.10.05-1", None),
        ):
            with self.subTest(spin):
                if expect is not None:
                    expect = sc.lookup_cycle(expect)
                    self.assertNotEqual(None, expect)
                cycle = sc.lookup_spin(spin).previous_cycle
                if expect is None:
                    self.assertEqual(None, cycle)
                else:
                    self.assertEqual(expect.name, cycle.name)


if __name__ == "__main__":
    unittest.main()
