import os
import sys
import unittest
from testfixtures import TempDirectory

from ktl.kernel_series import (
    KernelSeries,
    KernelSeriesCache,
    KernelSeriesEntry,
    KernelSourceEntry,
    KernelSourceTestingFlavourEntry,
    KernelPackageEntry,
    KernelSnapEntry,
    KernelRepoEntry,
)


class TestKernelSeriesCore(unittest.TestCase):

    if sys.version_info[:3] > (3, 0):

        def assertItemsEqual(self, a, b):
            return self.assertCountEqual(a, b)


class TestKernelSeries(TestKernelSeriesCore):

    data_yaml = """
    '18.04':
        codename: bionic
        development: true
    '16.04':
        codename: xenial
    '14.04':
    """
    data_series_names = ["18.04", "16.04", "14.04"]

    def test_initialisation_data(self):
        ks = KernelSeries(data=self.data_yaml)

        count = 0
        for series in ks.series:
            self.assertTrue(isinstance(series, KernelSeriesEntry))
            count += 1
        self.assertEqual(count, 3)

    def test_initialisation_url(self):
        with TempDirectory() as d:
            d.write("kernel-series.yaml", self.data_yaml.encode("utf-8"))

            ks = KernelSeries(url="file://" + d.getpath("kernel-series.yaml"))

        count = 0
        for series in ks.series:
            self.assertTrue(isinstance(series, KernelSeriesEntry))
            count += 1
        self.assertEqual(count, 3)

    def test_kernel_series_use_local(self):
        err = None
        try:
            KernelSeries(use_local=True)
        except Exception as e:
            err = e
        self.assertIsNone(err)

    def test_lookup_series(self):
        ks = KernelSeries(data=self.data_yaml)
        series = ks.lookup_series("16.04")

        self.assertEqual(series.name, "16.04")
        self.assertEqual(series.codename, "xenial")

    def test_lookup_series_codename(self):
        ks = KernelSeries(data=self.data_yaml)
        series = ks.lookup_series(codename="xenial")

        self.assertEqual(series.name, "16.04")
        self.assertEqual(series.codename, "xenial")

    def test_lookup_series_development(self):
        ks = KernelSeries(data=self.data_yaml)
        series = ks.lookup_series(development=True)

        self.assertEqual(series.name, "18.04")
        self.assertEqual(series.codename, "bionic")

    def test_lookup_series_invalid_no_selectors(self):
        ks = KernelSeries(data=self.data_yaml)

        with self.assertRaises(ValueError):
            series = ks.lookup_series()

    def test_series(self):
        ks = KernelSeries(data=self.data_yaml)
        series_names = [s.name for s in ks.series]

        self.assertItemsEqual(series_names, self.data_series_names)


