#!/usr/bin/env python
#

import re
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

import yaml


def convert_v2_to_v1(data):
    data_v1 = {}
    for series_key, series in data.items():
        series_v1 = data_v1.setdefault(series_key, {})

        series_v1['series_version'] = series_key
        series_v1['name'] = series['codename']
        for key in ('development', 'supported'):
            series_v1[key] = series.get(key, False)
        for key in ('lts', 'esm'):
            if series.get(key, False):
                series_v1[key] = series[key]

        if 'sources' not in series:
            continue

        for source_key, source in series['sources'].items():
            if 'versions' in source:
                series_v1['kernels'] = source['versions']
                series_v1['kernel'] = series_v1['kernels'][-1]
                break

        series_v1['derivative-packages'] = {}
        series_v1['packages'] = []
        series_v1['derivative-packages']['linux'] = []
        for source_key, source in series['sources'].items():
            if source.get('supported', False) and not source.get('copy-forward', False):
                if 'derived-from' in source:
                    (derived_series, derived_package) = source['derived-from']
                    if derived_series == series_key:
                        derivative_packages = series_v1['derivative-packages'].setdefault(derived_package, [])
                        derivative_packages.append(source_key)
                    else:
                        backport_packages = series_v1.setdefault('backport-packages', {})
                        backport_packages[source_key] = [ derived_package, derived_series ]

                else:
                    series_v1['derivative-packages'].setdefault(source_key, [])

            for package_key, package in source['packages'].items():
                if source.get('supported', False) and not source.get('copy-forward', False):
                    series_v1['packages'].append(package_key)

                if not package:
                    continue

                dependent_packages = series_v1.setdefault('dependent-packages', {})
                dependent_packages_package = dependent_packages.setdefault(source_key, {})

                if 'type' in package:
                    dependent_packages_package[package['type']] = package_key

            if 'snaps' in source:
                for snap_key, snap in source['snaps'].items():
                    if snap and 'primary' in snap:
                        dependent_snaps = series_v1.setdefault('dependent-snaps', {})
                        dependent_snaps_source = dependent_snaps.setdefault(source_key, snap)
                        dependent_snaps_source['snap'] = snap_key
                        del dependent_snaps_source['primary']
                        del dependent_snaps_source['repo']
                    else:
                        derivative_snaps = series_v1.setdefault('derivative-snaps', {})
                        derivative_snaps.setdefault(source_key, []).append(snap_key)

    return data_v1


class KernelRepoEntry:
    def __init__(self, ks, owner, data):
        if isinstance(data, list):
            new_data = { 'url': data[0] }
            if len(data) == 2:
                new_data['branch'] = data[1]
            data = new_data

        self._ks = ks
        self._owner = owner
        self._data = data if data else {}

    @property
    def owner(self):
        return self._owner.series

    @property
    def url(self):
        return self._data['url']

    @property
    def branch(self):
        return self._data.get('branch', None)

    def __str__(self):
        return "{} {}".format(self.repo, self.branch)


class KernelSnapEntry:
    def __init__(self, ks, source, name, data):
        self._ks = ks
        self._source = source
        self._name = name
        self._data = data if data else {}

    @property
    def series(self):
        return self._source.series

    @property
    def source(self):
        return self._source

    @property
    def name(self):
        return self._name

    @property
    def repo(self):
        data = self._data.get('repo', None)
        if not data:
            return None
        return KernelRepoEntry(self._ks, self, data)

    @property
    def primary(self):
        return self._data.get('primary', False)

    @property
    def gated(self):
        return self._data.get('gated', False)

    @property
    def stable(self):
        return self._data.get('stable', False)

    @property
    def qa(self):
        return self._data.get('qa', False)

    @property
    def hw_cert(self):
        return self._data.get('hw-cert', False)

    @property
    def repo(self):
        return self._data.get('repo', None)

    @property
    def arches(self):
        return self._data.get('arches', None)

    def __str__(self):
        return "{} {}".format(str(self.source), self.name)


class KernelPackageEntry:
    def __init__(self, ks, source, name, data):
        self._ks = ks
        self._source = source
        self._name = name
        self._data = data if data else {}

    @property
    def series(self):
        return self._source.series

    @property
    def source(self):
        return self._source

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._data.get('type', 'prime')

    @property
    def repo(self):
        data = self._data.get('repo', None)
        if not data:
            return None
        return KernelRepoEntry(self._ks, self, data)

    def __str__(self):
        return "{} {} {}".format(str(self.source), self.name, self.type)


