#!/usr/bin/env python3
#

try:
    from urllib.request import urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import urlopen
    from urllib2 import HTTPError, URLError

from datetime       import datetime
from warnings       import warn
import os
import yaml


KERNEL_VERSIONS_DIR = os.path.realpath(
                        os.path.join(os.path.dirname(__file__), '..', '..',
                                     'kernel-versions', 'info'))

SRU_CYCLE_HEADER = '''# kernel SRU Cycle information file (YAML format)
#
# For all live SRU cycles this file contains a record.  That dictionary record
# defines attributed of the SRU cycle such as its current release-data.
#
# File format:
# The file en-toto is an unnamed dictionary containing a named series of Cycle
# records (see below).  The name for a record is the official cycle name without
# its respin number, for example 2018.05.21.
#
# Cycle record fields:
#  * name (string)
#       the name of this SRU Cycle
#  * complete (bool)
#       the cycle was completed and is archived
#  * release-date (string)
#       the release date of this SRU cycle; YYYY-MM-DD format
#  * hold (bool)
#       the cycle is on hold; infer kernel-block on all active packages
#  * current (bool)
#       indicates which sru cycle is the current cycle. the current field only
#       needs to exist on the current cycle entry
#  * cutoff-date (string)
#       the date patches are no longer applied to the git repos for the given
#       cycle
#  * stream (integer)
#       the stream which the cycle uses by default (1 if not present)
#  * notes-link (string)
#       a notes link; initially a jira card identifier KERN-1234
'''

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
            self._start_date_explicit = True
        else:
            sdate = cycle
            if not sdate[0].isdigit():
                sdate = sdate[1:]
            sdate = datetime.strptime(sdate, '%Y.%m.%d').date()
            self._start_date_explicit = False
        self._start_date = sdate

        rdate = data.get('release-date')
        if rdate is not None:
            rdate = datetime.strptime(rdate, '%Y-%m-%d').date()
        self._release_date = rdate

        self._hold = data.get('hold', False)
        self._complete = data.get('complete', False)
        self._cutoff_date = data.get('cutoff-date', None)
        self._stream = data.get('stream')
        self._notes_link = data.get('notes-link')

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
    def cutoff_date(self):
        return self._cutoff_date

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
    def complete(self):
        return self._complete

    @property
    def known(self):
        return self._known

    @property
    def stream(self):
        return self._stream

    @property
    def ready_to_release(self):
        if self.hold:
            return False
        if self.release_date is None:
            return False
        return datetime.now().date() >= self.release_date

    @property
    def notes_link(self):
        return self._notes_link

    def __str__(self):
        s = "'{}':\n".format(self.name)
        if self._hold:
            s += "    hold: {}\n".format(str(self._hold).lower())
        if self._cutoff_date:
            s += "    cutoff-date: '{}'\n".format(self._cutoff_date)
        if self._start_date_explicit:
            s += "    start-date: '{}'\n".format(self._start_date)
        if self._release_date:
            s += "    release-date: '{}'\n".format(self._release_date)
        if self._notes_link:
            s += "    notes-link: {}\n".format(self._notes_link)
        if self._stream:
            s += "    stream: {}\n".format(self._stream)
        if self._complete:
            s += "    complete: {}\n".format(str(self._complete).lower())
        return s


'''
 Should be SruCycles
'''
class SruCycle:
    '''
    Cycle Info accessor class (SRU and security cycles)

    Environment variables can be used to change the data source being used:

    - USE_LOCAL_SRU_CYCLE_YAML (bool, deprecated)
      When set to 1 use the yaml file in the default local path
    - SRU_CYCLE_USE=<key> with key being:
        default|remote[:<url>] Read-only access via remote URL
        local[:<path>]: RW access via local file (default location if path is not given)

    For the default local path the 'kernel-versions' repository must be checked out with that
    name in the same top level directory of kteam-tools.
    '''
    _cfg  = None
    _data = None

    @classmethod
    def key_name(cls, name):
        '''
        Returns a sorting key for a given cycle name. The goal is to sort by date and
        for the same date have the SRU cycle name first, then the security cycle and
        finally the devel cycle last.
        '''
        if name[:1].isalpha():
            key = name[1:]
            if name[:1] == "d":
                key += "-3"
            else:
                key += "-2"
        else:
            key = name + "-1"
        return key

    @classmethod
    def __load_once(cls, url):
        if not cls._data:
            response = urlopen(url)
            data = response.read()
            if not isinstance(data, str):
                data = data.decode('utf-8')
            cls._data = yaml.safe_load(data)

    def __init__(self, data_source=None):
        '''
        data_source (string): Optionally allows to override the source of data. Possible values:
            default|remote[:<URL>]
                Allows read-only access to the default remote URL.
            local[:<path>]
                Allows read-write access to a local file representation
            direct:<string>
                Allows to pass in yaml data directly. Since this is meant for testing
                this is not available as a environment key.

        '''
        # This used to be a Launchpad git raw URL but that was unreliable. The web URL is
        # updated every 2min and has a higher reliability.
        _url = 'https://kernel.ubuntu.com/info/sru-cycle.yaml'

        # The data source can be set from the environment but only if not directly done from
        # the command line.
        if data_source is None:
            data_source = os.getnenv('SRU_CYCLE_USE', None)

            if data_source and data_source.startswith('direct:'):
                raise ValueError('The direct: method is not allowed via environment!')

            # Deprecated mathod of overriding the data location
            if data_source is None and os.getenv("USE_LOCAL_SRU_CYCLE_YAML", False):
                warn('Use of USE_LOCAL_SRU_CYCLE_YAML is deprecated, use SRU_CYCLE_USE=local instead.')
                data_source='local'

        _data = None
        if data_source is not None:
            if data_source == 'default' or data_source == 'remote':
                pass
            elif data_source.startswith('remote:'):
                _url = data_source.split(':', 1)[1]
            elif data_source == 'local':
                _url = 'file://' + os.path.join(KERNEL_VERSIONS_DIR, 'sru-cycle.yaml')
            elif data_source.startswith('local:'):
                _url = 'file://' + data_source.split(':', 1)[1]
            elif data_source.startswith('direct:'):
                _data = data_source.split(':', 1)[1]
                if not isinstance(_data, str):
                    _data = _data.decode('utf-8')
                self._url = 'direct:'
            else:
                raise ValueError('{} is not a valid data source!'.format(data_source))

        if not self._data:
            self._url = _url
            if not _data:
                response = urlopen(_url)
                _data = response.read()
            if not isinstance(_data, str):
                _data = _data.decode('utf-8')
            self._data = yaml.safe_load(_data)

    @property
    def data_source(self):
        '''
        Returns the URL of the data source which was used to create the instance
        '''
        return self._url

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

    def __str__(self):
        '''
        Returns the YAML representation of sru-cycle.yaml as a string (including
        the informational header. This can be used to write a new file after any
        changes.
        '''
        s = SRU_CYCLE_HEADER
        for key in sorted(self._data.keys(), key=self.key_name, reverse=True):
            s += "\n" + str(SruCycleSpinEntry(key, data=self._data[key], sc=self))
        return s

# vi:set ts=4 sw=4 expandtab:
