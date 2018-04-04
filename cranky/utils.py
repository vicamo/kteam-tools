#!/usr/bin/env python3
#
# Cranky toolchain helper functions and classes
#
# Juerg Haefliger <juergh@canonical.com>
#

import os
import yaml


def get_config(tool=None):
    """
    Read the cranky config options from file and (optionally) return the tool
    specific subset
    """
    config = {}
    cfile = os.path.join(os.path.expanduser('~'), '.cranky')
    if os.path.exists(cfile):
        with open(cfile, 'r') as fh:
            config = yaml.load(fh)

    if tool is not None:
        return config.get(tool, {})
    else:
        return config
