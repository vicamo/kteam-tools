
import argparse
import json
import os
import sys
from datetime import datetime
from urllib.request import pathname2url, urljoin, urlopen


# SruSpinsDataHandle
#
class SruSpinsDataHandle:
    def __init__(self, spin, data):
        self.spin = spin
        self.tracker = data.get("tracker")
        self.versions = data.get("versions")


# SruSpinsData
#
class SruSpinsIndex:
    @classmethod
    def from_loader(cls, loader):
        return SruSpinsIndex(loader("index"), loader)

    def __init__(self, cycles, loader=None):
        self._cycles = cycles
        self._loader = loader

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

    def handle_cycle(self, handle, cycle):
        cycle_data = self.cycle(cycle)
        if cycle_data is None:
            return None
        for spin_no, spin_data in sorted(cycle_data.items(), key=self.spin_key, reverse=True):
            if handle in spin_data:
                return SruSpinsDataHandle(f"{cycle}-{spin_no}", spin_data[handle])
        return None

    def handle_spin(self, handle, spin):
        cycle, spin_no = spin.rsplit("-", 1)
        cycle_data = self.cycle(cycle)
        if cycle_data is None:
            return None
        spin_data = cycle_data.get(spin_no)
        if spin_data is None:
            return None
        if handle in spin_data:
            return SruSpinsDataHandle(spin, spin_data[handle])
        return None


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
    def from_path(cls, path):
        return SruSpinsIndex.from_loader(
            lambda cycle: cls._load_path(path, cycle),
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
    sru_spins = SruSpins()

    handle_data = sru_spins.handle_cycle("noble:linux", "2024.08.05")
    print(handle_data.spin, handle_data.versions)

    handle_data = sru_spins.handle_spin("noble:linux", "2024.08.05-3")
    print(handle_data.spin, handle_data.versions)

    handle_data = sru_spins.handle_cycle("noble:linux", "2024.06.10")
    print(handle_data.spin, handle_data.versions)
