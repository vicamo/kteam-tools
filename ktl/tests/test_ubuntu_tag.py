"""ubuntu_tag unit tests
"""

import json
import unittest

from ktl.ubuntu_tag import UbuntuTag, Version


class TestVersion(unittest.TestCase):
    """Version unit tests"""

    def test_equal(self):
        """Test implicit and explicit equality interfaces"""
        # Setup
        a = Version(1, 0)
        b = Version(1, 0)
        c = Version(1, 1)

        # Assert - implicit
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

        # Assert - explicit
        self.assertTrue(a == b)
        self.assertFalse(a != b)

    def test_hash(self):
        """Test implicit and explicit hash interfaces
        Equal objects should have the same hash
        """
        # Setup
        a = Version(2, 0)
        b = Version(2, 0)

        # Assert - implicit
        data = set((a, b))
        self.assertEqual(len(data), 1)

        # Assert - explicit
        self.assertEqual(hash(a), hash(b))

    def test_compare(self):
        """Test comparison interface"""
        # Setup
        a = Version(1, 0)
        b = Version(1, 1)
        c = Version(1, 1, 1)
        d = Version(2, 2, 2)

        # Assert - explicit so we know the __lt/gt/le/ge__ interfaces are called
        self.assertTrue(d > a)
        self.assertTrue(d >= a)
        self.assertTrue(a < d)
        self.assertTrue(a <= d)
        self.assertTrue(b > a)
        self.assertTrue(b >= a)
        self.assertTrue(a < b)
        self.assertTrue(a <= b)
        self.assertTrue(c > b)
        self.assertTrue(c >= b)
        self.assertTrue(b < c)
        self.assertTrue(b <= c)

    def test_ordering(self):
        """Implicit list ordering test"""
        # Setup
        a = Version(1, 0)
        b = Version(1, 1)
        c = Version(1, 1, 1)
        d = Version(2, 2, 2)
        data = [d, b, a, c]
        expect = [a, b, c, d]

        # Execute
        actual = sorted(data)

        # Assert
        self.assertEqual(actual, expect)

    from_str_data = (
        ("1", None),
        ("a", None),
        ("a.b", None),
        ("1.b", None),
        ("1.2.b", None),
        ("1.2", Version(1, 2)),
        ("1.2.3", Version(1, 2, 3)),
    )

    def test_from_str(self):
        """Test string parse helper"""
        for value, expect in self.from_str_data:
            with self.subTest(value):
                # Execute
                version = Version.from_str(value)
                # Assert
                self.assertEqual(version, expect)

    def test_from_str_raise(self):
        """Test string parse helper with raise-error"""
        for value, expect in self.from_str_data:
            # We only want test inputs that will fails
            if expect:
                continue

            with self.subTest(value):
                with self.assertRaises(ValueError):
                    # Execute
                    _ = Version.from_str(value, raise_on_error=True)


