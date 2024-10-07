
import argparse
import json
import os
import sys
from copy import deepcopy
from datetime import datetime
from fcntl import lockf, LOCK_EX, LOCK_NB, LOCK_UN
from urllib.request import pathname2url, urljoin, urlopen


# SruSpinsDataHandle
#
class SruSpinsDataHandle:
    def __init__(self, spin, data, full_versions=None):
        self.spin = spin
        self.tracker = data.get("tracker")
        self.versions = data.get("versions")

        self.full_versions = self.versions


# SruSpinsData
#
class SruSpinsIndex:
    @classmethod
    def from_loader(cls, loader, updater=None):
        return SruSpinsIndex(loader("index"), loader, updater=updater)

    def __init__(self, cycles, loader=None, updater=None):
        self._cycles = cycles
        self._loader = loader
        self._updater = updater

    def spin_key(self, data):
        return int(data[0]), data[1]

    def cycle(self, cycle):
        cycle_data = self._cycles.get(cycle)
        if cycle_data is None:
            return None
        if cycle_data is True:
            cycle_data = self._loader(cycle)
            self._cycles[cycle] = cycle_data
        return cycle_data

    def _populate_spin(self, handle, cycle, cycle_data, spin=None):
        result = None
        full_versions = {}
        for spin_no, spin_data in sorted(cycle_data.items(), key=self.spin_key, reverse=True):
            if handle in spin_data:
                result = SruSpinsDataHandle(f"{cycle}-{spin_no}", spin_data[handle])
                full_versions.update(result.versions)
                result.full_versions = full_versions
            #print(spin_no, spin_data, result)

            if spin is not None and spin == spin_no:
                break

        if spin is not None and spin != spin_no:
            return None

        return result

    def handle_cycle(self, handle, cycle):
        cycle_data = self.cycle(cycle)
        if cycle_data is None:
            return None
        return self._populate_spin(handle, cycle, cycle_data)

    def handle_spin(self, handle, spin):
        try:
            cycle, spin_no = spin.rsplit("-", 1)
        except ValueError:
            return None
        cycle_data = self.cycle(cycle)
        if cycle_data is None:
            return None
        return self._populate_spin(handle, cycle, cycle_data, spin_no=spin_no)

    def handle_spin_update(self, handle, spin, data):
        self._updater(spin, handle, data)


# SruSpins
#
class SruSpins:
    _url = 'https://kernel.ubuntu.com/swm/spin-info'
    _local = 'spin-info'

    @classmethod
    def from_json(cls, json_data):
        return SruSpinsIndex(json.loads(json_data))

    @classmethod
    def _load_path(cls, path_base, part):
        path = os.path.join(path_base, part + ".json")
        with open(path) as jfd:
            json_data = jfd.read()
        return json.loads(json_data)

    @classmethod
    def _write_path(cls, path_base, part, data):
        path = os.path.join(path_base, part + ".json")
        with open(path + ".new", "w") as jfd:
            json.dump(data, jfd)
        os.rename(path + ".new", path)

    @classmethod
    def _update_path(cls, path_base, spin, handle, data):
        cycle, spin_no = spin.rsplit("-", 1)

        # Lock the index so we can perform the update.
        path = os.path.join(path_base, ".index.lck")
        with open(path, "a") as lfd:
            lockf(lfd, LOCK_EX, 1, 0)

            index_data = cls._load_path(path_base, "index")
            index_data_before = deepcopy(index_data)
            if cycle not in index_data:
                index_data[cycle] = True
                cycle_data = {}
            else:
                cycle_data = cls._load_path(path_base, cycle)
            cycle_data_before = deepcopy(cycle_data)

            # Update the entry.
            entry = cycle_data.setdefault(spin_no, {}).setdefault(handle, {})
            entry.update(data)

            # If the data is changed, update it.
            if cycle_data != cycle_data_before:
                cls._write_path(path_base, cycle, cycle_data)
            if index_data != index_data_before:
                cls._write_path(path_base, "index", index_data)

            lockf(lfd, LOCK_UN, 1, 0)

    @classmethod
    def from_path(cls, path):
        return SruSpinsIndex.from_loader(
            lambda cycle: cls._load_path(path, cycle),
            updater=lambda spin, handle, data: cls._update_path(path, spin, handle, data),
        )

    @classmethod
    def _load_url(cls, url_base, part):
        url = url_base + "/" + part + ".json"
        response = urlopen(url)
        json_data = response.read()
        if isinstance(json_data, bytes):
            json_data = json_data.decode('utf-8')
        return json.loads(json_data)

    @classmethod
    def from_url(cls, url):
        return SruSpinsIndex.from_loader(
            lambda cycle: cls._load_url(url, cycle),
        )

    @classmethod
    def from_local(cls):
        return cls.from_path(cls._local)

    def __new__(cls):
        return cls.from_url(cls._url)
        #return cls.from_path(cls._local)


if __name__ == "__main__":
    sru_spins = SruSpins.from_local()

    #handle_data = sru_spins.handle_cycle("noble:linux", "2024.08.05")
    #print(handle_data.spin, handle_data.versions)

    #handle_data = sru_spins.handle_spin("noble:linux", "2024.08.05-3")
    #print(handle_data.spin, handle_data.versions)

    #handle_data = sru_spins.handle_cycle("noble:linux", "2024.06.10")
    #print(handle_data.spin, handle_data.versions)

    sru_spins.handle_spin_update("noble:linux", "2024.08.05-3", {"versions": {"main": "1.2.3"}})
    sru_spins.handle_spin_update("noble:linux", "2024.08.05-2", {"versions": {"main": "1.2.2"}})
