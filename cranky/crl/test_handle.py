#!/usr/bin/python3

import os
import sys
from testfixtures               import TempDirectory
import unittest
from subprocess                 import getstatusoutput

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'libs')))
sys.path.append(os.pardir)

from handle                     import Handle, change_directory, HandleError
from ktl.kernel_series          import KernelSeries
from config                     import Config

class TestHandle(unittest.TestCase):

    data_yaml = """
    '18.04':
        codename: bionic
        sources:
            linux:
                packages:
                    linux:
                    linux-meta:
                        type: meta
            linux2:
                packages:
                    linux2-main:
                    linux2-meta:
                        type: meta
    '17.10':
        codename: artful
        sources:
            linux:
                packages:
                    linux:
                    linux-meta:
                        type: meta
    '16.04':
        codename: xenial
        sources:
            linux:
                packages:
                    linux:
                    linux-meta:
                        type: meta
    """

    path_config_yaml = """
    package-path:
        artful--linux--linux-meta:  artful/meta
        artful--linux:              'artful/{package}'
        xenial:                     '{series}-old/{package}'
        default:                    '{series}/{package}'
    """
    basepath_config_yaml = path_config_yaml + """
        base-path:                  '/src'
    """

    def assertEqualTrees(self, expected, trees_raw):
        trees = []
        for tree_entry in trees_raw:
            trees.append([tree_entry.series.codename,
                tree_entry.package.name, tree_entry.directory])

        self.assertEqual(sorted(expected), sorted(trees))


class TestHandleSeries(TestHandle):

    def test_series_source(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_set('bionic:linux')

        self.assertEqual(hdl.source.series.codename, 'bionic')
        self.assertEqual(hdl.source.name, 'linux')

    def test_series_source_main_missmatch(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_set('bionic:linux2')

        self.assertEqual(hdl.source.series.codename, 'bionic')
        self.assertEqual(hdl.source.name, 'linux2')

    def test_series_package(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        self.assertEqual(hdl.package.series.codename, 'bionic')
        self.assertEqual(hdl.package.name, 'linux-meta')

    def test_series_package_main_missmatch(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux2-main')

        self.assertEqual(hdl.package.series.codename, 'bionic')
        self.assertEqual(hdl.package.name, 'linux2-main')

    def test_trees_series_bionic(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_set('bionic:linux')

        trees_match = [
            [ 'bionic', 'linux', 'bionic/linux' ],
            [ 'bionic', 'linux-meta', 'bionic/linux-meta' ],
            ]
        self.assertEqualTrees(trees_match, hdl.trees)

    def test_trees_series_artful(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_set('artful:linux')

        trees_match = [
            [ 'artful', 'linux', 'artful/linux' ],
            [ 'artful', 'linux-meta', 'artful/meta' ],
            ]
        self.assertEqualTrees(trees_match, hdl.trees)

    def test_trees_series_bionic_basepath(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.basepath_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_set('bionic:linux')

        trees_match = [
            [ 'bionic', 'linux', '/src/bionic/linux' ],
            [ 'bionic', 'linux-meta', '/src/bionic/linux-meta' ],
            ]
        self.assertEqualTrees(trees_match, hdl.trees)


class TestHandleDirectoryEncode(TestHandle):

    def test_encode_directory_series(self):
        config_yaml = """
        package-path:
            default:    '{series}'
        """
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'bionic')

    def test_encode_directory_source(self):
        config_yaml = """
        package-path:
            default:    '{source}'
        """
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'linux')

    def test_encode_directory_package(self):
        config_yaml = """
        package-path:
            default:    '{package}'
        """
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'linux-meta')

    def test_encode_directory_type_main(self):
        config_yaml = """
        package-path:
            default:    '{type}'
        """
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'main')

    def test_encode_directory_type_meta(self):
        config_yaml = """
        package-path:
            default:    '{type}'
        """
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'meta')

    def test_encode_directory_typesuffix_main(self):
        config_yaml = """
        package-path:
            default:    '{type_suffix}'
        """
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, '')

    def test_encode_directory_typesuffix_meta(self):
        config_yaml = """
        package-path:
            default:    '{type_suffix}'
        """
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, '-meta')

    def test_encode_directory_bionic_linux(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'bionic/linux')
        self.assertEqual(hdl.directory, 'bionic/linux')

    def test_encode_directory_bionic_linux_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'bionic/linux-meta')
        self.assertEqual(hdl.directory, 'bionic/linux-meta')

    def test_encode_directory_artful_linux(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('artful:linux')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'artful/linux')

    def test_encode_directory_artful_linux_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('artful:linux-meta')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'artful/meta')

    def test_encode_directory_xenial_linux(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'xenial-old/linux')

    def test_encode_directory_xenial_linux_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)
        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta')

        directory = hdl.encode_directory(hdl.package)

        self.assertEqual(directory, 'xenial-old/linux-meta')


