import sys
import unittest
from testfixtures       import TempDirectory

from kernel_series      import (KernelSeries,
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
    """
    data_series_names = [ '18.04', '16.04' ]

    def test_initialisation_data(self):
        ks = KernelSeries(data=self.data_yaml)

        count = 0
        for series in ks.series:
            self.assertTrue(isinstance(series, KernelSeriesEntry))
            count += 1
        self.assertEqual(count, 2)

    def test_initialisation_url(self):
        with TempDirectory() as d:
            d.write('kernel-series.yaml', self.data_yaml.encode('utf-8'))

            ks = KernelSeries(url='file://' + d.getpath('kernel-series.yaml'))

        count = 0
        for series in ks.series:
            self.assertTrue(isinstance(series, KernelSeriesEntry))
            count += 1
        self.assertEqual(count, 2)

    def test_lookup_series(self):
        ks = KernelSeries(data=self.data_yaml)
        series = ks.lookup_series('16.04')

        self.assertEqual(series.name, '16.04')
        self.assertEqual(series.codename, 'xenial')

    def test_lookup_series_codename(self):
        ks = KernelSeries(data=self.data_yaml)
        series = ks.lookup_series(codename='xenial')

        self.assertEqual(series.name, '16.04')
        self.assertEqual(series.codename, 'xenial')

    def test_lookup_series_development(self):
        ks = KernelSeries(data=self.data_yaml)
        series = ks.lookup_series(development=True)

        self.assertEqual(series.name, '18.04')
        self.assertEqual(series.codename, 'bionic')

    def test_lookup_series_invalid_no_selectors(self):
        ks = KernelSeries(data=self.data_yaml)

        with self.assertRaises(ValueError):
            series = ks.lookup_series()

    def test_series(self):
        ks = KernelSeries(data=self.data_yaml)
        series_names = [ s.name for s in ks.series ]

        self.assertItemsEqual(series_names, self.data_series_names)


class TestKernelSeriesEntry(TestKernelSeriesCore):

    def test_equal_true(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series('18.04')
        series2 = ks.lookup_series('18.04')

        self.assertEqual(series1, series2)

    def test_equal_false(self):
        data = """
        '18.04':
        '16.04':
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series('18.04')
        series2 = ks.lookup_series('16.04')

        self.assertNotEqual(series1, series2)

    def test_equal_none(self):
        data = """
        '18.04':
        '16.04':
        """
        ks = KernelSeries(data=data)
        series1 = ks.lookup_series('18.04')

        self.assertNotEqual(series1, None)
        self.assertNotEqual(None, series1)

    def test_development_present_true(self):
        data = """
        '18.04':
            development: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.development, True)

    def test_development_present_false(self):
        data = """
        '18.04':
            development: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.development, False)

    def test_development_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.development, False)

    def test_supported_present_true(self):
        data = """
        '18.04':
            supported: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.supported, True)

    def test_supported_present_false(self):
        data = """
        '18.04':
            supported: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.supported, False)

    def test_supported_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.supported, False)

    def test_lts_present_true(self):
        data = """
        '18.04':
            lts: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.lts, True)

    def test_lts_present_false(self):
        data = """
        '18.04':
            lts: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.lts, False)

    def test_lts_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.lts, False)

    def test_esm_present_true(self):
        data = """
        '18.04':
            esm: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.esm, True)

    def test_esm_present_false(self):
        data = """
        '18.04':
            esm: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.esm, False)

    def test_esm_absent_false(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.esm, False)

    def test_opening_allow_present_empty(self):
        data = """
        '18.04':
            opening:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow('thing'), False)
        self.assertEqual(series.opening_allow('thing2'), False)

    def test_opening_allow_present_true(self):
        data = """
        '18.04':
            opening: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow('thing'), False)
        self.assertEqual(series.opening_allow('thing2'), False)

    def test_opening_allow_present_false(self):
        data = """
        '18.04':
            opening: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, False)
        self.assertEqual(series.opening_allow('thing'), True)
        self.assertEqual(series.opening_allow('thing2'), True)

    def test_opening_allow_present_mixed_true(self):
        data = """
        '18.04':
            opening:
                thing: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow('thing'), True)
        self.assertEqual(series.opening_allow('thing2'), False)

    def test_opening_allow_present_mixed_false(self):
        data = """
        '18.04':
            opening:
                thing: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow('thing'), False)
        self.assertEqual(series.opening_allow('thing2'), False)

    def test_opening_allow_present_mixed_mixed(self):
        data = """
        '18.04':
            opening:
                thing: false
                thing2: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow('thing'), False)
        self.assertEqual(series.opening_allow('thing2'), True)

    def test_opening_allow_present_empty(self):
        data = """
        '18.04':
            opening:
                thing:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_allow('thing'), False)

    def test_opening_allow_absent(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, False)
        self.assertEqual(series.opening_allow('thing'), True)

    def test_opening_ready_present_empty(self):
        data = """
        '18.04':
            opening:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), False)
        self.assertEqual(series.opening_ready('thing2'), False)
        self.assertEqual(series.opening_ready('thing', 'thing2'), False)

    def test_opening_ready_present_true(self):
        data = """
        '18.04':
            opening: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), False)
        self.assertEqual(series.opening_ready('thing2'), False)
        self.assertEqual(series.opening_ready('thing', 'thing2'), False)

    def test_opening_ready_present_false(self):
        data = """
        '18.04':
            opening: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, False)
        self.assertEqual(series.opening_ready('thing'), True)
        self.assertEqual(series.opening_ready('thing2'), True)
        self.assertEqual(series.opening_ready('thing', 'thing2'), True)

    def test_opening_ready_present_true_absent(self):
        data = """
        '18.04':
            opening:
                thing: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), True)
        self.assertEqual(series.opening_ready('thing2'), False)
        self.assertEqual(series.opening_ready('thing', 'thing2'), False)

    def test_opening_ready_present_false_absent(self):
        data = """
        '18.04':
            opening:
                thing: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), False)
        self.assertEqual(series.opening_ready('thing2'), False)
        self.assertEqual(series.opening_ready('thing', 'thing2'), False)

    def test_opening_ready_present_false_true(self):
        data = """
        '18.04':
            opening:
                thing: false
                thing2: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), False)
        self.assertEqual(series.opening_ready('thing2'), True)
        self.assertEqual(series.opening_ready('thing', 'thing2'), False)

    def test_opening_ready_present_true_false(self):
        data = """
        '18.04':
            opening:
                thing: true
                thing2: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), True)
        self.assertEqual(series.opening_ready('thing2'), False)
        self.assertEqual(series.opening_ready('thing', 'thing2'), False)

    def test_opening_ready_present_true_true(self):
        data = """
        '18.04':
            opening:
                thing: true
                thing2: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), True)
        self.assertEqual(series.opening_ready('thing2'), True)
        self.assertEqual(series.opening_ready('thing', 'thing2'), True)

    def test_opening_ready_present_empty_absent(self):
        data = """
        '18.04':
            opening:
                thing:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), False)
        self.assertEqual(series.opening_ready('thing2'), False)
        self.assertEqual(series.opening_ready('thing', 'thing2'), False)

    def test_opening_ready_present_empty_true(self):
        data = """
        '18.04':
            opening:
                thing:
                thing2: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, True)
        self.assertEqual(series.opening_ready('thing'), False)
        self.assertEqual(series.opening_ready('thing2'), True)
        self.assertEqual(series.opening_ready('thing', 'thing2'), False)

    def test_opening_ready_absent(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertEqual(series.opening, False)
        self.assertEqual(series.opening_ready('thing'), True)
        self.assertEqual(series.opening_ready('thing2'), True)
        self.assertEqual(series.opening_ready('thing', 'thing2'), True)

    def test_sources_no_sources(self):
        data = """
        '18.04':
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertItemsEqual(series.sources, [])

    def test_sources_no_source_entries(self):
        data = """
        '18.04':
            sources:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        self.assertItemsEqual(series.sources, [])

    def test_sources_one(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

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
        series = ks.lookup_series('18.04')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertEqual(source, None)

    def test_lookup_source_no_source_entries(self):
        data = """
        '18.04':
            sources:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        source = series.lookup_source('linux')
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
        series = ks.lookup_series('18.04')
        source1 = series.lookup_source('linux')
        source2 = series.lookup_source('linux-raspi2')
        source3 = series.lookup_source('linux-snapdragon')

        self.assertEqual(source1.name, 'linux')
        self.assertEqual(source2.name, 'linux-raspi2')
        self.assertEqual(source3.name, 'linux-snapdragon')

