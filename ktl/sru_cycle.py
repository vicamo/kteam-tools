#!/usr/bin/env python
#

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from datetime       import (date, datetime)
import os
import sys
import yaml

class SruCycleEntry:
    def __init__(self, sc, name, data):
        self._sc = sc
        self._name = name
        self._data = data if data else {}

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self._name == other._name
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def name(self):
        return self._name

    @property
    def release_date(self):
        rdate = self._data.get('release-date')
        if not rdate:
            return None
        return datetime.strptime(rdate, '%Y-%m-%d').date()

    @property
    def ready_to_release(self):
        return datetime.now().date() >= self.release_date

    def __str__(self):
        return "{} ({})".format(self.name, self.release_date)


# SruCycle
#
class SruCycle:
    _url = 'https://git.launchpad.net/~canonical-kernel/+git/kteam-tools/plain/info/sru-cycle.yaml'
    _url_local = 'file://' + os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'info', 'sru-cycle.yaml'))
    #_url = 'file:///home/apw/git2/kteam-tools/info/kernel-series.yaml'
    #_url = 'file:///home/work/kteam-tools/info/kernel-series.yaml'
    _data = None

    @classmethod
    def __load_once(cls, url):
        if not cls._data:
            response = urlopen(url)
            data = response.read()
            if type(data) != str:
                data = data.decode('utf-8')
            cls._data = yaml.load(data)

    def __init__(self, url=None, data=None, use_local=False):
        if data or url:
            if url:
                response = urlopen(url)
                data = response.read()
            if type(data) != str:
                data = data.decode('utf-8')
            self._data = yaml.load(data)
        else:
            self.__load_once(self._url_local if use_local else self._url)

    @property
    def cycles(self):
        return [ SruCycleEntry(self, cycle_key, cycle)
                 for cycle_key, cycle in self._data.items() ]

    def lookup_cycle(self, cycle=None):
        if not cycle:
            raise ValueError("cycle required")
        if cycle not in self._data:
            return None
        return SruCycleEntry(self, cycle, self._data[cycle])

# vi:set ts=4 sw=4 expandtab:
