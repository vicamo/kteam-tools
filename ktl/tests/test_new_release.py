"""new_release unit tests
"""

import unittest
from ktl.new_release import KernelVersion


class TestNewRelease(unittest.TestCase):
    def test_simple(self):
        a = KernelVersion("5.15.0-48.50")
        b = KernelVersion("5.15.0-49.51")
        c = KernelVersion("5.15.0-49.51")
        a.bump()
        self.assertEqual(b, c)
        self.assertEqual(a, b)

    def test_suffix_only(self):
        a = KernelVersion("5.4.0-1048.50+fips1")
        b = KernelVersion("5.4.0-1048.50+fips2")
        c = KernelVersion("5.4.0-1048.50+fips3")
        a.bump()
        self.assertEqual(a, b)
        b.bump()
        self.assertEqual(b, c)

    def test_series_suffix_only(self):
        a = KernelVersion("4.15.0-30.33~16.04.11")
        b = KernelVersion("4.15.0-30.33~16.04.12")
        c = KernelVersion("4.15.0-30.33~16.04.13")
        a.bump()
        self.assertEqual(a, b)
        b.bump()
        self.assertEqual(b, c)

    def test_suffix_same_parent(self):
        a = KernelVersion("4.4.0-212.220~14.04.1", "4.4.0-212.220")
        b = KernelVersion("4.4.0-212.220~14.04.2")
        a.bump()
        self.assertEqual(a, b)

    def test_suffix_new_parent(self):
        a = KernelVersion("4.4.0-212.220~14.04.2", "4.4.0-213.221")
        b = KernelVersion("4.4.0-213.221~14.04.1")
        a.bump()
        self.assertEqual(a, b)

    def test_invalid(self):
        # Library does not validate upstream version
        a = KernelVersion("50-20.3000")
        a.bump()
        self.assertEqual(a, KernelVersion("50-21.3001"))

        # Parent version is totally ignored when there is no extra part
        b = KernelVersion("50-20.3000", "42+answer")
        b.bump()
        self.assertEqual(b, KernelVersion("50-21.3001"))

        # Parent version is not validated, extra part may start with anything
        # but a digit, and is appended to the parent version.
        c = KernelVersion("50-20.3000U2", "42+answer")
        c.bump()
        self.assertEqual(c, KernelVersion("42+answerU1"))

        # Extra part must end with a digit
        d = KernelVersion("50-20.3000U")
        with self.assertRaises(ValueError):
            d.bump()

        # Original version must have a dash and ABI and upload parts
        e = KernelVersion("42+answer")
        with self.assertRaises(ValueError):
            e.bump()

        # Original version must have a dash and ABI and upload parts
        f = KernelVersion("4.4.0-19")
        with self.assertRaises(ValueError):
            f.bump()