class KernelSourceEntry:
    def __init__(self, ks, series, name, data):
        self._ks = ks
        self._series = series
        self._name = name
        self._data = data if data else {}

    @property
    def name(self):
        return self._name

    @property
    def series(self):
        return self._series

    @property
    def versions(self):
        if 'versions' in self._data:
            return self._data['versions']

        derived_from = self.derived_from
        if derived_from:
            return derived_from.versions

        return None

    @property
    def supported(self):
        return self._data.get('supported', False)

    @property
    def packages(self):
        result = []
        for package_key, package in self._data.get('packages', {}).items():
            result.append(KernelPackageEntry(self._ks, self, package_key, package))
        return result

    def lookup_package(self, package_key):
        package = self._data.get('packages', {}).get(package_key, False)
        if package == False:
            raise KeyError("package {} not found in source {}".format(package_key, self))
        return KernelPackageEntry(self._ks, self, package_key, package)

    @property
    def snaps(self):
        result = []
        for snap_key, snap in self._data.get('snaps', {}).items():
            result.append(KernelSnapEntry(self._ks, self, snap_key, snap))
        return result

    @property
    def derived_from(self):
        if 'derived-from' not in self._data:
            return None

        (series_key, source_key) = self._data['derived-from']

        series = self._ks.lookup_series(series_key)
        source = series.lookup_source(source_key)

        return source

    def __str__(self):
        return "{} {}".format(self.series.name, self.name)


class KernelSeriesEntry:
    def __init__(self, ks, name, data):
        self._ks = ks
        self._name = name
        self._data = data

    @property
    def name(self):
        return self._name

    @property
    def codename(self):
        return self._data['codename']

    @property
    def development(self):
        return self._data.get('development', False)

    @property
    def supported(self):
        return self._data.get('supported', False)

    @property
    def lts(self):
        return self._data.get('lts', False)

    @property
    def esm(self):
        return self._data.get('esm', False)

    def __str__(self):
        return "{} ({})".format(self.name, self.codename)

    @property
    def sources(self):
        result = []
        for source_key, source in self._data.get('sources', {}).items():
            result.append(KernelSourceEntry(self._ks, self, source_key, source))
        return result

    def lookup_source(self, source_key):
        source = self._data.get('sources', {}).get(source_key)
        if not source:
            raise KeyError("source {} not found in series {}".format(source_key, series))
        return KernelSourceEntry(self._ks, self, source_key, source)


# KernelSeries
#
class KernelSeries:
    #_url = 'https://git.launchpad.net/~canonical-kernel/+git/kteam-tools/plain/info/kernel-series.yaml'
    _url = 'file:///home/apw/git2/kteam-tools/info/kernel-series.yaml'

    def __init__(self):
        response = urlopen(self._url)
        content = response.read()
        if type(content) != str:
            content = content.decode('utf-8')
        self._data = yaml.load(content)

        self._development_series = None
        self._codename_to_series = {}
        for series_key, series in self._data.items():
            if series.get('development', False):
                self._development_series = series_key
            if 'codename' in series:
                self._codename_to_series[series['codename']] = series_key

    @staticmethod
    def key_series_name(series):
        return [ int(x) for x in series.name.split('.') ]

    @property
    def series(self):
        return [ KernelSeriesEntry(self, series_key, series)
                 for series_key, series in self._data.items() ]

    def lookup_series(self, series=None, codename=None, development=False):
        if not series and not codename and not development:
            raise KeyError("series/codename/development required")
        if not series and codename:
            if codename not in self._codename_to_series:
                raise KeyError("series {} not found".format(series))
            series = self._codename_to_series[codename]
        if not series and development:
            if not self._development_series:
                raise KeyError("development series not defined")
            series = self._development_series
        if series:
            if series not in self._data:
                raise KeyError("series {} not found".format(series))
        return KernelSeriesEntry(self, series, self._data[series])


if __name__ == '__main__':
    db = KernelSeries()

    series = db.lookup_series('16.04')
    if series.name != '16.04':
        print('series.name != 16.04')
    if series.codename != 'xenial':
        print('series.codename != xenial')

    series2 = db.lookup_series(codename='xenial')
    if series2.name != '16.04':
        print('series2.name != 16.04')
    if series2.codename != 'xenial':
        print('series2.codename != xenial')

    series3 = db.lookup_series(development=True)
    if series3.name != '18.04':
        print('series3.name != 18.04')
    if series3.codename != 'bionic':
        print('series3.codename != bionic')

    print(str(series), str(series2), str(series3))

    for series2 in sorted(db.series, key=db.key_series_name):
        print(series2)

    for source in series.sources:
        print(str(source), source.series.name, source.name)

        print(source.derived_from)
        print(source.versions)

        for package in source.packages:
            print("PACKAGE", str(package))

        for snap in source.snaps:
            print("SNAP", str(snap), snap.arches)


# vi:set ts=4 sw=4 expandtab:
