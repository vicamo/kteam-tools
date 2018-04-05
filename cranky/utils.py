#!/usr/bin/env python3
#
# Cranky toolchain helper functions and classes
#
# Juerg Haefliger <juergh@canonical.com>
#

import os
import yaml

from copy import deepcopy


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


def get_config(tool=None):
    """
    Read the cranky config options from file and (optionally) return the tool
    specific subset
    """
    config = {}
    cfile = os.path.join(os.path.expanduser('~'), '.cranky')
    if os.path.exists(cfile):
        with open(cfile, 'r') as fh:
            config = _expanduser(yaml.load(fh))

    if tool is not None:
        return config.get(tool, {})
    else:
        return config
