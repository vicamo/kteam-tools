try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

from copy import copy
from datetime import datetime
from warnings import warn
import os
import yaml


KERNEL_VERSIONS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "kernel-versions", "info"))

SRU_CYCLE_HEADER = """# kernel SRU Cycle information file (YAML format)
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
#  * owner (string)
#       the owner of the cycle
"""


class SruCycleSpinEntry:

    def __init__(self, spin, data=False, sc=None, owner=None):
        """
        Instantiate a new SruCycleSpinEntry object.

        spin (string): Either a spin or a cycle name (with or without "-X" suffix).
            This is the dictionary key for the SruCycle class.
        data (dict): Intended to pass in the dictionary representing the elements
            of the cycle data. If nothing is supplied a rudimentary initialized
            objects gets returned (name, cycle, known:False, hold:True).
        sc (deprecated) only accepted for backwards compatibility.
        """
        cycle = spin.split("-")[0]

        self._sc = None
        self._name = spin
        self._cycle = cycle
        self._known = data is not False
        if data is False:
            data = {
                "hold": True,
            }
        elif data is None:
            data = {}

        sdate = data.get("start-date")
        if sdate is not None:
            sdate = datetime.strptime(sdate, "%Y-%m-%d").date()
            self._start_date_explicit = True
        else:
            sdate = cycle
            if not sdate[0].isdigit():
                sdate = sdate[1:]
            sdate = datetime.strptime(sdate, "%Y.%m.%d").date()
            self._start_date_explicit = False
        self._start_date = sdate

        rdate = data.get("release-date")
        if rdate is not None:
            rdate = datetime.strptime(rdate, "%Y-%m-%d").date()
        self._release_date = rdate

        self._hold = data.get("hold", False)
        self._complete = data.get("complete", False)
        self._cutoff_date = data.get("cutoff-date", None)
        self._stream = data.get("stream")
        self._notes_link = data.get("notes-link")

        self._previous_cycle = data.get("previous-cycle")
        self._previous_cycle_explicit = self._previous_cycle is not None
        self._owner = data.get("owner")
        if owner is not None:
            self._owner = owner

    def __eq__(self, other):
        """
        Returns True if both objects are SruCycleSpinEntry with the same name.
        """
        if isinstance(self, other.__class__):
            return self.name == other.name
        return False

    def __ne__(self, other):
        """
        Returns True if both sides are not considered to be the same.
        """
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

    def attach(self, table):
        self._sc = table
        return self

    @property
    def previous_cycle(self):
        if isinstance(self._previous_cycle, str):
            # Handle delayed instantiation of explicit previous-cycle markers.
            self._previous_cycle = self._sc.lookup_cycle(self._previous_cycle)

        elif not self._previous_cycle_explicit:
            # Find the previous cycle for this cycle by taking the one before
            # it in the configuration.  d* cycles do not have a previous-cycle
            # by default and must be specified explicitly.  When considering
            # previous cycles for stable cycles ignore development cycles.
            self._previous_cycle = None
            if self.cycle[0] != "d":
                pick_next = False
                for cycle in self._sc.cycles:
                    if cycle.name[0] == "d":
                        continue
                    if pick_next:
                        self._previous_cycle = cycle
                        break
                    if cycle.cycle == self.cycle:
                        pick_next = True
        return self._previous_cycle

    def __str__(self):
        """
        Returns a string which represents the data of the object in YAML form.
        """
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
        if self._previous_cycle_explicit:
            s += "    previous-cycle: {}\n".format(self.previous_cycle.name)
        if self._owner:
            s += "    owner: {}\n".format(self._owner)
        return s


"""
 Should be SruCycles
"""


