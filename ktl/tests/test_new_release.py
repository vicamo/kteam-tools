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

    def test_hwe_parent(self):
        # focal:linux-riscv-5.15 works like that
        a = KernelVersion("5.15.0-1040.42~20.04.2", "5.15.0-90.91")
        b = KernelVersion("5.15.0-1041.43~20.04.1")
        a.bump()
        self.assertEqual(a, b)

        # when hwe-5.19 became the new parent, it worked like that
        a = KernelVersion("5.19.0-1040.42~20.04.2", "5.19.0-50.51~20.04.1")
        b = KernelVersion("5.19.0-1041.43~20.04.1")
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

        # If parent version is lower than version, it is ignored
        c = KernelVersion("50-20.3000U2", "42+answer")
        c.bump()
        self.assertEqual(c, KernelVersion("50-21.3001U1"))

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

    def test_lrm_lt(self):
        # Test lrm version < parent version
        a = KernelVersion("6.5.0-1.1", parent_version="6.5.0-2.2", package_type="lrm")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0-2.2"))

    def test_lrm_eq(self):
        # Test lrm version == parent version
        a = KernelVersion("6.5.0-2.2", parent_version="6.5.0-2.2", package_type="lrm")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0-2.2+1"))

    def test_lrm_gt(self):
        # Test lrm version > parent version
        a = KernelVersion("6.5.0-3.3+1", parent_version="6.5.0-3.3", package_type="lrm")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0-3.3+2"))

    def test_lrm_gt_bad1(self):
        # Test bad lrm version > parent version
        a = KernelVersion("6.5.0-4.4", parent_version="6.5.0-3.3", package_type="lrm")
        with self.assertRaises(ValueError):
            a.bump()

    def test_lrm_gt_bad2(self):
        # Test bad lrm version > parent version
        a = KernelVersion("6.5.0-4.4+1", parent_version="6.5.0-3.3", package_type="lrm")
        with self.assertRaises(ValueError):
            a.bump()

    def test_lrm_no_parent(self):
        a = KernelVersion("6.5.0-2.2", package_type="lrm")
        with self.assertRaises(ValueError):
            a.bump()

    def test_meta_old_lt_abi(self):
        a = KernelVersion("6.5.0.2.4", parent_version="6.5.0-3.6", package_type="meta")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0.3.5"))

    def test_meta_old_sameport(self):
        a = KernelVersion("6.5.0.26.26.1", parent_version="6.5.0-27.28.1", package_type="meta")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0.27.28.1"))

    def test_meta_old_sameport_upload_version(self):
        a = KernelVersion("6.5.0.27.28.1", parent_version="6.5.0-27.28.1", package_type="meta")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0.27.28.2"))

    def test_meta_old_eq_abi(self):
        a = KernelVersion("6.5.0.5.9", parent_version="6.5.0-5.6", package_type="meta")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0.5.10"))

    def test_meta_bp_fp_same_base(self):
        # Test backport meta version with same main package base version
        a = KernelVersion("6.5.0.9.9.1~22.04.1", parent_version="6.5.0-9.9.1~22.04.4", package_type="meta")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0.9.9.1~22.04.2"))

        # Test forwardport meta version with same main package base version
        b = KernelVersion("5.15.0.9.9+22.10.2", parent_version="5.15.0-9.9+22.10.4", package_type="meta")
        b.bump()
        self.assertEqual(b, KernelVersion("5.15.0.9.9+22.10.3"))

    def test_meta_bp_fp_new_base(self):
        # Test backport meta version with new main package base version
        a = KernelVersion("6.5.0.9.9.9~22.04.2", parent_version="6.5.0-10.10.3~22.04.5", package_type="meta")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0.10.10.3~22.04.1"))

        # Test forwardport meta version with new main package base version
        b = KernelVersion("5.15.0.9.9+22.10.1", parent_version="5.15.0-11.12+22.10.1", package_type="meta")
        b.bump()
        self.assertEqual(b, KernelVersion("5.15.0.11.12+22.10.1"))

    def test_main_sameport_backport(self):
        a = KernelVersion("6.5.0-26.26.1~22.04.1", parent_version="6.5.0-27.28.1", package_type="main")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0-27.28.1~22.04.1"))

    def test_main_parent_sameport_bump(self):
        a = KernelVersion("6.5.0-27.28.1~22.04.1", parent_version="6.5.0-27.28.2", package_type="main")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0-27.28.2~22.04.1"))

    def test_main_sameport_backport_reupload(self):
        a = KernelVersion("6.5.0-27.28.1~22.04.1", parent_version="6.5.0-27.28.1", package_type="main")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0-27.28.1~22.04.2"))

    def test_main_sameport(self):
        a = KernelVersion("6.5.0-26.26.1", parent_version="6.5.0-27.28", package_type="main")
        a.bump()
        self.assertEqual(a, KernelVersion("6.5.0-27.28.1"))