class TestKernelSeriesEntry(TestKernelSeriesCore):

    def test_equal_true(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series("18.04")
        series2 = ks.lookup_series("18.04")

        self.assertEqual(series1, series2)

    def test_equal_false(self):
        data = """
        '18.04':
        '16.04':
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series("18.04")
        series2 = ks.lookup_series("16.04")

        self.assertNotEqual(series1, series2)

    def test_equal_none(self):
        data = """
        '18.04':
        '16.04':
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series("18.04")

        self.assertNotEqual(series1, None)
        self.assertNotEqual(None, series1)

    def test_codename_present(self):
        data = """
        '18.04':
            codename: bionic
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.codename, "bionic")

    def test_codename_present_empty(self):
        data = """
        '18.04':
            codename:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertIsNone(series.codename)

    def test_codename_absent(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertIsNone(series.codename)

    def test_development_present_true(self):
        data = """
        '18.04':
            development: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.development, True)

    def test_development_present_false(self):
        data = """
        '18.04':
            development: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.development, False)

    def test_development_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.development, False)

    def test_supported_present_true(self):
        data = """
        '18.04':
            supported: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.supported, True)

    def test_supported_present_false(self):
        data = """
        '18.04':
            supported: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.supported, False)

    def test_supported_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.supported, False)

    def test_lts_present_true(self):
        data = """
        '18.04':
            lts: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.lts, True)

    def test_lts_present_false(self):
        data = """
        '18.04':
            lts: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.lts, False)

    def test_lts_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.lts, False)

    def test_esm_present_true(self):
        data = """
        '18.04':
            esm: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.esm, True)

    def test_esm_present_false(self):
        data = """
        '18.04':
            esm: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.esm, False)

    def test_esm_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.esm, False)

    def test_esm_legacy_present_true(self):
        data = """
        '18.04':
            esm-legacy: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.esm_legacy, True)

    def test_esm_legacy_present_false(self):
        data = """
        '18.04':
            esm-legacy: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.esm_legacy, False)

    def test_esm_legacy_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.esm_legacy, False)

    def test_opening_allow_present_empty(self):
        data = """
        '18.04':
            opening:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow("thing"), False)
        self.assertEqual(series.opening_allow("thing2"), False)

    def test_opening_allow_present_true(self):
        data = """
        '18.04':
            opening: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow("thing"), False)
        self.assertEqual(series.opening_allow("thing2"), False)

    def test_opening_allow_present_false(self):
        data = """
        '18.04':
            opening: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, False)
        self.assertEqual(series.opening_allow("thing"), True)
        self.assertEqual(series.opening_allow("thing2"), True)

    def test_opening_allow_present_mixed_true(self):
        data = """
        '18.04':
            opening:
                thing: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow("thing"), True)
        self.assertEqual(series.opening_allow("thing2"), False)

    def test_opening_allow_present_mixed_false(self):
        data = """
        '18.04':
            opening:
                thing: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow("thing"), False)
        self.assertEqual(series.opening_allow("thing2"), False)

    def test_opening_allow_present_mixed_mixed(self):
        data = """
        '18.04':
            opening:
                thing: false
                thing2: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow("thing"), False)
        self.assertEqual(series.opening_allow("thing2"), True)

    def test_opening_allow_present_empty(self):
        data = """
        '18.04':
            opening:
                thing:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow("thing"), False)

    def test_opening_allow_absent(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, False)
        self.assertEqual(series.opening_allow("thing"), True)

    def test_opening_ready_present_empty(self):
        data = """
        '18.04':
            opening:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), False)
        self.assertEqual(series.opening_ready("thing2"), False)
        self.assertEqual(series.opening_ready("thing", "thing2"), False)

    def test_opening_ready_present_true(self):
        data = """
        '18.04':
            opening: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), False)
        self.assertEqual(series.opening_ready("thing2"), False)
        self.assertEqual(series.opening_ready("thing", "thing2"), False)

    def test_opening_ready_present_false(self):
        data = """
        '18.04':
            opening: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, False)
        self.assertEqual(series.opening_ready("thing"), True)
        self.assertEqual(series.opening_ready("thing2"), True)
        self.assertEqual(series.opening_ready("thing", "thing2"), True)

    def test_opening_ready_present_true_absent(self):
        data = """
        '18.04':
            opening:
                thing: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), True)
        self.assertEqual(series.opening_ready("thing2"), False)
        self.assertEqual(series.opening_ready("thing", "thing2"), False)

    def test_opening_ready_present_false_absent(self):
        data = """
        '18.04':
            opening:
                thing: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), False)
        self.assertEqual(series.opening_ready("thing2"), False)
        self.assertEqual(series.opening_ready("thing", "thing2"), False)

    def test_opening_ready_present_false_true(self):
        data = """
        '18.04':
            opening:
                thing: false
                thing2: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), False)
        self.assertEqual(series.opening_ready("thing2"), True)
        self.assertEqual(series.opening_ready("thing", "thing2"), False)

    def test_opening_ready_present_true_false(self):
        data = """
        '18.04':
            opening:
                thing: true
                thing2: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), True)
        self.assertEqual(series.opening_ready("thing2"), False)
        self.assertEqual(series.opening_ready("thing", "thing2"), False)

    def test_opening_ready_present_true_true(self):
        data = """
        '18.04':
            opening:
                thing: true
                thing2: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), True)
        self.assertEqual(series.opening_ready("thing2"), True)
        self.assertEqual(series.opening_ready("thing", "thing2"), True)

    def test_opening_ready_present_empty_absent(self):
        data = """
        '18.04':
            opening:
                thing:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), False)
        self.assertEqual(series.opening_ready("thing2"), False)
        self.assertEqual(series.opening_ready("thing", "thing2"), False)

    def test_opening_ready_present_empty_true(self):
        data = """
        '18.04':
            opening:
                thing:
                thing2: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready("thing"), False)
        self.assertEqual(series.opening_ready("thing2"), True)
        self.assertEqual(series.opening_ready("thing", "thing2"), False)

    def test_opening_ready_absent(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertEqual(series.opening, False)
        self.assertEqual(series.opening_ready("thing"), True)
        self.assertEqual(series.opening_ready("thing2"), True)
        self.assertEqual(series.opening_ready("thing", "thing2"), True)

    def test_sources_no_sources(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertItemsEqual(series.sources, [])

    def test_sources_no_source_entries(self):
        data = """
        '18.04':
            sources:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        self.assertItemsEqual(series.sources, [])

    def test_sources_one(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        count = 0
        for source in series.sources:
            self.assertTrue(isinstance(source, KernelSourceEntry))
            count += 1
        self.assertEqual(count, 1)

    def test_sources_many(self):
        data = """
        '18.04':
            sources:
                linux:
                linux-signed:
                linux-meta:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        count = 0
        for source in series.sources:
            self.assertTrue(isinstance(source, KernelSourceEntry))
            count += 1
        self.assertEqual(count, 3)

    def test_lookup_source_no_sources(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source, None)

    def test_lookup_source_no_source_entries(self):
        data = """
        '18.04':
            sources:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")

        source = series.lookup_source("linux")
        self.assertEqual(source, None)

    def test_lookup_source_present(self):
        data = """
        '18.04':
            sources:
                linux:
                linux-raspi2:
                linux-snapdragon:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source1 = series.lookup_source("linux")
        source2 = series.lookup_source("linux-raspi2")
        source3 = series.lookup_source("linux-snapdragon")

        self.assertEqual(source1.name, "linux")
        self.assertEqual(source2.name, "linux-raspi2")
        self.assertEqual(source3.name, "linux-snapdragon")


class TestKernelSourceEntry(TestKernelSeriesCore):

    def test_series_linkage(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.name, "linux")
        self.assertEqual(series, source.series)

    def test_equal_true(self):
        data = """
        '18.04':
            sources:
                linux:
        '16.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source1 = series.lookup_source("linux")
        series2 = ks.lookup_series("18.04")

        source2 = series.lookup_source("linux")

        self.assertEqual(source1, source2)

    def test_equal_false(self):
        data = """
        '18.04':
            sources:
                linux:
                linux-raspi2:
        '16.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series("18.04")
        source1 = series1.lookup_source("linux")
        source2 = series1.lookup_source("linux-raspi2")
        series2 = ks.lookup_series("16.04")
        source3 = series2.lookup_source("linux")

        self.assertNotEqual(source1, source2)
        self.assertNotEqual(source1, source3)

    def test_equal_none(self):
        data = """
        '18.04':
            sources:
                linux:
                linux-raspi2:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source1 = series.lookup_source("linux")

        self.assertNotEqual(source1, None)
        self.assertNotEqual(None, source1)

    def test_name(self):
        data = """
        '18.04':
            sources:
                linux:
                linux-raspi2:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source1 = series.lookup_source("linux")
        source2 = series.lookup_source("linux-raspi2")

        self.assertEqual(source1.name, "linux")
        self.assertEqual(source2.name, "linux-raspi2")

    def test_versions_present_one(self):
        data = """
        '18.04':
            sources:
                linux:
                    versions: [ 1 ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertItemsEqual(source.versions, [1])
        self.assertEqual(source.version, 1)

    def test_versions_present_many(self):
        data = """
        '18.04':
            sources:
                linux:
                    versions: [ 1, 2, 3, 10 ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertItemsEqual(source.versions, [1, 2, 3, 10])
        self.assertEqual(source.version, 10)

    def test_versions_present_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    versions: []
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertItemsEqual(source.versions, [])
        self.assertEqual(source.version, None)

    def test_versions_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.versions, None)

    def test_development_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    development: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.development, True)

    def test_development_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    development: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.development, False)

    def test_development_absent_false(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.development, False)

    def test_development_absent_series_present_true(self):
        data = """
        '18.04':
            development: true
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.development, True)

    def test_development_absent_series_present_false(self):
        data = """
        '18.04':
            development: false
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.development, False)

    def test_supported_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    supported: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertTrue(source.supported)

    def test_supported_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    supported: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.supported)

    def test_supported_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.supported)

    def test_supported_absent_series_present_true(self):
        data = """
        '18.04':
            supported: true
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertTrue(source.supported)

    def test_supported_absent_series_present_false(self):
        data = """
        '18.04':
            supported: false
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.supported)

    def test_severe_only_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    severe-only: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertTrue(source.severe_only)

    def test_severe_only_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    severe-only: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.severe_only)

    def test_severe_only_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.severe_only)

    def test_backport_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    backport: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertTrue(source.backport)

    def test_backport_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    backport: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.backport)

    def test_backport_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.backport)

    def test_copy_forward_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    copy-forward: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertTrue(source.copy_forward)

    def test_copy_forward_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    copy-forward: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.copy_forward)

    def test_copy_forward_present_true_with_derived_from(self):
        data = """
        '18.04':
            sources:
                linux:
                linux-foo:
                    derived-from: ['18.04', 'linux']
                    copy-forward: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux-foo")

        copy = source.copy_forward
        self.assertTrue(isinstance(copy, KernelSourceEntry))
        self.assertEqual(copy.series.name, "18.04")
        self.assertEqual(copy.name, "linux")

    def test_copy_forward_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.copy_forward)

    def test_packages_no_packages(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertItemsEqual(source.packages, [])

    def test_packages_no_package_entries(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertItemsEqual(source.packages, [])

    def test_packages_one(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        count = 0
        for package in source.packages:
            self.assertTrue(isinstance(package, KernelPackageEntry))
            count += 1
        self.assertEqual(count, 1)

    def test_packages_many(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux:
                        linux-signed:
                        linux-meta:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        count = 0
        for package in source.packages:
            self.assertTrue(isinstance(package, KernelPackageEntry))
            count += 1
        self.assertEqual(count, 3)

    def test_snaps_no_snaps(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertItemsEqual(source.snaps, [])

    def test_snaps_no_snap_entries(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertItemsEqual(source.snaps, [])

    def test_snaps_one(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        count = 0
        for snap in source.snaps:
            self.assertTrue(isinstance(snap, KernelSnapEntry))
            count += 1
        self.assertEqual(count, 1)

    def test_snaps_many(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                        euclid-kernel:
                        lowlatency-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        count = 0
        for snap in source.snaps:
            self.assertTrue(isinstance(snap, KernelSnapEntry))
            count += 1
        self.assertEqual(count, 3)

    def test_derived_from_series_same(self):
        data = """
        '18.04':
            sources:
                linux:
                linux-raspi2:
                    derived-from: [ '18.04', 'linux' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source1 = series.lookup_source("linux")
        source2 = series.lookup_source("linux-raspi2")

        self.assertEqual(source2.derived_from, source1)

    def test_derived_from_series_different(self):
        data = """
        '18.04':
            sources:
                linux:
        '16.04':
            sources:
                linux-hwe:
                    derived-from: [ '18.04', 'linux' ]
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series("18.04")
        source1 = series1.lookup_source("linux")
        series2 = ks.lookup_series("16.04")
        source2 = series2.lookup_source("linux-hwe")

        self.assertEqual(source2.derived_from, source1)

    def test_derived_from_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.derived_from, None)

    def test_derived_from_multiple(self):
        data = """
        '22.04':
            sources:
                linux-realtime:
                linux-raspi:
                linux-raspi-realtime:
                    derived-from: [['22.04', 'linux-realtime'], ['22.04', 'linux-raspi']]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("22.04")
        source1 = series.lookup_source("linux-realtime")
        source2 = series.lookup_source("linux-raspi-realtime")

        self.assertEqual(source2.derived_from, source1)

    def test_derived_from_all_series_same(self):
        data = """
        '22.04':
            sources:
                linux:
                linux-raspi:
                    derived-from: ['22.04', 'linux']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("22.04")
        source1 = series.lookup_source("linux")
        source2 = series.lookup_source("linux-raspi")

        self.assertEqual(source2.derived_from_all, [source1])

    def test_derived_from_all_multiple_series_same(self):
        data = """
        '22.04':
            sources:
                linux-raspi:
                linux-realtime:
                linux-raspi-realtime:
                    derived-from: [['22.04', 'linux-raspi'], ['22.04', 'linux-realtime']]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("22.04")
        source1 = series.lookup_source("linux-raspi")
        source2 = series.lookup_source("linux-realtime")
        source3 = series.lookup_source("linux-raspi-realtime")

        self.assertEqual(source3.derived_from_all, [source1, source2])

    def test_invalid_tasks_present_single(self):
        data = """
        '18.04':
            sources:
                linux:
                    invalid-tasks: [ 'task1' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.invalid_tasks, ["task1"])

    def test_invalid_tasks_present_multiple(self):
        data = """
        '18.04':
            sources:
                linux:
                    invalid-tasks: [ 'task1', 'task2' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.invalid_tasks, ["task1", "task2"])

    def test_invalid_tasks_present_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    invalid-tasks:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.invalid_tasks, [])

    def test_supported_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.invalid_tasks, [])

    def test_testable_flavours_absent(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.testable_flavours, [])

    def test_testable_flavours_testing_present_empty(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.testable_flavours, [])

    def test_testable_flavours_testing_flavours_present_empty(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.testable_flavours, [])

    def test_testable_flavours_testing_flavours_present_empty(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                            lowlatency:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.testable_flavours, [])

    def test_testable_flavours_testing_flavours_arches_present_empty(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                arches:
                            lowlatency:
                                arches:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        flavours = []
        count = 0
        for testable in source.testable_flavours:
            self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
            flavours.append(testable.name)
            count += 1
        self.assertEqual(count, 2)
        self.assertEqual(sorted(flavours), sorted(["generic", "lowlatency"]))

    def test_testable_flavours_testing_flavours_arches_present_valid(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                arches: ['arch1', 'arch2']
                            lowlatency:
                                arches: ['arch1', 'arch3']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        flavours = []
        count = 0
        for testable in source.testable_flavours:
            self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
            flavours.append(testable.name)
            count += 1
        self.assertEqual(count, 2)
        self.assertEqual(sorted(flavours), sorted(["generic", "lowlatency"]))

    def test_testable_flavours_testing_flavours_arches_clouds_present_valid(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                arches: ['arch1', 'arch2']
                                clouds: ['cloud1', 'cloud2']
                            lowlatency:
                                arches: ['arch1', 'arch3']
                                clouds: ['cloud1', 'cloud3']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        flavours = []
        count = 0
        for testable in source.testable_flavours:
            self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
            flavours.append(testable.name)
            count += 1
        self.assertEqual(count, 2)
        self.assertEqual(sorted(flavours), sorted(["generic", "lowlatency"]))

    def test_swm_data_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertIsNone(source.swm_data)

    def test_swm_data_present_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    swm:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertIsNone(source.swm_data)

    def test_swm_data_present_something(self):
        data = """
        '18.04':
            sources:
                linux:
                    swm:
                        something: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertIsNotNone(source.swm_data)
        self.assertTrue(source.swm_data["something"])

    def test_owner_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertIsNone(source.owner)

    def test_swm_owner_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    owner:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertIsNone(source.owner)

    def test_owner_present_something(self):
        data = """
        '18.04':
            sources:
                linux:
                    owner: botty-mc-bot-face
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.owner, "botty-mc-bot-face")

    def test_swm_peer_reviewer_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertIsNone(source.peer_reviewer)

    def test_swm_peer_reviewer_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    peer-reviewer:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertIsNone(source.peer_reviewer)

    def test_peer_reviewer_present_something(self):
        data = """
        '18.04':
            sources:
                linux:
                    peer-reviewer: botty-mc-bot-face
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertEqual(source.peer_reviewer, "botty-mc-bot-face")


class TestKernelSourceTestingFlavourEntry(TestKernelSeriesCore):

    def test_name(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                arches:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.name, "generic")

    def test_arches_absent(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                clouds:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.arches, [])

    def test_arches_present_empty(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                arches:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.arches, [])

    def test_arches_present_short(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                arches: [ 'arch1' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.arches, ["arch1"])

    def test_arches_present_many(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                arches: [ 'arch1', 'arch2', 'arch3' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.arches, ["arch1", "arch2", "arch3"])

    def test_clouds_absent(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                arches:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.clouds, [])

    def test_clouds_present_empty(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                clouds:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.clouds, [])

    def test_clouds_present_short(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                clouds: [ 'cloud1' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.clouds, ["cloud1"])

    def test_cloud_present_long(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
                    testing:
                        flavours:
                            generic:
                                clouds: [ 'cloud1', 'cloud2', 'cloud3' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.clouds, ["cloud1", "cloud2", "cloud3"])


class TestKernelPackageEntry(TestKernelSeriesCore):

    def test_source_linkage(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-meta")

        self.assertEqual(source.name, "linux")
        self.assertEqual(package.name, "linux-meta")
        self.assertEqual(package.source, source)
        self.assertEqual(package.series, series)

    def test_equal_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package1 = source.lookup_package("linux-meta")
        package2 = source.lookup_package("linux-meta")

        self.assertEqual(package1, package2)

    def test_equal_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
                        linux-signed:
        '16.04':
            sources:
                linux:
                    packages:
                        linux-meta:
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series("18.04")
        source1 = series1.lookup_source("linux")
        package1 = source1.lookup_package("linux-meta")
        package2 = source1.lookup_package("linux-signed")
        series2 = ks.lookup_series("16.04")
        source2 = series2.lookup_source("linux")
        package3 = source2.lookup_package("linux-meta")

        self.assertNotEqual(package1, package2)
        self.assertNotEqual(package1, package3)

    def test_equal_none(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
                        linux-signed:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package1 = source.lookup_package("linux-meta")

        self.assertNotEqual(package1, None)
        self.assertNotEqual(None, package1)

    def test_name(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
                        linux-signed:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package1 = source.lookup_package("linux-meta")
        package2 = source.lookup_package("linux-signed")

        self.assertEqual(package1.name, "linux-meta")
        self.assertEqual(package2.name, "linux-signed")

    def test_type_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
                            type: meta
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-meta")

        self.assertEqual(package.type, "meta")

    def test_type_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-meta")

        self.assertEqual(package.type, "main")

    def test_repo_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
                            repo: [ 'url-string' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-meta")

        self.assertTrue(isinstance(package.repo, KernelRepoEntry))

    def test_repo_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-meta")

        self.assertEqual(package.repo, None)

    def test_ancillary_for_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-signed:
                            type: signed
                        linux-generate:
                            ancillary-for: signed
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertEqual(package.ancillary_for.type, "signed")

    def test_ancillary_for_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertEqual(package.ancillary_for, None)

    def test_ancillary_for_default(self):
        data = """
        defaults:
            package-relations:
                default:
                    generate:
                        ancillary-for: signed
        '18.04':
            sources:
                linux:
                    packages:
                        linux-signed:
                            type: signed
                        linux-generate:
                            type: generate
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertEqual(package.ancillary_for.type, "signed")

    def test_depends_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-signed:
                            type: signed
                        linux-generate:
                            depends: signed
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertEqual(package.depends.type, "signed")

    def test_depends_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-signed:
                            type: signed
                        linux-generate:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertEqual(package.depends, None)

    def test_depends_default(self):
        data = """
        defaults:
            package-relations:
                default:
                    generate:
                        depends: signed
        '18.04':
            sources:
                linux:
                    packages:
                        linux-signed:
                            type: signed
                        linux-generate:
                            type: generate
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertEqual(package.depends.type, "signed")

    def test_adjunct_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
                            adjunct: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertTrue(package.adjunct)

    def test_adjunct_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertFalse(package.adjunct)

    def test_adjunct_default(self):
        data = """
        defaults:
            package-relations:
                default:
                    generate:
                        adjunct: true
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
                            type: generate
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertTrue(package.adjunct)

    def test_signing_to_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
                            signing-to: signed
                        linux-signed:
                            type: signed
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertEqual(package.signing_to.type, "signed")

    def test_signing_to_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertEqual(package.signing_to, None)

    def test_signing_to_default(self):
        data = """
        defaults:
            package-relations:
                default:
                    generate:
                        signing-to: signed
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
                            type: generate
                        linux-signed:
                            type: signed
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-generate")

        self.assertTrue(package.signing_to.type == "signed")

    def test_signing_from_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
                            type: generate
                        linux-signed:
                            signing-from: generate
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-signed")

        self.assertEqual(package.signing_from.type, "generate")

    def test_signing_from_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-signed:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-signed")

        self.assertEqual(package.signing_from, None)

    def test_signing_from_default(self):
        data = """
        defaults:
            package-relations:
                default:
                    generate:
                    signed:
                        signing-from: generate
        '18.04':
            sources:
                linux:
                    packages:
                        linux-generate:
                            type: generate
                        linux-signed:
                            type: signed
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-signed")

        self.assertEqual(package.signing_from.type, "generate")


class TestKernelSnapEntry(TestKernelSeriesCore):

    def test_source_linkage(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(source.name, "linux")
        self.assertEqual(snap.name, "pc-kernel")
        self.assertEqual(snap.source, source)
        self.assertEqual(snap.series, series)

    def test_equal_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap1 = source.lookup_snap("pc-kernel")
        snap2 = source.lookup_snap("pc-kernel")

        self.assertEqual(snap1, snap2)

    def test_equal_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                        euclid-kernel:
        '16.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series("18.04")
        source1 = series1.lookup_source("linux")
        snap1 = source1.lookup_snap("pc-kernel")
        snap2 = source1.lookup_snap("euclid-kernel")
        series2 = ks.lookup_series("16.04")
        source2 = series2.lookup_source("linux")
        snap3 = source2.lookup_snap("pc-kernel")

        self.assertNotEqual(snap1, snap2)
        self.assertNotEqual(snap1, snap3)

    def test_equal_none(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                        euclid-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap1 = source.lookup_snap("pc-kernel")

        self.assertNotEqual(snap1, None)
        self.assertNotEqual(None, snap1)

    def test_name(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                        euclid-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap1 = source.lookup_snap("pc-kernel")
        snap2 = source.lookup_snap("euclid-kernel")

        self.assertEqual(snap1.name, "pc-kernel")
        self.assertEqual(snap2.name, "euclid-kernel")

    def test_repo_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            repo: [ 'url-string' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(isinstance(snap.repo, KernelRepoEntry))

    def test_repo_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(snap.repo, None)

    def test_primary_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            primary: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.primary)

    def test_primary_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            primary: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.primary)

    def test_primary_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.primary)

    def test_gated_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            gated: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.gated)

    def test_gated_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            gated: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.gated)

    def test_gated_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.gated)

    def test_gated_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            gated: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.gated)

    def test_gated_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            gated: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.gated)

    def test_gated_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.gated)

    def test_stable_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            stable: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.stable)

    def test_stable_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            stable: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.stable)

    def test_stable_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.stable)

    def test_qa_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            qa: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.qa)

    def test_qa_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            qa: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.qa)

    def test_qa_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.qa)

    def test_hw_cert_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            hw-cert: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.hw_cert)

    def test_hw_cert_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            hw-cert: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.hw_cert)

    def test_hw_cert_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.hw_cert)

    def test_arches_present_one(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            arches: [ 'amd64' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertItemsEqual(snap.arches, ["amd64"])

    def test_arches_present_many(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            arches: [ 'arm64', 'armhf' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertItemsEqual(snap.arches, ["arm64", "armhf"])

    def test_arches_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(snap.arches, None)

    def test_track_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(snap.track, None)

    def test_track_present_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            track:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(snap.track, None)

    def test_track_present_valid(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            track: "18"
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(snap.track, "18")

    def test_publish_to_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(snap.publish_to, None)

    def test_publish_to_present_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            publish-to:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertIsNone(snap.publish_to)

    def test_publish_to_present_valid(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            publish-to:
                                amd64: [ '18' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = {"amd64": ["18"]}
        self.assertEqual(match, snap.publish_to)

    def test_publish_to_present_multiple(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            publish-to:
                                armhf: [ "18-pi2", "18-pi3" ]
                                arm64: [ "18-pi3", "18-cm3" ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = {
            "armhf": ["18-pi2", "18-pi3"],
            "arm64": ["18-pi3", "18-cm3"],
        }
        self.assertEqual(match, snap.publish_to)

    def test_publish_to_compat_track_arches_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            track: 18-pi2
                            arches: [ 'armhf', 'arm64' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = {
            "armhf": ["18-pi2"],
            "arm64": ["18-pi2"],
        }
        self.assertEqual(snap.track, "18-pi2")
        self.assertEqual(match, snap.publish_to)

    def test_publish_to_compat_arches_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            arches: [ 'armhf', 'arm64' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = {
            "armhf": ["latest"],
            "arm64": ["latest"],
        }
        self.assertIsNone(snap.track)
        self.assertEqual(match, snap.publish_to)

    def test_promote_to_present_list_one(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: ['beta']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["beta"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_present_list_many(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: ['edge', 'beta', 'stable']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["edge", "beta", "stable"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_present_string_edge(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: edge
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["edge"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_present_string_beta(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: beta
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["edge", "beta"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_present_string_candidate(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: candidate
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["edge", "beta", "candidate"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_present_string_stable(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: stable
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["edge", "beta", "candidate", "stable"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_missing_stable_missing(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["edge"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_missing_stable_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            stable: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["edge", "beta", "candidate"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_missing_stable_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            stable: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        match = ["edge", "beta", "candidate", "stable"]
        self.assertEqual(match, snap.promote_to)

    def test_promote_to_present_candidate_stable_implied_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: candidate
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.stable)

    def test_promote_to_present_stable_stable_implied_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: stable
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.stable)

    def test_promote_to_present_list_edge_promote_to_risk_edge_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: ['edge']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.promote_to_risk("edge"))
        self.assertFalse(snap.promote_to_risk("beta"))
        self.assertFalse(snap.promote_to_risk("candidate"))
        self.assertFalse(snap.promote_to_risk("stable"))

    def test_promote_to_present_list_beta_promote_to_risk(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: ['beta']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.promote_to_risk("edge"))
        self.assertTrue(snap.promote_to_risk("beta"))
        self.assertFalse(snap.promote_to_risk("candidate"))
        self.assertFalse(snap.promote_to_risk("stable"))

    def test_promote_to_present_list_candidate_promote_to_risk(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: ['candidate']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.promote_to_risk("edge"))
        self.assertFalse(snap.promote_to_risk("beta"))
        self.assertTrue(snap.promote_to_risk("candidate"))
        self.assertFalse(snap.promote_to_risk("stable"))

    def test_promote_to_present_list_stable_promote_to_risk(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: ['stable']
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertFalse(snap.promote_to_risk("edge"))
        self.assertFalse(snap.promote_to_risk("beta"))
        self.assertFalse(snap.promote_to_risk("candidate"))
        self.assertTrue(snap.promote_to_risk("stable"))

    def test_promote_to_present_string_edge_promote_to_risk(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: edge
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.promote_to_risk("edge"))
        self.assertFalse(snap.promote_to_risk("beta"))
        self.assertFalse(snap.promote_to_risk("candidate"))
        self.assertFalse(snap.promote_to_risk("stable"))

    def test_promote_to_present_string_beta_promote_to_risk(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: beta
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.promote_to_risk("edge"))
        self.assertTrue(snap.promote_to_risk("beta"))
        self.assertFalse(snap.promote_to_risk("candidate"))
        self.assertFalse(snap.promote_to_risk("stable"))

    def test_promote_to_present_string_candidate_promote_to_risk(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: candidate
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.promote_to_risk("edge"))
        self.assertTrue(snap.promote_to_risk("beta"))
        self.assertTrue(snap.promote_to_risk("candidate"))
        self.assertFalse(snap.promote_to_risk("stable"))

    def test_promote_to_present_string_stable_promote_to_risk(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            promote-to: stable
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertTrue(snap.promote_to_risk("edge"))
        self.assertTrue(snap.promote_to_risk("beta"))
        self.assertTrue(snap.promote_to_risk("candidate"))
        self.assertTrue(snap.promote_to_risk("stable"))


class TestKernelRepoEntry(TestKernelSeriesCore):

    def test_owner_linkage(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
                            repo: [ 'url-string' ]
                    snaps:
                        pc-kernel:
                            repo: [ 'url-string2' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package = source.lookup_package("linux-meta")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(package.repo.owner, package)
        self.assertEqual(snap.repo.owner, snap)
        self.assertNotEqual(package.repo, snap.repo)

    def test_equal_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package1 = source.lookup_package("linux-meta")
        package2 = source.lookup_package("linux-meta")

        self.assertEqual(package1.repo, package2.repo)

    def test_equal_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
                            repo: [ 'url-string' ]
                        linux-signed:
                            repo: [ 'url-string2' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package1 = source.lookup_package("linux-meta")
        package2 = source.lookup_package("linux-signed")

        self.assertNotEqual(package1.repo, package2.repo)

    def test_equal_none(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
                            repo: [ 'url-string' ]
                        linux-signed:
                            repo: [ 'url-string2' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        package1 = source.lookup_package("linux-meta")

        self.assertNotEqual(package1.repo, None)
        self.assertNotEqual(None, package1.repo)

    def test_repo_url_only(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            repo: [ 'url-string' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(snap.repo.url, "url-string")
        self.assertEqual(snap.repo.branch, "master")

    def test_repo_url_branch(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
                            repo: [ 'url-string', 'branch-name' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        snap = source.lookup_snap("pc-kernel")

        self.assertEqual(snap.repo.url, "url-string")
        self.assertEqual(snap.repo.branch, "branch-name")


class TestKernelRoutingEntry(TestKernelSeriesCore):

    routing_data = """
        defaults:
            routing-table:
                default:
                    build:
                        - ['default-build', 'Release' ]
                        - ['default-build2', 'Release' ]
                devel:
                    build:
                        - ['default-devel-build', 'Release' ]
                esm:
                    build:
                        - ['default-esm-build', 'Release' ]
    """

    def test_source_linkage(self):
        data = (
            self.routing_data
            + """
        '18.04':
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing

        self.assertEqual(routing.source, source)

    def test_equal_true(self):
        data = (
            self.routing_data
            + """
        '18.04':
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing1 = source.routing
        routing2 = source.routing

        self.assertEqual(routing1, routing2)

    def test_equal_none(self):
        data = (
            self.routing_data
            + """
        '18.04':
            sources:
                linux:
                    routing:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing1 = source.routing

        self.assertEqual(routing1, None)

    def test_routing_default(self):
        data = (
            self.routing_data
            + """
        '18.04':
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing
        destination = routing.lookup_destination("build")

        match = [["default-build", "Release"], ["default-build2", "Release"]]
        self.assertEqual(destination, match)

    def test_routing_default_primary(self):
        data = (
            self.routing_data
            + """
        '18.04':
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing
        destination = routing.lookup_destination("build", primary=True)

        match = ["default-build", "Release"]
        self.assertEqual(destination, match)

    def test_routing_devel(self):
        data = (
            self.routing_data
            + """
        '18.04':
            development: true
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing
        destination = routing.lookup_destination("build")

        match = [["default-devel-build", "Release"]]
        self.assertEqual(destination, match)

    def test_routing_esm(self):
        data = (
            self.routing_data
            + """
        '18.04':
            esm: true
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing
        destination = routing.lookup_destination("build")

        match = [["default-esm-build", "Release"]]
        self.assertEqual(destination, match)

    def test_routing_override_devel(self):
        data = (
            self.routing_data
            + """
        '18.04':
            sources:
                linux:
                    routing: esm
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing
        destination = routing.lookup_destination("build")

        match = [["default-esm-build", "Release"]]
        self.assertEqual(destination, match)

    def test_routing_override_local(self):
        data = (
            self.routing_data
            + """
        '18.04':
            sources:
                linux:
                    routing:
                        build:
                            - [ 'local-build', 'Release' ]
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing
        destination = routing.lookup_destination("build")

        match = [["local-build", "Release"]]
        self.assertEqual(destination, match)

    def test_name_default(self):
        data = (
            self.routing_data
            + """
        '18.04':
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing

        self.assertEqual(routing.name, "default")

    def test_name_devel(self):
        data = (
            self.routing_data
            + """
        '18.04':
            development: true
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing

        self.assertEqual(routing.name, "devel")

    def test_name_esm(self):
        data = (
            self.routing_data
            + """
        '18.04':
            esm: true
            sources:
                linux:
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing

        self.assertEqual(routing.name, "esm")

    def test_name_override_local(self):
        data = (
            self.routing_data
            + """
        '18.04':
            codename: bionic
            sources:
                linux:
                    routing:
                        build:
                            - [ 'local-build', 'Release' ]
        """
        )
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")
        routing = source.routing

        self.assertEqual(routing.name, "bionic:linux")

    def test_private_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    private: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertTrue(source.private)

    def test_private_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    private: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.private)

    def test_private_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series("18.04")
        source = series.lookup_source("linux")

        self.assertFalse(source.private)


class TestKernelSeriesCache(TestKernelSeriesCore):

    def test_url_local_cycles(self):
        ksc = KernelSeriesCache(data_location="/DATA/")
        for what, cycle, paths in (
            ("tip", None, ["file:///DATA/kernel-series.yaml"]),
            (
                "cycle c1",
                "c1",
                [
                    "file:///DATA/kernel-versions/c1/info/kernel-series.yaml",
                    "file:///DATA/kernel-versions/complete/c1/info/kernel-series.yaml",
                    "file:///DATA/kernel-series.yaml@c1",
                ],
            ),
        ):
            with self.subTest(msg=what):
                urls = ksc.url_local(cycle)
                self.assertEqual(urls, paths)

    def test_form_url_cycles(self):
        ksc = KernelSeriesCache(data_location="/DATA")
        for which, cycle, paths, local in (
            (None, None, ["https://kernel.ubuntu.com/info/kernel-series.json.gz"], False),
            (None, "c1", ["https://kernel.ubuntu.com/info/kernel-series.json.gz@c1"], False),
            ("local", None, ["file:///DATA/kernel-series.yaml"], True),
            (
                "local",
                "c1",
                [
                    "file:///DATA/kernel-versions/c1/info/kernel-series.yaml",
                    "file:///DATA/kernel-versions/complete/c1/info/kernel-series.yaml",
                    "file:///DATA/kernel-series.yaml@c1",
                ],
                True,
            ),
            (
                "launchpad",
                None,
                ["https://git.launchpad.net/~canonical-kernel/+git/kteam-tools/plain/info/kernel-series.yaml"],
                False,
            ),
            (
                "launchpad",
                "c1",
                [
                    "https://git.launchpad.net/~canonical-kernel/+git/kernel-versions/plain/c1/info/kernel-series.yaml?h=main",
                    "https://git.launchpad.net/~canonical-kernel/+git/kernel-versions/plain/complete/c1/info/kernel-series.yaml?h=main",
                    "https://git.launchpad.net/~canonical-kernel/+git/kernel-versions/plain/info/kernel-series.yaml?h=c1",
                ],
                False,
            ),
        ):
            with self.subTest(msg=str(which) + " " + str(cycle)):
                with unittest.mock.patch.dict(os.environ):
                    os.environ.pop("KERNEL_SERIES_USE", None)
                    if which is not None:
                        os.environ["KERNEL_SERIES_USE"] = which
                    urls, use_local = ksc.form_url(False, cycle)
                    self.assertEqual(urls, paths)
                    self.assertEqual(use_local, local)


if __name__ == "__main__":
    unittest.main()
