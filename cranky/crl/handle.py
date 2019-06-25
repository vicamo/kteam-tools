#!/usr/bin/python3

import contextlib
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'libs')))

from ktl.kernel_series import KernelSeries
from ktl.debian import Debian, DebianError
from ktl.git import GitError

from crl.config import Config


class HandleError(ValueError):
    pass


@contextlib.contextmanager
def change_directory(new_dir):
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)


class HandleCore:
    def __init__(self, series=None, package=None, source=None, config=None, ks=None):
        self.series = series
        self.package = package
        self.source = source
        self.config = Config() if config is None else config
        self.ks = KernelSeries() if ks is None else ks
        self.name = "" if series is None or package is None else "{}:{}".format(series.codename, package.name)

    def encode_directory(self, package):
        base_path = self.config.lookup('package-path.base-path', '')
        which = package.type if package.type else 'main'
        which_suffix = '-' + package.type if package.type else ''

        for key in ("{series}--{source}--{package}",
                    "{series}--{source}",
                    "{series}",
                    "{type}",
                    "default"):
            key = key.format(series=package.series.codename,
                             source=package.source.name,
                             package=package.name,
                             type=which)

            package_path = self.config.lookup('package-path.' + key)
            if package_path:
                break
        if package_path is None:
            package_path = '{series}/{package}'

        package_path = package_path.format(series=package.series.codename,
                                           source=package.source.name,
                                           package=package.name,
                                           type=which,
                                           type_suffix=which_suffix)

        return os.path.expanduser(os.path.join(base_path, package_path))

    def set_minimal_suffixes(self, source):
        # Built a set of directory names for all of the packages in the source.
        paths = {}
        for package_entry in source.packages:
            path = self.encode_directory(package_entry)
            paths[package_entry.type if package_entry.type else 'main'] = path

        # Remove the longest common prefix.
        prefix = os.path.commonprefix(list(paths.values()))
        prefix_len = len(prefix)
        for key in paths:
            paths[key] = paths[key][prefix_len:]

        # Build a list, longest suffix first.
        longest = sorted(paths.values(), key=lambda p : -len(p))   # noqa: E203

        return (longest, paths)

    def identify_directory(self, directory):
        try:
            with change_directory(directory):
                changelog = Debian.changelog()
        except (DebianError, GitError) as e:
            raise HandleError("{}: bad directory handle -- {}".format(directory, e))

        if len(changelog) > 0 and changelog[0]['series'] == 'UNRELEASED':
            changelog.pop(0)

        if len(changelog) == 0:
            raise HandleError("{}: Unable to identify directory handle".format(directory))

        return (changelog[0]['series'], changelog[0]['package'])


class HandleTree(HandleCore):
    def __init__(self, series, package, directory=None, validate=True, config=None, ks=None):
        super().__init__(series=series, package=package, config=config, ks=ks)

        if directory is None:
            directory = self.encode_directory(package)

        directory = os.path.abspath(directory)
        if validate and os.path.exists(directory):
            (series_name, package_name) = self.identify_directory(directory)
            if (series_name != series.codename or package_name != package.name):
                raise HandleError("{}: tree inconsistent, is for {}:{}".format(
                    directory, series_name, package_name))

        self.directory = directory

    @property
    def remote(self):
        cross_series = False
        cross_source = False
        cross_type = False
        primary_package = None
        for series in self.ks.series:
            for source in series.sources:
                for package in source.packages:
                    # We work against the remote name for the first package
                    # which references our repository.
                    if primary_package is None and self.package.repo and package.repo:
                        if self.package.repo.url == package.repo.url:
                            primary_package = package
                    if self.package == package:
                        continue
                    directory = os.path.abspath(self.encode_directory(package))
                    if self.directory == directory:
                        if self.series != series:
                            cross_series = True
                        if self.package.source != source:
                            cross_source = True
                        if self.package.type != package.type:
                            cross_type = True

        if primary_package is None:
            primary_package = self.package
        bits = []
        if cross_series:
            bits.append(primary_package.series.codename)
        if cross_source and primary_package.source.name != 'linux':
            bits.append(primary_package.source.name.replace('linux-', ''))
        if cross_type and primary_package.type:
            bits.append(primary_package.type)

        remote = '-'.join(bits)
        return remote if remote != '' else 'origin'


class HandleSet(HandleCore):
    def __init__(self, handle, series, source, validate=True, trees=None, sample=None, ks=None, config=None):
        super().__init__(series=series, source=source, config=config, ks=ks)

        if trees:
            self.trees = trees

        elif sample is not None:
            self.trees = [sample]
            (remove, add) = self.set_minimal_suffixes(source)

            prefix = None
            directory = sample.directory
            for remove_entry in remove:
                if remove_entry == '':
                        prefix = directory
                        break
                elif directory.endswith(remove_entry):
                    prefix = directory[:-len(remove_entry)]
                    break

            if prefix is None:
                raise HandleError("{}: directory handle does not match set forms".format(handle))

            for package_entry in source.packages:
                if package_entry == sample.package:
                    continue
                directory = prefix + add[package_entry.type if package_entry.type else 'main']
                self.trees.append(HandleTree(series, package_entry, directory,
                                             validate=validate, ks=self.ks, config=self.config))

        else:
            self.trees = []
            for package_entry in source.packages:
                self.trees.append(HandleTree(series, package_entry,
                                             validate=validate, ks=self.ks, config=self.config))


class Handle(HandleCore):
    def __init__(self, config=None, ks=None):
        super().__init__(config=config, ks=ks)

    def lookup_package(self, package, validate=True):
        return HandleTree(package.series, package, validate=validate, ks=self.ks, config=self.config)

    def lookup_tree(self, handle, validate=True):
        series = None
        package = None
        directory = None

        # A directory passed as a handle.
        if os.path.exists(handle):
            (series_name, package_name) = self.identify_directory(handle)
            directory = handle

        else:
            bits = handle.split(':')
            if len(bits) != 2:
                raise HandleError("{}: handle format unknown".format(handle))

            (series_name, package_name) = bits

        series = self.ks.lookup_series(codename=series_name)
        if series is None:
            series = self.ks.lookup_series(series=series_name)
        if series is None:
            raise HandleError("{}: handle directory contains unknown series {}".format(handle, series_name))

        for source_entry in series.sources:
            for package_entry in source_entry.packages:
                if package_entry.name == package_name:
                    package = package_entry
                    break
            if package:
                break

        if package is None:
            raise HandleError("{}: handle directory contains unknown package {}".format(handle, package_name))

        return HandleTree(series, package, directory, validate=validate, ks=self.ks, config=self.config)

    def lookup_set(self, handle, validate=True):
        series = None
        source = None

        # A directory passed as a handle.
        if os.path.exists(handle):
            tree = self.lookup_tree(handle, validate=validate)
            return HandleSet(handle, tree.series, tree.package.source, validate=validate, sample=tree, ks=self.ks, config=self.config)

        # Validate this as a series/package handle.
        bits = handle.split(':')
        if len(bits) != 2:
            raise HandleError("{}: handle format unknown".format(handle))

        (series_name, source_name) = bits

        series = self.ks.lookup_series(codename=series_name)
        if series is None:
            series = self.ks.lookup_series(series=series_name)
        if series is None:
            raise HandleError("{}: handle contains unknown series".format(series_name))

        source = series.lookup_source(source_name)
        if source is None:
            raise HandleError("{}: handle contains unknown source".format(source_name))

        return HandleSet(handle, series, source, validate=validate, ks=self.ks, config=self.config)