class TestUbuntuTagParser(unittest.TestCase):
    """UbuntuTag parser tests"""

    @unittest.skip("debugging test")
    def test_all(self):
        all_tags_file = ""
        with open(all_tags_file) as f:
            for raw_tag in f:
                tag = UbuntuTag(raw_tag)
                print(repr(tag))

    @unittest.skip("debugging test")
    def test_single(self):
        """Test harness for single tag"""
        raw_tag = ""
        tag = UbuntuTag(raw_tag)
        self.fail(repr(tag))

    good_test_cases = (
        # Simplest tag possible
        (
            "Ubuntu-5.4.0-1057.57",
            {
                "raw_tag": "Ubuntu-5.4.0-1057.57",
                "package": "",
                "kernel": str(Version(5, 4)),
                "ubuntu": str(Version(1057, 57)),
                "abi": 1057,
                "upload": 57,
                "deb": 0,
                "series": "",
                "extra": [],
                "respin": str(Version(0, 0)),
            },
        ),
        # Simplest tag possible but in meta form
        (
            "Ubuntu-5.4.0.1057.57",
            {
                "raw_tag": "Ubuntu-5.4.0.1057.57",
                "package": "",
                "kernel": str(Version(5, 4)),
                "ubuntu": str(Version(1057, 57)),
                "abi": 1057,
                "upload": 57,
                "deb": 0,
                "series": "",
                "extra": [],
                "respin": str(Version(0, 0)),
            },
        ),
        # Simple package name
        (
            "Ubuntu-aws-5.4.0-1057.57",
            {
                "raw_tag": "Ubuntu-aws-5.4.0-1057.57",
                "package": "aws",
                "kernel": str(Version(5, 4)),
                "ubuntu": str(Version(1057, 57)),
                "abi": 1057,
                "upload": 57,
                "deb": 0,
                "series": "",
                "extra": [],
                "respin": str(Version(0, 0)),
            },
        ),
        # Complex package name
        (
            "Ubuntu-aws-5.4-5.4.0-1057.57",
            {
                "raw_tag": "Ubuntu-aws-5.4-5.4.0-1057.57",
                "package": "aws-5.4",
                "kernel": str(Version(5, 4)),
                "ubuntu": str(Version(1057, 57)),
                "abi": 1057,
                "upload": 57,
                "deb": 0,
                "series": "",
                "extra": [],
                "respin": str(Version(0, 0)),
            },
        ),
        # Complex package name, non-zero debian build
        (
            "Ubuntu-aws-5.4-5.4.0-1057.57.1",
            {
                "raw_tag": "Ubuntu-aws-5.4-5.4.0-1057.57.1",
                "package": "aws-5.4",
                "kernel": str(Version(5, 4)),
                "ubuntu": str(Version(1057, 57, 1)),
                "abi": 1057,
                "upload": 57,
                "deb": 1,
                "series": "",
                "extra": [],
                "respin": str(Version(0, 0)),
            },
        ),
        # Complex package name, non-zero debian build, YY.MM series
        (
            "Ubuntu-gke-5.15-5.15.0-1020.25_20.04",
            {
                "raw_tag": "Ubuntu-gke-5.15-5.15.0-1020.25_20.04",
                "package": "gke-5.15",
                "kernel": str(Version(5, 15)),
                "ubuntu": str(Version(1020, 25)),
                "abi": 1020,
                "upload": 25,
                "deb": 0,
                "series": "20.04",
                "extra": [],
                "respin": str(Version(0, 0)),
            },
        ),
        # Complex package name, non-zero debian build, full series
        (
            "Ubuntu-gke-5.15-5.15.0-1020.25_20.04.1",
            {
                "raw_tag": "Ubuntu-gke-5.15-5.15.0-1020.25_20.04.1",
                "package": "gke-5.15",
                "kernel": str(Version(5, 15)),
                "ubuntu": str(Version(1020, 25)),
                "abi": 1020,
                "upload": 25,
                "deb": 0,
                "series": "20.04.1",
                "extra": [],
                "respin": str(Version(0, 0)),
            },
        ),
        # Respin tag
        (
            "Ubuntu-azure-fde-5.15.0-1008.9_20.04.1+1",
            {
                "raw_tag": "Ubuntu-azure-fde-5.15.0-1008.9_20.04.1+1",
                "package": "azure-fde",
                "kernel": str(Version(5, 15)),
                "ubuntu": str(Version(1008, 9)),
                "abi": 1008,
                "upload": 9,
                "deb": 0,
                "series": "20.04.1",
                "extra": ["1"],
                "respin": str(Version(1, 0)),
            },
        ),
        # Info tag and respin tag
        (
            "Ubuntu-azure-fde-5.15.0-1008.9_20.04.1+cvm1.1+1",
            {
                "raw_tag": "Ubuntu-azure-fde-5.15.0-1008.9_20.04.1+cvm1.1+1",
                "package": "azure-fde",
                "kernel": str(Version(5, 15)),
                "ubuntu": str(Version(1008, 9)),
                "abi": 1008,
                "upload": 9,
                "deb": 0,
                "series": "20.04.1",
                "extra": ["cvm1.1", "1"],
                "respin": str(Version(1, 0)),
            },
        ),
        # Info tag and complex respin tag
        (
            "Ubuntu-azure-fde-5.15.0-1008.9_20.04.1+signed+cvm1.2.3",
            {
                "raw_tag": "Ubuntu-azure-fde-5.15.0-1008.9_20.04.1+signed+cvm1.2.3",
                "package": "azure-fde",
                "kernel": str(Version(5, 15)),
                "ubuntu": str(Version(1008, 9)),
                "abi": 1008,
                "upload": 9,
                "deb": 0,
                "series": "20.04.1",
                "extra": ["signed", "cvm1.2.3"],
                "respin": str(Version(1, 2, 3)),
            },
        ),
    )

    def test_parser(self):
        """Exercise parameterized tests from good_test_cases"""
        for raw_tag, expect in self.good_test_cases:
            with self.subTest(raw_tag):
                # Execute
                tag = UbuntuTag(raw_tag)
                # Assert
                actual_json = repr(tag)
                expect_json = json.dumps(expect, indent=4)
                self.assertEqual(actual_json, expect_json)

    bad_test_cases = (
        None,
        "",
        "v5.19",
        "5.15.0-34.35",
        "Ubuntu",
        "Ubuntu-" "Ubuntu-hwe-5.17",
        "Ubuntu-hwe-5.17.0-1",
        "Ubuntu-hwe-5.17-5.17.0-1",
        "Ubuntu-hwe-5.17-5.17.0.1",
        "Ubuntu-hwe-5.17-5.17.0.1.X",
    )

    def test_parser_fail_no_raise(self):
        """Exercise bad format detection"""
        for raw_tag in self.bad_test_cases:
            with self.subTest(raw_tag):
                # Execute
                tag = UbuntuTag.from_str(raw_tag)
                # Assert
                self.assertIsNone(tag)

    def test_parser_fail_raise(self):
        """Exercise bad format detection"""
        for raw_tag in self.bad_test_cases:
            with self.subTest(raw_tag):
                with self.assertRaises(ValueError):
                    _ = UbuntuTag.from_str(raw_tag, raise_on_error=True)


