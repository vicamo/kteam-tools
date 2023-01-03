#!/usr/bin/env python
#

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

import os
import yaml

from .signing_config import SigningConfig


class KernelRoutingEntryDestination:

    def __init__(self, ks, route, entry, data):
        self._ks = ks
        self.route = route
        self.entry = entry

        self.name = "{}#{}".format(route.name, entry) if entry > 1 else route.name

        self.raw_reference = data[0]
        self.pocket = data[1]
        self._reference = None

        self.suite = self.route.routing.source.series.codename
        if self.pocket != "Release":
            self.suite += "-" + self.pocket.lower()

    @property
    def reference(self):
        if self._reference is None:
            # Convert signing: namespace items via the signing-config streams.
            if self.raw_reference.startswith("signing:"):
                stream = self._ks.xc.lookup_stream(self.raw_reference[8:])
                self._reference = stream.archive_reference
            else:
                self._reference = self.raw_reference

        return self._reference


class KernelRoutingEntryRoute:

    def __init__(self, ks, routing, name, data):
        self._ks = ks
        self.name = name
        self.routing = routing

        self._data = data

        self._entries = None

    @property
    def entries(self):
        if self._entries is None:
            self._entries = [KernelRoutingEntryDestination(self._ks, self, count + 1, entry) for count, entry in enumerate(self._data)]
        return self._entries

    def __iter__(self):
        return iter(self.entries)

    def __getitem__(self, item):
        return self.entries[item]


class KernelRoutingEntry:
    def __init__(self, ks, source, data):
        name = "{}:{}".format(source.series.codename, source.name)
        if isinstance(data, str):
            # Map the name via the routing-map if present.
            data = source.series.routing_map.get(data, data)
            name = data

            # Look the name up in the routing table.
            table = source.series.routing_table
            if table is None:
                raise ValueError("unable to map routing alias {}, "
                                 "no series routing table".format(data))
            if data not in table:
                raise ValueError("unable to map routing alias {}, "
                                 "not listed in series routing table".format(data))
            data = table[data]

        # Clear out any entries that have been overriden to None.
        for entry in dict(data):
            if data[entry] is None:
                del data[entry]

        self._ks = ks
        self._source = source
        self._name = name
        self._data = data if data else {}

        self._routes = None

    @property
    def source(self):
        return self._source

    @property
    def name(self):
        return self._name

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return list(self) == list(other)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __iter__(self):
        return iter(self._data.items())

    def __getitem__(self, which):
        return self._data[which]

    def _routes_init(self):
        if self._routes is None:
            self._routes = {dest: KernelRoutingEntryRoute(self._ks, self, dest, route) for dest, route in self._data.items()}

    @property
    def routes(self):
        self._routes_init()
        return [route for dest, route in self._routes.items()]

    def lookup_route(self, route):
        self._routes_init()
        return self._routes.get(route, [])

    def lookup_destination(self, dest, primary=False):
        routes = self.lookup_route(dest)
        simple = [[route.reference, route.pocket] for route in self.lookup_route(dest)]
        if len(simple) == 0:
            return None
        if primary is True:
            return simple[0]
        return simple

    def __str__(self):
        return str(self._data)


class KernelRepoEntry:
    def __init__(self, ks, owner, data):
        if isinstance(data, list):
            new_data = {'url': data[0]}
            if len(data) == 1:
                new_data['branch'] = 'master'
            elif len(data) == 2:
                new_data['branch'] = data[1]
            data = new_data

        self._ks = ks
        self._owner = owner
        self._data = data if data else {}

    @property
    def owner(self):
        return self._owner

    # XXX: should this object have a name ?

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.url == other.url and self.branch == other.branch
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def url(self):
        return self._data['url']

    @property
    def branch(self):
        return self._data.get('branch', None)

    def __str__(self):
        return "{} {}".format(self.url, self.branch)


class KernelSnapEntry:
    def __init__(self, ks, source, name, data):
        self._ks = ks
        self._source = source
        self._name = name
        self._data = data if data else {}

        # Convert arches/track to publish-to form.
        if 'publish-to' not in self._data:
            if 'arches' in self._data:
                publish_to = {}
                for arch in self._data['arches']:
                    publish_to[arch] = [self._data.get('track', 'latest')]
                self._data['publish-to'] = publish_to

        # Convert stable to promote-to form.
        if 'promote-to' not in self._data and 'stable' in self._data:
            if self._data['stable'] is True:
                self._data['promote-to'] = 'stable'
            else:
                self._data['promote-to'] = 'candidate'
        # Assume no promote-to data to mean just to edge.
        promote_to = self._data.get('promote-to', 'edge')
        if isinstance(promote_to, str):
            expand_promote_to = []
            for risk in ('edge', 'beta', 'candidate', 'stable'):
                expand_promote_to.append(risk)
                if risk == promote_to:
                    break
            self._data['promote-to'] = expand_promote_to
        # Ensure we have stable when promote-to is present.
        if 'promote-to' in self._data and 'stable' not in self._data:
            if 'stable' in self._data['promote-to']:
                self._data['stable'] = True
            else:
                self._data['stable'] = False

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name and self.source == other.source
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

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
    def arches(self):
        # XXX: should this be []
        return self._data.get('arches', None)

    @property
    def track(self):
        return self._data.get('track', None)

    @property
    def publish_to(self):
        return self._data.get('publish-to', None)

    @property
    def promote_to(self):
        return self._data.get('promote-to', None)

    def promote_to_risk(self, risk):
        return risk in self._data.get('promote-to', [])

    def __str__(self):
        return "{} {}".format(str(self.source), self.name)


