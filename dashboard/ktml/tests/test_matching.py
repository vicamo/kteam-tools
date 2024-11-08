import pytest
import os
from matching import (
    MatchHandles,
    match_handle,
    match_handles,
    match_patch_count,
    match_patch_subject,
    match_patchset,
    ParsingPatchesError,
)

handle_data = [
    ("J", "jammy:linux"),
    ("J", "jammy:linux"),
    ("J:linux", "jammy:linux"),
    ("j", "jammy:linux"),
    ("jammy:linux", "jammy:linux"),
    ("JAMMY:LINUX", "jammy:linux"),
    ("j:gcp", "jammy:linux-gcp"),
    ("f:linux-ein", "focal:linux-ein"),
    ("N:nvidia-lowlatency", "noble:linux-nvidia-lowlatency"),
]

subject_data = [
    ("[SRU][J][PATCH 0/1] Test handle", [("J", "jammy:linux")]),
    ("[SRU][J][PATCH 0/1] Test handle Xenial:linux", [("J", "jammy:linux")]),
    ("[SRU][J:linux][PATCH 0/1] Test handle", [("J:linux", "jammy:linux")]),
    ("[SRU][j][PATCH 0/1] Test handle", [("j", "jammy:linux")]),
    ("[SRU][jammy:linux][PATCH 0/1] Test handle", [("jammy:linux", "jammy:linux")]),
    (
        "[SRU][B/X/F/J][PATCH 0/1] Test handle",
        [("B", "bionic:linux"), ("X", "xenial:linux"), ("F", "focal:linux"), ("J", "jammy:linux")],
    ),
    ("[SRU][j:gcp/j:gke][PATCH 0/1] Test handle", [("j:gcp", "jammy:linux-gcp"), ("j:gke", "jammy:linux-gke")]),
    ("[SRU][N][PATCH 0/1] Test handle", [("N", "noble:linux")]),
    (
        "[SRU][xenial:linux/oracular:non-existing-linux][PATCH 0/1] Test handle",
        [("xenial:linux", "xenial:linux"), ("oracular:non-existing-linux", None)],
    ),
    ("[SRU][jemmy:linux][PATCH 0/1] Test handle", [("jemmy:linux", "jammy:linux")]),
    ("[SRU][T/X][PATCH 0/1] Test handle", [("T", "trusty:linux"), ("X", "xenial:linux")]),
]

patch_count_data = [
    ("[SRU][J][PATCH 0/10] Test handle", "10"),
    ("[SRU][J][PATCH 0/1] Test handle", "1"),
    ("[SRU][PATCH 0/5][J] Test handle", "5"),
    ("[SRU][PATCH 0/500][J] Test handle", "500"),
    ("[N][PATCH 2/2] UBUNTU: SAUCE: apparmor4.0.0 [95/99]:", "2"),
]

patch_matching_data_count = [
    ("[SRU][J][PATCH 2/5] Test handle", "J", "2", True),
    ("[SRU][jammy:linux][PATCH 2/5] Test handle", "jammy:linux", "2", True),
    ("[SRU][jammy:linux-ein][PATCH 2/5] Test handle", "jammy:linux-ein", "2", True),
    ("[SRU][J][PATCH 5/5] Test handle", "J", "5", True),
    ("[SRU][J/X][PATCH 5/5] Test handle", "J", "5", True),
    ("[SRU][J][X][PATCH 5/5] Test handle", "J", "5", True),
    ("[SRU][J][PATCH 2/5] Test handle", "J", "3", False),
    ("[SRU][Jammy:linux-ein][PATCH 2/5] Test handle", "J", "2", False),
    ("[SRU][J][PATCH 2/5] Test handle", "X", "2", False),
    ("[SRU][X][PATCH 2/5] Test handle", "J", "2", False),
    ("[N][PATCH 2/2] UBUNTU: SAUCE: apparmor4.0.0 [95/99]:", "N", "2", True),
]

patchset_data = [
    ("[SRU][B/X][PATCH 0/5] CVE-2024"),
    ("[SRU][B][PATCH 1/5] Bluetooth: SCO: Fix not validating setsockopt user input"),
    ("[SRU][B][PATCH 2/5] Bluetooth: RFCOMM: Fix not validating setsockopt user input"),
    ("[SRU][B][PATCH 3/5] Bluetooth: L2CAP: uninitialized variables in l2cap_sock_setsockopt()"),
    ("[SRU][B][PATCH 4/5] Bluetooth: L2CAP: Fix not validating setsockopt user input"),
    ("[SRU][B][PATCH 5/5] Bluetooth: hci_sock: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 1/5] Bluetooth: SCO: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 2/5] Bluetooth: RFCOMM: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 3/5] Bluetooth: L2CAP: uninitialized variables in l2cap_sock_setsockopt()"),
    ("[SRU][X][PATCH 4/5] Bluetooth: L2CAP: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 5/5] Bluetooth: hci_sock: Fix not validating setsockopt user input"),
]