class TestHandleDirectory(TestHandle):

    def setUpRunCmd(self, path, cmd):
        with change_directory(path):
            (status, output) = getstatusoutput(cmd)
            if status != 0:
                print("CMD FAILED:", output)
            self.assertEqual(status, 0)

    def setUpSourceMain(self, d, name, branch, series, package):
        git_path = d.path + '/' + name

        d.makedir(name)
        self.setUpRunCmd(git_path, 'git init')

        debian = 'debian.' + branch

        data_env = "DEBIAN={}\n".format(debian)
        d.makedir(name + '/debian')
        d.write(name + '/debian/debian.env', data_env.encode('utf-8'))
        self.setUpRunCmd(git_path, 'git add debian/debian.env')

        data_changelog = "{} ({}) {}; urgency=medium\n  * foo\n -- ME\n".format(package, '4.15.0-1.2', series)
        d.makedir(name + '/' + debian)
        d.write(name + '/' + debian + '/changelog', data_changelog.encode('utf-8'))
        self.setUpRunCmd(git_path, 'git add {}/changelog'.format(debian))

        self.setUpRunCmd(git_path, 'git commit -a -m "Initial"'.format(debian))

    def setUpSourceMeta(self, d, name, branch, series, package):
        git_path = d.path + '/' + name

        d.makedir(name)
        self.setUpRunCmd(git_path, 'git init')

        data_changelog = "{} ({}) {}; urgency=medium\n  * foo\n -- ME\n".format(package, '4.15.0-1.2', series)
        d.makedir(name + '/debian')
        d.write(name + '/debian/changelog', data_changelog.encode('utf-8'))
        self.setUpRunCmd(git_path, 'git add debian/changelog'.format(debian))

        self.setUpRunCmd(git_path, 'git commit -a -m "Initial"'.format(debian))

    def test_directory_source_noconfig(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux', 'master', 'bionic', 'linux')

            config = Config(data="")

            hdl = Handle(ks=ks, config=config).lookup_set(d.getpath('bionic/linux'))

            self.assertEqual(hdl.series.codename, 'bionic')
            self.assertEqual(hdl.source.name, 'linux')

    def test_directory_source_config_bionic_linux(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux', 'master', 'bionic', 'linux')

            config = Config(data=self.path_config_yaml)

            hdl = Handle(ks=ks, config=config).lookup_set(d.getpath('bionic/linux'))

            self.assertEqual(hdl.series.codename, 'bionic')
            self.assertEqual(hdl.source.name, 'linux')

    def test_directory_source_config_bionic_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux-meta', 'master', 'bionic', 'linux-meta')

            config = Config(data=self.path_config_yaml)

            hdl = Handle(ks=ks, config=config).lookup_set(d.getpath('bionic/linux-meta'))

            self.assertEqual(hdl.series.codename, 'bionic')
            self.assertEqual(hdl.source.name, 'linux')

    def test_directory_tree_config_bionic_linux(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux', 'master', 'bionic', 'linux')

            config = Config(data=self.path_config_yaml)

            hdl = Handle(ks=ks, config=config).lookup_tree(d.getpath('bionic/linux'))

            self.assertEqual(hdl.series.codename, 'bionic')
            self.assertEqual(hdl.package.name, 'linux')
            self.assertEqual(hdl.directory, d.getpath('bionic/linux'))

    def test_directory_tree_config_bionic_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux-meta', 'master', 'bionic', 'linux-meta')

            config = Config(data=self.path_config_yaml)

            hdl = Handle(ks=ks, config=config).lookup_tree(d.getpath('bionic/linux-meta'))

            self.assertEqual(hdl.series.codename, 'bionic')
            self.assertEqual(hdl.package.name, 'linux-meta')
            self.assertEqual(hdl.directory, d.getpath('bionic/linux-meta'))

    def test_trees_directory_source_config_bionic_linux(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux', 'master', 'bionic', 'linux')

            config = Config(data=self.path_config_yaml)

            hdl = Handle(ks=ks, config=config).lookup_set(d.getpath('bionic/linux'))

            trees_match = [
                [ 'bionic', 'linux', d.getpath('bionic/linux') ],
                [ 'bionic', 'linux-meta', d.getpath('bionic/linux-meta') ],
                ]
            self.assertEqualTrees(trees_match, hdl.trees)

    def test_trees_directory_source_config_bionic_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux-meta', 'master', 'bionic', 'linux-meta')

            config = Config(data=self.path_config_yaml)

            hdl = Handle(ks=ks, config=config).lookup_set(d.getpath('bionic/linux-meta'))

            trees_match = [
                [ 'bionic', 'linux', d.getpath('bionic/linux') ],
                [ 'bionic', 'linux-meta', d.getpath('bionic/linux-meta') ],
                ]
            self.assertEqualTrees(trees_match, hdl.trees)

    def test_trees_directory_source_config_bionic_linux_metapresent(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux', 'master', 'bionic', 'linux')
            self.setUpSourceMain(d, 'bionic/linux-meta', 'master', 'bionic', 'linux-meta')

            config = Config(data=self.path_config_yaml)

            hdl = Handle(ks=ks, config=config).lookup_set(d.getpath('bionic/linux'))

            trees_match = [
                [ 'bionic', 'linux', d.getpath('bionic/linux') ],
                [ 'bionic', 'linux-meta', d.getpath('bionic/linux-meta') ],
                ]
            self.assertEqualTrees(trees_match, hdl.trees)

    def test_trees_directory_source_config_bionic_linux_metabroken(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux', 'master', 'bionic', 'linux')
            self.setUpSourceMain(d, 'bionic/linux-meta', 'master', 'bionic', 'linux-meta-hwe')

            config = Config(data=self.path_config_yaml)

            with self.assertRaises(HandleError):
                hdl = Handle(ks=ks, config=config).lookup_set(d.getpath('bionic/linux'))

    def test_trees_directory_source_config_bionic_linux_dot(self):
        ks = KernelSeries(data=self.data_yaml)
        with TempDirectory() as d:
            self.setUpSourceMain(d, 'bionic/linux', 'master', 'bionic', 'linux')

            config = Config(data=self.path_config_yaml)

            with change_directory(d.getpath('bionic/linux')):
                hdl = Handle(ks=ks, config=config).lookup_set('.')

            trees_match = [
                [ 'bionic', 'linux', d.getpath('bionic/linux') ],
                [ 'bionic', 'linux-meta', d.getpath('bionic/linux-meta') ],
                ]
            self.assertEqualTrees(trees_match, hdl.trees)


class TestHandleSuffixes(TestHandle):

    def test_minimal_suffixes_bionic_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux')

        (remove, add) = hdl.set_minimal_suffixes(hdl.package.source)

        remove_match = [ '-meta', '', ]
        add_match = { 'main': '', 'meta': '-meta', }

        self.assertEqual(remove, remove_match)
        self.assertEqual(add, add_match)

    def test_minimal_suffixes_artful(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('artful:linux')

        (remove, add) = hdl.set_minimal_suffixes(hdl.package.source)

        remove_match = [ 'linux', 'meta', ]
        add_match = { 'main': 'linux', 'meta': 'meta', }

        self.assertEqual(remove, remove_match)
        self.assertEqual(add, add_match)

    def test_minimal_suffixes_xenial(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux')

        (remove, add) = hdl.set_minimal_suffixes(hdl.package.source)

        remove_match = [ '-meta', '', ]
        add_match = { 'main': '', 'meta': '-meta', }

        self.assertEqual(remove, remove_match)
        self.assertEqual(add, add_match)


class TestHandleTreeRemote(TestHandle):
    data_yaml = """
    '18.04':
        codename: bionic
        sources:
            linux:
                packages:
                    linux:
                        repo: [ 'A' ]
                    linux-meta:
                        type: meta
            linux-raspi2:
                packages:
                    linux-raspi2:
                        repo: [ 'A', 'raspi2' ]
                    linux-meta-raspi2:
                        type: meta
            linux-kvm:
                packages:
                    linux-kvm:
                    linux-meta-kvm:
                        type: meta
    '16.04':
        codename: xenial
        sources:
            linux:
                packages:
                    linux:
                        repo: [ 'B' ]
                    linux-meta:
                        type: meta
            linux-kvm:
                packages:
                    linux-kvm:
                    linux-meta-kvm:
                        type: meta
    """

    path_config_one_yaml = """
    package-path:
        default:                    ubuntu
    """
    def test_remote_one_xenial_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_one_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux')

        self.assertEqual('xenial', hdl.remote)

    def test_remote_one_xenial_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_one_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta')

        self.assertEqual('xenial-meta', hdl.remote)

    def test_remote_one_xenial_kvm_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_one_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-kvm')

        self.assertEqual('xenial-kvm', hdl.remote)

    def test_remote_one_xenial_kvm_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_one_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta-kvm')

        self.assertEqual('xenial-kvm-meta', hdl.remote)

    def test_remote_one_bionic_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_one_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux')

        self.assertEqual('bionic', hdl.remote)

    def test_remote_one_bionic_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_one_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        self.assertEqual('bionic-meta', hdl.remote)

    def test_remote_one_bionic_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_one_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-raspi2')

        self.assertEqual('bionic', hdl.remote)

    path_config_crossseries_yaml = """
    package-path:
        default:                    '{package}'
    """
    def test_remote_crossseries_xenial_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crossseries_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux')

        self.assertEqual('xenial', hdl.remote)

    def test_remote_crossseries_xenial_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crossseries_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta')

        self.assertEqual('xenial', hdl.remote)

    def test_remote_crossseries_xenial_kvm_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crossseries_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-kvm')

        self.assertEqual('xenial-kvm', hdl.remote)

    def test_remote_crossseries_xenial_kvm_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crossseries_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta-kvm')

        self.assertEqual('xenial-kvm', hdl.remote)

    def test_remote_crossseries_bionic_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crossseries_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux')

        self.assertEqual('bionic', hdl.remote)

    def test_remote_crossseries_bionic_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crossseries_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        self.assertEqual('bionic', hdl.remote)

    def test_remote_crossseries_bionic_raspi2(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crossseries_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-raspi2')

        self.assertEqual('origin', hdl.remote)

    path_config_crosspackage_yaml = """
    package-path:
        default:                    '{series}'
    """
    def test_remote_crosspackage_xenial_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crosspackage_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux')

        self.assertEqual('origin', hdl.remote)

    def test_remote_crosspackage_xenial_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crosspackage_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta')

        self.assertEqual('meta', hdl.remote)

    def test_remote_crosspackage_xenial_kvm_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crosspackage_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-kvm')

        self.assertEqual('kvm', hdl.remote)

    def test_remote_crosspackage_xenial_kvm_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crosspackage_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta-kvm')

        self.assertEqual('kvm-meta', hdl.remote)

    def test_remote_crosspackage_bionic_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crosspackage_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux')

        self.assertEqual('origin', hdl.remote)

    def test_remote_crosspackage_bionic_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crosspackage_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        self.assertEqual('meta', hdl.remote)

    def test_remote_crosspackage_bionic_raspi2(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_crosspackage_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-raspi2')

        self.assertEqual('origin', hdl.remote)

    path_config_separate_yaml = """
    package-path:
        default:                    '{series}/{source}{type_suffix}'
    """
    def test_remote_separate_xenial_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_separate_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux')

        self.assertEqual('origin', hdl.remote)

    def test_remote_separate_xenial_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_separate_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta')

        self.assertEqual('origin', hdl.remote)

    def test_remote_separate_xenial_kvm_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_separate_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-kvm')

        self.assertEqual('origin', hdl.remote)

    def test_remote_separate_xenial_kvm_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_separate_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('xenial:linux-meta-kvm')

        self.assertEqual('origin', hdl.remote)

    def test_remote_separate_bionic_main(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_separate_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux')

        self.assertEqual('origin', hdl.remote)

    def test_remote_separate_bionic_meta(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_separate_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-meta')

        self.assertEqual('origin', hdl.remote)

    def test_remote_separate_bionic_raspi2(self):
        ks = KernelSeries(data=self.data_yaml)
        config = Config(data=self.path_config_separate_yaml)

        hdl = Handle(ks=ks, config=config).lookup_tree('bionic:linux-raspi2')

        self.assertEqual('origin', hdl.remote)


if __name__ == '__main__':
    unittest.main()