class KernelPackageEntry:
    def __init__(self, ks, source, name, data):
        self._ks = ks
        self._source = source
        self._name = name
        self._data = data if data else {}

        package_relations = self._source.package_relations
        self._defaults = self._ks.defaults.get('package-relations', {}).get(package_relations, {}).get(self.type, {})

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name and self.source == other.source
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

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
        return self._data.get('type', None)

    def _type_to_package(self, ptype):
        if ptype is None:
            return None
        return self._source.lookup_package(type=ptype)

    @property
    def ancillary_for(self):
        return self._type_to_package(self._data.get('ancillary-for', self._defaults.get('ancillary-for')))

    @property
    def adjunct(self):
        return self._data.get('adjunct', self._defaults.get('adjunct', False))

    @property
    def signing_to(self):
        return self._type_to_package(self._data.get('signing-to', self._defaults.get('signing-to')))

    @property
    def signing_from(self):
        return self._type_to_package(self._data.get('signing-from', self._defaults.get('signing-from')))

    @property
    def depends(self):
        return self._type_to_package(self._data.get('depends', self._defaults.get('depends')))

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

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name and self.series == other.series
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

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
        if derived_from is not None:
            return derived_from.versions

        copy_forward = self.copy_forward
        if copy_forward is not None:
            return copy_forward.versions

        # XXX: should this be []
        return None

    @property
    def version(self):
        versions = self.versions
        if not versions:
            return None
        return versions[-1]

    @property
    def variants(self):
        if 'variants' in self._data:
            return self._data['variants']

        copy_forward = self.copy_forward
        if copy_forward is not None:
            return copy_forward.variants

        return None

    @property
    def development(self):
        return self._data.get('development', self.series.development)

    @property
    def supported(self):
        return self._data.get('supported', self.series.supported)

    @property
    def severe_only(self):
        return self._data.get('severe-only', False)

    @property
    def owner(self):
        return self._data.get('owner', None)

    @property
    def stakeholder(self):
        return self._data.get('stakeholder', None)

    @property
    def package_relations(self):
        return self._data.get('package-relations', 'default')

    @property
    def packages(self):
        # XXX: should this return None when empty
        result = []
        packages = self._data.get('packages')
        if packages:
            for package_key, package in packages.items():
                result.append(KernelPackageEntry(self._ks, self, package_key, package))
        return result

    def lookup_package(self, package_key=None, type=None):
        if package_key is None and type is None:
            raise ValueError("package-name/package-type required")
        packages = self._data.get('packages')
        if not packages:
            return None
        if type is not None:
            for package in self.packages:
                if package.type == type or (type == 'main' and package.type is None):
                    return package
            return None
        if package_key is None or package_key not in packages:
            return None
        return KernelPackageEntry(self._ks, self, package_key, packages[package_key])

    @property
    def snaps(self):
        # XXX: should this return None when empty
        result = []
        snaps = self._data.get('snaps')
        if snaps:
            for snap_key, snap in snaps.items():
                result.append(KernelSnapEntry(self._ks, self, snap_key, snap))
        return result

    def lookup_snap(self, snap_key):
        snaps = self._data.get('snaps')
        if not snaps or snap_key not in snaps:
            return None
        return KernelSnapEntry(self._ks, self, snap_key, snaps[snap_key])

    @property
    def derived_from(self):
        if 'derived-from' not in self._data:
            return None

        (series_key, source_key) = self._data['derived-from']

        series = self._ks.lookup_series(series_key)
        source = series.lookup_source(source_key)

        return source

    @property
    def testable_flavours(self):
        retval = []
        if (self._data.get('testing') is not None and
                self._data['testing'].get('flavours') is not None):
            # XXX: there should be a KernelSourceTesting object which carries kernel_testing
            # and has a flavours attribute to return this information.
            kernel_testing = self._data['testing'].get('kernel-testing', False)
            if not kernel_testing:
                # XXX: Fallback to swm.kernel-testing: true/false if not present.
                # this should be removed once all existing instances are converted.
                swm_config = self._data.get('swm')
                swm_config = {} if swm_config is None else swm_config
                kernel_testing = swm_config.get('kernel-testing', False)
            for flavour in self._data['testing']['flavours'].keys():
                fdata = self._data['testing']['flavours'][flavour]
                # If we have neither arches nor clouds we represent a noop
                if not fdata:
                    continue
                retval.append(KernelSourceTestingFlavourEntry(flavour, fdata, kernel_testing, source=self))
        return retval

    @property
    def invalid_tasks(self):
        retval = self._data.get('invalid-tasks', [])
        if retval is None:
            retval = []
        return retval

    @property
    def copy_forward(self):
        if 'copy-forward' not in self._data:
            return None

        # XXX: backwards compatibility.
        if self._data['copy-forward'] is False:
            return None
        if self._data['copy-forward'] is True:
            derived_from = self.derived_from
            if derived_from is None:
                return True
            return self.derived_from

        (series_key, source_key) = self._data['copy-forward']

        series = self._ks.lookup_series(series_key)
        source = series.lookup_source(source_key)

        return source

    @property
    def backport(self):
        return self._data.get('backport', False)

    @property
    def routing(self):
        default = 'default'
        if self.series.development:
            default = 'devel'
        if self.series.esm:
            default = 'esm'
        data = self._data.get('routing', default)
        if data is None:
            return data
        return KernelRoutingEntry(self._ks, self, data)

    @property
    def swm_data(self):
        return self._data.get('swm')

    @property
    def private(self):
        return self._data.get('private', False)

    def __str__(self):
        return "{} {}".format(self.series.name, self.name)

class KernelSourceTestingFlavourEntry:
    def __init__(self, name, data, kernel_testing, source=None):
        self._name = name
        self._data = data
        self._source = source

        self._arches = self._data.get('arches', None)
        self._arches = self._arches if self._arches is not None else []
        self._clouds = self._data.get('clouds', None)
        self._clouds = self._clouds if self._clouds is not None else []
        self._meta_pkg = self._data.get('meta-pkg', None)

        if self._meta_pkg is None and kernel_testing:
            self._meta_pkg = "kernel-testing--{}--full--{}".format(self._source.name, name)

    @property
    def name(self):
        return self._name

    @property
    def arches(self):
        return self._arches

    @property
    def clouds(self):
        return self._clouds

    @property
    def meta_pkg(self):
        return self._meta_pkg