class TestUbuntuTagCompare(unittest.TestCase):
    """Test tag comparison cases"""

    def test_obvious_relations(self):
        """Test cases where a<b<c"""
        # Setup
        a = UbuntuTag("Ubuntu-5.15.0-54.60")
        b = UbuntuTag("Ubuntu-5.15.0-56.62")
        c = UbuntuTag("Ubuntu-5.15.0-57.63")

        # Assert
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertGreater(c, a)

    def test_simple_respins(self):
        """Test cases where a<b<c based on respin syntax"""
        # Setup
        a = UbuntuTag("Ubuntu-5.15.0-54.60")
        b = UbuntuTag("Ubuntu-5.15.0-54.60+1")
        c = UbuntuTag("Ubuntu-5.15.0-54.60+2")

        # Assert
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertGreater(c, a)

    def test_complex_respins(self):
        """Test cases where a<b<c based on +extra +respin syntax"""
        # Setup
        a = UbuntuTag("Ubuntu-5.15.0-54.60+signed1")
        b = UbuntuTag("Ubuntu-5.15.0-54.60+signed2")
        c = UbuntuTag("Ubuntu-5.15.0-54.60+signed3")

        # Assert
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertGreater(c, a)

    def test_complex_dot_respins(self):
        """Test cases where a<b<c based on +extra +respin dot syntax"""
        # Setup
        a = UbuntuTag("Ubuntu-5.15.0-54.60+signed")
        b = UbuntuTag("Ubuntu-5.15.0-54.60+signed+1.2")
        c = UbuntuTag("Ubuntu-5.15.0-54.60+signed+cvm1.3")

        # Assert
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertGreater(c, a)

    def test_series_complex_dot_respins(self):
        """Test cases where a<b<c based on +extra +respin dot syntax"""
        # Setup
        a = UbuntuTag("Ubuntu-5.15.0-54.60_20.04.1+signed")
        b = UbuntuTag("Ubuntu-5.15.0-54.60_20.04.1+signed+1.2")
        c = UbuntuTag("Ubuntu-5.15.0-54.60_20.04.1+signed+cvm2")

        # Assert
        self.assertLess(a, b)
        self.assertLess(b, c)
        self.assertGreater(c, a)

    def test_series_complex_dot_respins_extra(self):
        """Test cases where a == b on +extra +respin dot syntax"""
        # Setup
        a = UbuntuTag("Ubuntu-5.15.0-54.60_20.04.1+signed+cvm1.2")
        b = UbuntuTag("Ubuntu-5.15.0-54.60_20.04.1+1.2")

        # Assert
        self.assertEqual(a, b)

    def test_non_comparable_package(self):
        """Ensure tags from different packages cannot be compared"""
        # Setup
        a = UbuntuTag("Ubuntu-lowlatency-5.15.0-21.21")
        b = UbuntuTag("Ubuntu-5.15.0-57.63")

        # Assert
        with self.assertRaises(ValueError):
            _ = a < b

    def test_non_comparable_package_direct(self):
        """Ensure tags from different packages cannot be compared"""
        # Setup
        a = UbuntuTag("Ubuntu-lowlatency-5.15.0-21.21")
        b = UbuntuTag("Ubuntu-5.15.0-57.63")

        # Assert
        self.assertFalse(a.can_compare(b))

    def test_non_comparable_kernel_direct(self):
        """Ensure tags from different kernel versions cannot be compared"""
        # Setup
        a = UbuntuTag("Ubuntu-lowlatency-4.4.0-21.21")
        b = UbuntuTag("Ubuntu-lowlatency-5.15.0-57.63")

        # Assert
        self.assertFalse(a.can_compare(b))

    def test_comparable_package_direct(self):
        """Ensure tags from different packages cannot be compared"""
        # Setup
        a = UbuntuTag("Ubuntu-5.15.0-57.63")
        b = UbuntuTag("Ubuntu-5.15.0-57.63+3")

        # Assert
        self.assertTrue(a.can_compare(b))

    def test_non_comparable_package_kernel(self):
        """Ensure tags from same package but different kernels cannot be compared"""
        # Setup
        a = UbuntuTag("Ubuntu-lowlatency-5.15-5.15.0-21.21")
        b = UbuntuTag("Ubuntu-lowlatency-5.11-5.11.0-57.63")

        # Assert
        with self.assertRaises(ValueError):
            _ = a < b