patchset_data_single = [
    ("[SRU][B/X][PATCH 0/5] CVE-2024"),
    ("[SRU][B/X][PATCH 1/5] Bluetooth: SCO: Fix not validating setsockopt user input"),
    ("[SRU][B/X][PATCH 2/5] Bluetooth: RFCOMM: Fix not validating setsockopt user input"),
    ("[SRU][B/X][PATCH 3/5] Bluetooth: L2CAP: uninitialized variables in l2cap_sock_setsockopt()"),
    ("[SRU][B/X][PATCH 4/5] Bluetooth: L2CAP: Fix not validating setsockopt user input"),
    ("[SRU][B/X][PATCH 5/5] Bluetooth: hci_sock: Fix not validating setsockopt user input"),
]

patchset_data_varying_patch_cnt = [
    ("[SRU][B/X][PATCH 0/2] CVE-2024"),
    ("[SRU][B][PATCH 0/5] CVE-2024"),
    ("[SRU][X][PATCH 0/3] CVE-2024"),
    ("[SRU][B][PATCH 1/5] Bluetooth: SCO: Fix not validating setsockopt user input"),
    ("[SRU][B][PATCH 2/5] Bluetooth: RFCOMM: Fix not validating setsockopt user input"),
    ("[SRU][B][PATCH 3/5] Bluetooth: L2CAP: uninitialized variables in l2cap_sock_setsockopt()"),
    ("[SRU][B][PATCH 4/5] Bluetooth: L2CAP: Fix not validating setsockopt user input"),
    ("[SRU][B][PATCH 5/5] Bluetooth: hci_sock: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 1/3] Bluetooth: SCO: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 2/3] Bluetooth: RFCOMM: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 3/3] Bluetooth: L2CAP: uninitialized variables in l2cap_sock_setsockopt()"),
]

patchset_data_missing = [
    ("[SRU][B/X][PATCH 0/2] CVE-2024"),
    ("[SRU][B][PATCH 0/5] CVE-2024"),
    ("[SRU][X][PATCH 0/3] CVE-2024"),
    ("[SRU][B][PATCH 1/5] Bluetooth: SCO: Fix not validating setsockopt user input"),
    ("[SRU][B][PATCH 3/5] Bluetooth: L2CAP: uninitialized variables in l2cap_sock_setsockopt()"),
    ("[SRU][B][PATCH 4/5] Bluetooth: L2CAP: Fix not validating setsockopt user input"),
    ("[SRU][B][PATCH 5/5] Bluetooth: hci_sock: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 1/3] Bluetooth: SCO: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 2/3] Bluetooth: RFCOMM: Fix not validating setsockopt user input"),
    ("[SRU][X][PATCH 3/3] Bluetooth: L2CAP: uninitialized variables in l2cap_sock_setsockopt()"),
]


def data_to_entries(data_list):
    full_entries = []
    for data in data_list:
        entry = {":subject": data}
        full_entries.append(entry)
    return full_entries


class TestMatchHandle:
    @classmethod
    def setup_class(cls):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "handles.list")) as handle_data:
            handles = [handle.strip() for handle in handle_data.readlines() if handle != ""]
        MatchHandles.handle_cache = handles

    @pytest.mark.parametrize("subject, expected", handle_data)
    def test_handle(self, subject, expected):
        assert expected == match_handle(subject)

    @pytest.mark.parametrize("subject, expected", subject_data)
    def test_handles(self, subject, expected):
        assert expected == match_handles(subject)

    @pytest.mark.parametrize("subject, expected", patch_count_data)
    def test_patch_count(self, subject, expected):
        assert expected == match_patch_count(subject)

    def test_failed_handle(self):
        with pytest.raises(AttributeError):
            match_handles("[SRU][PATCH 0/1] Test handle")

    def test_failed_patch_cnt(self):
        with pytest.raises(AttributeError):
            match_patch_count("[SRU][PULL] Test handle")

    @pytest.mark.parametrize("subject, raw_handle, index, expected", patch_matching_data_count)
    def test_patch_subject(self, subject, raw_handle, index, expected):
        assert expected == match_patch_subject(subject, raw_handle, index)

    def test_full_patchset(self):
        full_entries = data_to_entries(patchset_data)
        patches = match_patchset(full_entries, "B")
        for i, patch in enumerate(patches):
            assert patch[":subject"] == patchset_data[i + 1]
        patches = match_patchset(full_entries, "X")
        for i, patch in enumerate(patches):
            assert patch[":subject"] == patchset_data[i + 6]

    def test_single_patchset(self):
        full_entries = data_to_entries(patchset_data_single)
        patches = match_patchset(full_entries, "B")
        for i, patch in enumerate(patches):
            assert patch[":subject"] == patchset_data_single[i + 1]
        patches = match_patchset(full_entries, "X")
        for i, patch in enumerate(patches):
            assert patch[":subject"] == patchset_data_single[i + 1]

    def test_varying_patch_cnt(self):
        full_entries = data_to_entries(patchset_data_varying_patch_cnt)
        patches = match_patchset(full_entries, "B")
        for i, patch in enumerate(patches):
            assert patch[":subject"] == patchset_data_varying_patch_cnt[i + 3]
        patches = match_patchset(full_entries, "X")
        for i, patch in enumerate(patches):
            assert patch[":subject"] == patchset_data_varying_patch_cnt[i + 8]

    def test_data_missing(self):
        full_entries = data_to_entries(patchset_data_missing)
        with pytest.raises(ParsingPatchesError):
            patches = match_patchset(full_entries, "B")
        patches = match_patchset(full_entries, "X")
        for i, patch in enumerate(patches):
            assert patch[":subject"] == patchset_data_missing[i + 7]
