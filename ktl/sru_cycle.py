#!/usr/bin/env python
#

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from datetime       import datetime
import os
import yaml


class SruCycleSpinEntry:
    def __init__(self, spin, data=False, sc=None):
        cycle = spin.split('-')[0]

        self._name = spin
        self._cycle = cycle
        self._sc = SruCycle() if sc is None else sc
        if data is False:
            data = self._sc._data.get(spin, False)
        if data is False:
            data = self._sc._data.get(cycle, False)
        self._known = data is not False
        if data is False:
            data = { 'hold': True, }
        elif data is None:
            data = {}

        sdate = data.get('start-date')
        if sdate is not None:
            sdate = datetime.strptime(sdate, '%Y-%m-%d').date()
        else:
            sdate = cycle
            if sdate.startswith('d'):
                sdate = sdate[1:]
            sdate = datetime.strptime(sdate, '%Y.%m.%d').date()
        self._start_date = sdate

        rdate = data.get('release-date')
        if rdate is not None:
            rdate = datetime.strptime(rdate, '%Y-%m-%d').date()
        self._release_date = rdate

        self._hold = data.get('hold', False)

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
    def cycle(self):
        return self._cycle

    @property
    def start_date(self):
        return self._start_date

    @property
    def release_date(self):
        return self._release_date

    @property
    def hold(self):
        return self._hold

    @property
    def known(self):
        return self._known

    @property
    def ready_to_release(self):
        if self.hold:
            return False
        if self.release_date is None:
            return False
        return datetime.now().date() >= self.release_date

    def __str__(self):
        return "{} ({})".format(self.name, self.release_date)


# SruCycle
#
class SruCycle:
    _url = 'https://git.launchpad.net/~canonical-kernel/+git/kteam-tools/plain/info/sru-cycle.yaml'
    _url_local = 'file://' + os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                           '..', 'info', 'sru-cycle.yaml'))
    #_url = 'file:///home/apw/git2/kteam-tools/info/kernel-series.yaml'
    #_url = 'file:///home/work/kteam-tools/info/kernel-series.yaml'
    _data = None

    @classmethod
    def __load_once(cls, url):
        if not cls._data:
            response = urlopen(url)
            data = response.read()
            if not isinstance(data, str):
                data = data.decode('utf-8')
            cls._data = yaml.load(data)

    def __init__(self, url=None, data=None, use_local=False):
        if data or url:
            if url:
                response = urlopen(url)
                data = response.read()
            if not isinstance(data, str):
                data = data.decode('utf-8')
            self._data = yaml.load(data)
        else:
            self.__load_once(self._url_local if use_local else self._url)

    @property
    def cycles(self):
        return [SruCycleSpinEntry(cycle_key, cycle, sc=self)
                for cycle_key, cycle in self._data.items()]

    def lookup_cycle(self, cycle=None, allow_missing=False):
        if not cycle:
            raise ValueError("cycle required")
        spin_entry = SruCycleSpinEntry(cycle, sc=self)
        if allow_missing is False and spin_entry.known is False:
            return None
        return spin_entry

    def lookup_spin(self, spin=None, allow_missing=False):
        if not spin:
            raise ValueError("spin required")
        spin_entry = SruCycleSpinEntry(spin, sc=self)
        if allow_missing is False and spin_entry.known is False:
            return None
        return spin_entry

# vi:set ts=4 sw=4 expandtab:
