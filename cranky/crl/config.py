#!/usr/bin/python3

import os
import sys
import yaml


class Config:
    def __init__(self, filename=None, data=None):
        self.config = None

        filename = os.getenv("CRANKY_CONFIG_FILE", filename)

        if filename is not None and data is not None:
            raise ValueError("supply only one of filename and data")

        if data is None and filename is None:
            for path in (os.path.join(os.environ['HOME'], '.cranky.yaml'),
                         os.path.join(os.environ['HOME'], '.cranky')):
                if os.path.exists(path):
                    filename = path
                    break

        if data is None and filename is not None and os.path.exists(filename):
            with open(filename) as yfd:
                data = yfd.read()

        if data is not None:
            data = yaml.safe_load(data)
        else:
            data = {}

        self.config = data

        # Warn if old/deprecated config options are found
        warn = False
        if self.lookup("package-path.base-path", None) is not None:
            warn = True
            print("Deprecated 'package-path.base-path' option found in "
                  ".cranky config file.", file=sys.stderr)
            print("You should rename it to 'base-path'.", file=sys.stderr)
        if self.lookup("test-build.logdir", None) is not None:
            warn = True
            print("Deprecated 'test-build.logdir' option found in "
                  ".cranky config file.", file=sys.stderr)
            print("You should rename it to 'test-build.log-path' and make it "
                  "relative to 'base-path'.", file=sys.stderr)
        if warn:
            print("Check the config example in kteam-tools/cranky/docs/"
                  "snip-cranky.yaml for more information.", file=sys.stderr)

    def lookup(self, element, default=None):
        config = self.config

        element = element.split('.')
        while len(element) > 0:
            if not config:
                return default
            config = config.get(element.pop(0))
        if not config:
            return default
        return config
