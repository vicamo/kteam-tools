import unittest
from testfixtures       import TempDirectory

from kernel_series      import (KernelSeries,
                                KernelSeriesEntry,
                                KernelSourceEntry,
                                KernelPackageEntry,
                                KernelSnapEntry,
                                KernelRepoEntry,
                               )

class TestKernelSeries(unittest.TestCase):

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
            d.write('kernel-series.yaml', self.data_yaml)

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

    def test_series(self):
        ks = KernelSeries(data=self.data_yaml)
        series_names = [ s.name for s in ks.series ]

        self.assertItemsEqual(series_names, self.data_series_names)


class TestKernelSeriesEntry(unittest.TestCase):

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

        with self.assertRaises(KeyError):
            source = series.lookup_source('linux')

    def test_lookup_source_no_source_entries(self):
        data = """
        '18.04':
            sources:
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')

        with self.assertRaises(KeyError):
            source = series.lookup_source('linux')

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

class TestKernelSourceEntry(unittest.TestCase):

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
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source1 = series.lookup_source('linux')
        source2 = series.lookup_source('linux')

        self.assertEqual(source1, source2)

    def test_equal_false(self):
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

        self.assertNotEqual(source1, source2)

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

    def test_versions_present(self):
        data = """
        '18.04':
            sources:
                linux:
                    versions: [ 1, 2, 3 ]
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        
        self.assertItemsEqual(source.versions, [ 1, 2, 3 ])

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


class TestKernelPackageEntry(unittest.TestCase):

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
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        package1 = source.lookup_package('linux-meta')
        package2 = source.lookup_package('linux-signed')

        self.assertNotEqual(package1, package2)

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

        self.assertEqual(package.type, 'prime')

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


class TestKernelSnapEntry(unittest.TestCase):

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
        """
        ks = KernelSeries(data=data)
        series = ks.lookup_series('18.04')
        source = series.lookup_source('linux')
        snap1 = source.lookup_snap('pc-kernel')
        snap2 = source.lookup_snap('euclid-kernel')

        self.assertNotEqual(snap1, snap2)

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


class TestKernelRepoEntry(unittest.TestCase):

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
                            repo: [ 'url-string' ]
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
        self.assertEqual(snap.repo.branch, None)

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


if __name__ == '__main__':
    unittest.main()
