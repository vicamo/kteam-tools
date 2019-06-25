#!/usr/bin/python3

import os
import yaml


class Config:
    def __init__(self, filename=None, data=None):
        self.config = None

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
            data = yaml.load(data)
        else:
            data = {}

        self.config = data

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