class KernelSeriesEntry:
    def __init__(self, ks, name, data):
        self._ks = ks
        self._name = name
        self._data = {}
        self.defaults = self._ks.defaults.get('series', self._ks.defaults)
        if self.defaults is not None:
            self._data.update(self.defaults)
        if data is not None:
            self._data.update(data)

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.name == other.name
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def name(self):
        return self._name

    @property
    def codename(self):
        return self._data.get('codename', None)

    @property
    def opening(self):
        if 'opening' in self._data:
            if self._data['opening'] is not False:
                return True
        return False

    def opening_ready(self, *flags):
        if 'opening' not in self._data:
            return True
        allow = self._data['opening']
        if allow is None:
            return False
        if allow in (True, False):
            return not allow
        for flag in flags:
            flag_allow = allow.get(flag, False)
            if flag_allow is None or flag_allow is False:
                return False
        return True
    opening_allow = opening_ready

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

    @property
    def old_releases(self):
        return self._data.get('old-releases', False)

    def __str__(self):
        return "{} ({})".format(self.name, self.codename)

    @property
    def sources(self):
        result = []
        sources = self._data.get('sources')
        if sources:
            for source_key, source in sources.items():
                result.append(KernelSourceEntry(
                    self._ks, self, source_key, source))
        return result

    @property
    def routing_table(self):
        return self._data.get('routing-table', None)

    @property
    def routing_map(self):
        return self._data.get('routing-map', {})

    def lookup_source(self, source_key):
        sources = self._data.get('sources')
        if not sources or source_key not in sources:
            return None
        return KernelSourceEntry(self._ks, self, source_key, sources[source_key])


# KernelSeries
#
class KernelSeries:
    _url = 'https://git.launchpad.net/~canonical-kernel/' \
        '+git/kteam-tools/plain/info/kernel-series.yaml'
    _url_local = 'file://' + os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                           '..', 'info', 'kernel-series.yaml'))
    #_url = 'file:///home/apw/git2/kteam-tools/info/kernel-series.yaml'
    #_url = 'file:///home/work/kteam-tools/info/kernel-series.yaml'
    _data_txt = {}

    @classmethod
    def __load_once(cls, url):
        if url not in cls._data_txt:
            response = urlopen(url)
            data = response.read()
            if not isinstance(data, str):
                data = data.decode('utf-8')
            cls._data_txt[url] = data
        return cls._data_txt[url]

    def __init__(self, url=None, data=None, use_local=os.getenv("USE_LOCAL_KERNEL_SERIES_YAML", False), xc=None):
        if data or url:
            if url:
                response = urlopen(url)
                data = response.read()
            if not isinstance(data, str):
                data = data.decode('utf-8')
        else:
            data = self.__load_once(self._url_local if use_local else self._url)
        self._data = yaml.safe_load(data)

        self._xc = None
        self._xc_local = use_local

        self._development_series = None
        self._codename_to_series = {}
        for series_key, series in self._data.items():
            if not series:
                continue
            if series.get('development', False):
                self._development_series = series_key
            if 'codename' in series:
                self._codename_to_series[series['codename']] = series_key

        # Pull out the defaults.
        self.defaults = {}
        if 'defaults' in self._data:
            self.defaults = self._data['defaults']
            del self._data['defaults']
            # Strip the assets as they are only used for YAML instantiation.
            if 'assets' in self.defaults:
                del self.defaults['assets']

    @property
    def xc(self):
        if self._xc is None:
            self._xc = SigningConfig(use_local=self._xc_local)
        return self._xc

    @staticmethod
    def key_series_name(series):
        return [int(x) for x in series.name.split('.')]

    @property
    def series(self):
        return [KernelSeriesEntry(self, series_key, series)
                for series_key, series in self._data.items()]

    def lookup_series(self, series=None, codename=None, development=False):
        if not series and not codename and not development:
            raise ValueError("series/codename/development required")
        if not series and codename:
            if codename not in self._codename_to_series:
                return None
            series = self._codename_to_series[codename]
        if not series and development:
            if not self._development_series:
                return None
            series = self._development_series
        if series and series not in self._data:
            return None
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