class SruCycle:
    """
    Cycle Info accessor class (SRU and security cycles)

    Environment variables can be used to change the data source being used:

    - USE_LOCAL_SRU_CYCLE_YAML (bool, deprecated)
      When set to 1 use the yaml file in the default local path
    - SRU_CYCLE_USE=<key> with key being:
        default|remote[:<url>] Read-only access via remote URL
        local[:<path>]: RW access via local file (default location if path is not given)

    For the default local path the 'kernel-versions' repository must be checked out with that
    name in the same top level directory of kteam-tools.
    """

    _data = None

    @classmethod
    def key_name(cls, name):
        """
        Returns a sorting key for a given cycle name. The goal is to sort by date and
        for the same date have the SRU cycle name first, then the security cycle and
        finally the devel cycle last.
        For multiple entries of the same cycles but with different spin numbers, the
        spin number sorts those.
        """
        if "-" in name:
            cycle, spin = name.split("-", 1)
        else:
            cycle = name
            spin = "0"

        if name[:1].isalpha():
            cycle = name[1:]
            if name[:1] == "d":
                pfx = 3
            else:
                pfx = 2
        else:
            pfx = 1
        return (cycle, pfx, int(spin))

    def __cached_lookup(self, key):
        if isinstance(self._data[key], dict):
            self._data[key] = SruCycleSpinEntry(key, data=self._data[key]).attach(self)
        return self._data[key]

    def __init__(self, data=None):
        """
        data (string|dict()): Optionally allows to either pass in a URL override (string)
            or a pre-filled dictionary which represents cycle data (this is intended for
            testing).
            The URL override takes priority over the definitions in the environment.
        """
        # This used to be a Launchpad git raw URL but that was unreliable. The web URL is
        # updated every 2min and has a higher reliability.
        _url = "https://kernel.ubuntu.com/info/sru-cycle.yaml"

        # The data source can be set from the environment but only if not directly done from
        # the command line.
        if data is None:
            data = os.getenv("SRU_CYCLE_USE", None)

            # Deprecated mathod of overriding the data location
            if data is None and os.getenv("USE_LOCAL_SRU_CYCLE_YAML", False):
                warn("Use of USE_LOCAL_SRU_CYCLE_YAML is deprecated, use SRU_CYCLE_USE=local instead.")
                data = "local"

        _data = None
        if data:
            if isinstance(data, dict):
                self._url = "raw-data"
                self._data = data.copy()
            elif isinstance(data, str):
                if data == "default" or data == "remote":
                    pass
                elif data.startswith("remote:"):
                    _url = data.split(":", 1)[1]
                elif data == "local":
                    _url = "file://" + os.path.join(KERNEL_VERSIONS_DIR, "sru-cycle.yaml")
                elif data.startswith("local:"):
                    _url = "file://" + data.split(":", 1)[1]
                else:
                    raise ValueError("Invalid data provided!")
            else:
                raise ValueError("{} is not a valid data source!".format(data))

        if not self._data:
            self._url = _url
            if not _data:
                try:
                    response = urlopen(_url)
                    _data = response.read()
                except:
                    warn("Unable to open {}. Dataset will be empty!".format(_url))
                    _data = SRU_CYCLE_HEADER
            if not isinstance(_data, str):
                _data = _data.decode("utf-8")
            self._data = yaml.safe_load(_data)
            if not self._data:
                self._data = {}

    @property
    def data_source(self):
        """
        Returns the URL of the data source which was used to create the instance
        """
        return self._url

    @property
    def cycles(self):
        cl = []
        for key in sorted(self._data.keys(), key=self.key_name, reverse=True):
            cl.append(self.__cached_lookup(key))
        return cl

    def lookup_cycle(self, cycle=None, allow_missing=False):
        """
        Search for the given cycle ([ds]YYYY.MM.DD). If there is none found it either
        returns None or a minimally initialized SruCycleSpinEntry for the cycle date
        (allow_missing=True).

        cycle (string): name of the cycle to search
        allow_missing (bool): if false the search will return None if not found, otherwise
            a SruCycleSpinEntry() with just the name set will be returned.
        """
        if not cycle:
            raise ValueError("cycle required")
        if "-" in cycle:
            raise ValueError("cycle contains a spin number")

        if cycle in self._data:
            entry = self.__cached_lookup(cycle)
        elif allow_missing:
            entry = SruCycleSpinEntry(cycle).attach(self)
        else:
            entry = None

        return entry

    def lookup_spin(self, spin=None, allow_missing=False):
        """
        Search for a given spin ([ds]YYYY.MM.DD-S) in the dataset. If there is no
        spin found but a matching cycle without a spin number is, then that cycle
        gets returned instead.

        returns SruCycleSpinEntry() or None
            When allow_missing is set to True and no matching entry is found, then
            instead of None we return a minimally instantiated spin object.
        """
        if not spin:
            raise ValueError("spin required")
        if "-" not in spin:
            raise ValueError("argument does not contain a spin number")

        cycle, spin_nr = spin.split("-")
        if spin in self._data:
            entry = self.__cached_lookup(spin)
        elif cycle in self._data:
            entry = self.__cached_lookup(cycle)
        elif allow_missing:
            entry = SruCycleSpinEntry(spin).attach(self)
        else:
            entry = None

        return entry

    def add_cycle(self, cycle):
        """
        Adds a new cycle to the current database. The cycle must not already exist.

        cycle (SruCycleSpinEntry): new cycle entry to add

        returns: nothing
        raises:  ValueError if cycle already exists
        """
        if not isinstance(cycle, SruCycleSpinEntry):
            raise ValueError("cycle is not a SruCycleSpinEntry")
        if self.lookup_cycle(cycle.name) is not None:
            raise ValueError("Cycle {} already exists!".format(cycle.name))
        self._data[cycle.name] = copy(cycle).attach(self)

    def delete_cycle(self, cycle):
        """
        Deletes an existing cycle from the current database. If there is no cycle of
        the given name, nothing will happen.
        """
        if cycle in self._data:
            del self._data[cycle]

    def write(self):
        """
        Writes the current cycle info data back to a local: URL. Does nothing
        for any other source.
        """
        if not self._url.startswith("file://"):
            return
        with open(self._url[7:], "wt") as f:
            try:
                f.write(str(self))
            except:
                warn("Could not write to {}".format(self._url))

    def __str__(self):
        """
        Returns the YAML representation of sru-cycle.yaml as a string (including
        the informational header. This can be used to write a new file after any
        changes.
        """
        s = SRU_CYCLE_HEADER
        for cycle in self.cycles:
            s += "\n" + str(cycle)
        return s
