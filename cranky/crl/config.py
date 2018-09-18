#!/usr/bin/python3

from copy import deepcopy
import os
import sys
import yaml

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'libs')))

from ktl.kernel_series              import KernelSeries


def _expanduser(d):
    """
    Recursively cycle through a dict and expand all strings that start
    with '~/', but only if the resulting path exists.
    """
    _d = deepcopy(d)
    for k, v in _d.items():
        if isinstance(v, dict):
            _d[k] = _expanduser(v)
        elif isinstance(v, str) and v.startswith('~/'):
            # Only expand the user if the resulting directory exists
            expanded = os.path.expanduser(v)
            if os.path.exists(expanded):
                _d[k] = expanded
    return _d


class Config:
    def __init__(self, filename=None, data=None):
        self.config = None

        if filename and data:
            raise ValueError("supply only one of filename and data")

        if not data and not filename:
            for path in (
                os.path.join(os.environ['HOME'], '.cranky.yaml'),
                os.path.join(os.environ['HOME'], '.cranky'),
                ):
                if os.path.exists(path):
                    filename = path
                    break

        if not data and filename and os.path.exists(filename):
            with open(filename) as yfd:
                data = yfd.read()

        if data:
            data = _expanduser(yaml.load(data))
        else:
            data = {}

        self.config = data

    def lookup(self, element, default=None):
        config = self.config

        if isinstance(element, str):
            element = element.split('.')
        elif isinstance(element, list):
            pass
        else:
            raise ValueError("element must be list or str")

        while len(element) > 0:
            if not config:
                return default
            config = config.get(element.pop(0))
        return config


if __name__ == "__main__":
    def abort(msg):
        print(msg, file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        abort("Usage: {} <cmd> ...".format(sys.argv[0]))

    # Load up the kernel-series information.
    ks = KernelSeries(use_local=True)

    # Load up the application config.
    config = Config()

    if sys.argv[1] == 'source-packages-path':
        if len(sys.argv) != 4:
            abort("Usage: {0} {1} <series> <source>".format(*sys.argv))

        (series_codename, source_name) = sys.argv[2:]

        series = ks.lookup_series(codename=series_codename)
        if not series:
            abort("{}: {}: series not found".format(sys.argv[0], series_codename))
        source = series.lookup_source(source_name)
        if not source:
            abort("{}: {}: source not found in {}".format(sys.argv[0], source_name, series_codename))

        for package in source.packages:
            which = package.type if package.type else 'main'
            which_suffix = '-' + package.type if package.type else ''

            package_path = config.lookup(['package-path', which])
            if not package_path:
                package_path = config.lookup(['package-path', 'default'], '{series}{type_suffix}')

            print(os.path.expanduser(package_path.format(series=series.codename, type=which, type_suffix=which_suffix, name=package.name)))
