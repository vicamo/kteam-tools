#!/usr/bin/env python3
#
# Formats kernel-series.yaml file
#

import argparse
import ruamel.yaml
import sys

class PostProcess:
    def __call__(self, s):
        result = []
        for line in s.splitlines(True):
            sline = line.strip()
            if sline[:3] == '<<:' and sline[4] == '[':
                leading_spaces = line.find('<')
                result.append(' ' * leading_spaces + '<<:' + '\n')
                elements = sline[5:-1].split(',')
                for element in elements:
                    new_line = '- ' + element.strip()
                    result.append(' ' * leading_spaces + '  ' + new_line + '\n')
            else:
                result.append(line)

        return ''.join(result)

class KernelSeriesYamlFormat:
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, offset=2)
    # to prevent line-wrap
    yaml.width = 8192

    @classmethod
    def load(cls, filename):
        with open(filename, 'r') as f:
            return cls.yaml.load(f)

    @classmethod
    def dump(cls, filename, content):
        with open(filename, 'w') as f:
            cls.yaml.dump(content, f, transform=PostProcess())

    @classmethod
    def reformat(cls, filename):
        cls.dump(filename=filename, content=cls.load(filename=filename))