class TestKernelSourceEntry(TestKernelSeriesCore):

    def test_series_linkage(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertEqual(source.name, 'linux')
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
        series = ks.lookup_series('18.04')
        source1 = series.lookup_source('linux')
        series2 = ks.lookup_series('18.04')

        source2 = series.lookup_source('linux')

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
        series1 = ks.lookup_series('18.04')
        source1 = series1.lookup_source('linux')
        source2 = series1.lookup_source('linux-raspi2')
        series2 = ks.lookup_series('16.04')
        source3 = series2.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source1 = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source1 = series.lookup_source('linux')
        source2 = series.lookup_source('linux-raspi2')

        self.assertEqual(source1.name, 'linux')
        self.assertEqual(source2.name, 'linux-raspi2')

    def test_versions_present_one(self):
        data = """
        '18.04':
            sources:
                linux:
                    versions: [ 1 ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertItemsEqual(source.versions, [ 1 ])
        self.assertEqual(source.version, 1)

    def test_versions_present_many(self):
        data = """
        '18.04':
            sources:
                linux:
                    versions: [ 1, 2, 3, 10 ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertItemsEqual(source.versions, [ 1, 2, 3, 10 ])
        self.assertEqual(source.version, 10)

    def test_versions_present_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    versions: []
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertItemsEqual(source.versions, [])
        self.assertEqual(source.version, None)

    def test_versions_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertEqual(source.versions, None)

    def test_supported_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    supported: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertTrue(source.supported)

    def test_supported_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    supported: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertFalse(source.supported)

    def test_supported_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertFalse(source.supported)

    def test_severe_only_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    severe-only: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertTrue(source.severe_only)

    def test_severe_only_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    severe-only: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertFalse(source.severe_only)

    def test_severe_only_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertFalse(source.severe_only)

    def test_copy_forward_present_true(self):
        data = """
        '18.04':
            sources:
                linux:
                    copy-forward: true
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertTrue(source.copy_forward)

    def test_copy_forward_present_false(self):
        data = """
        '18.04':
            sources:
                linux:
                    copy-forward: false
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux-foo')

        copy = source.copy_forward
        self.assertTrue(isinstance(copy, KernelSourceEntry))
        self.assertEqual(copy.series.name, '18.04')
        self.assertEqual(copy.name, 'linux')

    def test_copy_forward_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertFalse(source.copy_forward)

    def test_packages_no_packages(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertItemsEqual(source.packages, [])

    def test_packages_no_package_entries(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertItemsEqual(source.snaps, [])

    def test_snaps_no_snap_entries(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source1 = series.lookup_source('linux')
        source2 = series.lookup_source('linux-raspi2')

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
        series1 = ks.lookup_series('18.04')
        source1 = series1.lookup_source('linux')
        series2 = ks.lookup_series('16.04')
        source2 = series2.lookup_source('linux-hwe')

        self.assertEqual(source2.derived_from, source1)

    def test_derived_from_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertEqual(source.derived_from, None)

    def test_invalid_tasks_present_single(self):
        data = """
        '18.04':
            sources:
                linux:
                    invalid-tasks: [ 'task1' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertEqual(source.invalid_tasks, ['task1'])

    def test_invalid_tasks_present_multiple(self):
        data = """
        '18.04':
            sources:
                linux:
                    invalid-tasks: [ 'task1', 'task2' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertEqual(source.invalid_tasks, ['task1', 'task2'])

    def test_invalid_tasks_present_empty(self):
        data = """
        '18.04':
            sources:
                linux:
                    invalid-tasks:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertEqual(source.invalid_tasks, [])

    def test_supported_absent(self):
        data = """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        self.assertEqual(source.invalid_tasks, [])

    def test_testable_flavours_absent(self):
        data = """
        '18.04':
            codename: bionic
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        flavours = []
        count = 0
        for testable in source.testable_flavours:
            self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
            flavours.append(testable.name)
            count += 1
        self.assertEqual(count, 2)
        self.assertEqual(sorted(flavours), sorted(['generic', 'lowlatency']))

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        flavours = []
        count = 0
        for testable in source.testable_flavours:
            self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
            flavours.append(testable.name)
            count += 1
        self.assertEqual(count, 2)
        self.assertEqual(sorted(flavours), sorted(['generic', 'lowlatency']))

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')

        flavours = []
        count = 0
        for testable in source.testable_flavours:
            self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
            flavours.append(testable.name)
            count += 1
        self.assertEqual(count, 2)
        self.assertEqual(sorted(flavours), sorted(['generic', 'lowlatency']))

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.name, 'generic')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.arches, ['arch1'])

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.arches, ['arch1', 'arch2', 'arch3'])

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.clouds, ['cloud1'])

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        testable = source.testable_flavours[0]

        self.assertTrue(isinstance(testable, KernelSourceTestingFlavourEntry))
        self.assertEqual(testable.clouds, ['cloud1', 'cloud2', 'cloud3'])


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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package = source.lookup_package('linux-meta')

        self.assertEqual(source.name, 'linux')
        self.assertEqual(package.name, 'linux-meta')
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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package1 = source.lookup_package('linux-meta')
        package2 = source.lookup_package('linux-meta')

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
        series1 = ks.lookup_series('18.04')
        source1 = series1.lookup_source('linux')
        package1 = source1.lookup_package('linux-meta')
        package2 = source1.lookup_package('linux-signed')
        series2 = ks.lookup_series('16.04')
        source2 = series2.lookup_source('linux')
        package3 = source2.lookup_package('linux-meta')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package1 = source.lookup_package('linux-meta')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package1 = source.lookup_package('linux-meta')
        package2 = source.lookup_package('linux-signed')

        self.assertEqual(package1.name, 'linux-meta')
        self.assertEqual(package2.name, 'linux-signed')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package = source.lookup_package('linux-meta')

        self.assertEqual(package.type, 'meta')

    def test_type_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    packages:
                        linux-meta:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package = source.lookup_package('linux-meta')

        self.assertEqual(package.type, None)

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package = source.lookup_package('linux-meta')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package = source.lookup_package('linux-meta')

        self.assertEqual(package.repo, None)


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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

        self.assertEqual(source.name, 'linux')
        self.assertEqual(snap.name, 'pc-kernel')
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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap1 = source.lookup_snap('pc-kernel')
        snap2 = source.lookup_snap('pc-kernel')

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
        series1 = ks.lookup_series('18.04')
        source1 = series1.lookup_source('linux')
        snap1 = source1.lookup_snap('pc-kernel')
        snap2 = source1.lookup_snap('euclid-kernel')
        series2 = ks.lookup_series('16.04')
        source2 = series2.lookup_source('linux')
        snap3 = source2.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap1 = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap1 = source.lookup_snap('pc-kernel')
        snap2 = source.lookup_snap('euclid-kernel')

        self.assertEqual(snap1.name, 'pc-kernel')
        self.assertEqual(snap2.name, 'euclid-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

        self.assertItemsEqual(snap.arches, [ 'amd64' ])

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

        self.assertItemsEqual(snap.arches, [ 'arm64', 'armhf' ])

    def test_arches_absent(self):
        data = """
        '18.04':
            sources:
                linux:
                    snaps:
                        pc-kernel:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

        self.assertEqual(snap.track, '18')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package = source.lookup_package('linux-meta')
        snap = source.lookup_snap('pc-kernel')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package1 = source.lookup_package('linux-meta')
        package2 = source.lookup_package('linux-meta')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package1 = source.lookup_package('linux-meta')
        package2 = source.lookup_package('linux-signed')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package1 = source.lookup_package('linux-meta')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

        self.assertEqual(snap.repo.url, 'url-string')
        self.assertEqual(snap.repo.branch, 'master')

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
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap = source.lookup_snap('pc-kernel')

        self.assertEqual(snap.repo.url, 'url-string')
        self.assertEqual(snap.repo.branch, 'branch-name')


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
        data = self.routing_data + """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing = source.routing

        self.assertEqual(routing.source, source)

    def test_equal_true(self):
        data = self.routing_data + """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing1 = source.routing
        routing2 = source.routing

        self.assertEqual(routing1, routing2)

    def test_equal_none(self):
        data = self.routing_data + """
        '18.04':
            sources:
                linux:
                    routing:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing1 = source.routing

        self.assertEqual(routing1, None)

    def test_routing_default(self):
        data = self.routing_data + """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing = source.routing
        destination = routing.lookup_destination('build')

        match = [['default-build', 'Release'], ['default-build2', 'Release']]
        self.assertEqual(destination, match)

    def test_routing_default_primary(self):
        data = self.routing_data + """
        '18.04':
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing = source.routing
        destination = routing.lookup_destination('build', primary=True)

        match = ['default-build', 'Release']
        self.assertEqual(destination, match)

    def test_routing_devel(self):
        data = self.routing_data + """
        '18.04':
            development: true
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing = source.routing
        destination = routing.lookup_destination('build')

        match = [['default-devel-build', 'Release']]
        self.assertEqual(destination, match)

    def test_routing_esm(self):
        data = self.routing_data + """
        '18.04':
            esm: true
            sources:
                linux:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing = source.routing
        destination = routing.lookup_destination('build')

        match = [['default-esm-build', 'Release']]
        self.assertEqual(destination, match)

    def test_routing_override_devel(self):
        data = self.routing_data + """
        '18.04':
            sources:
                linux:
                    routing: esm
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing = source.routing
        destination = routing.lookup_destination('build')

        match = [['default-esm-build', 'Release']]
        self.assertEqual(destination, match)

    def test_routing_override_local(self):
        data = self.routing_data + """
        '18.04':
            sources:
                linux:
                    routing:
                        build:
                            - [ 'local-build', 'Release' ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        routing = source.routing
        destination = routing.lookup_destination('build')

        match = [['local-build', 'Release']]
        self.assertEqual(destination, match)


if __name__ == '__main__':
    unittest.main()
