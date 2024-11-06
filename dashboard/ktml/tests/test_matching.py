import pytest
from ..matching import match_handle, match_handles, match_patch_count, match_patch_subject


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
]

patch_count_data = [
    ("[SRU][J][PATCH 0/10] Test handle", "10"),
    ("[SRU][J][PATCH 0/1] Test handle", "1"),
    ("[SRU][PATCH 0/5][J] Test handle", "5"),
    ("[SRU][PATCH 0/500][J] Test handle", "500"),
]

patch_matching_data = [
    ("[SRU][J][PATCH 2/5] Test handle", "J", "2", "5", True),
    ("[SRU][jammy:linux][PATCH 2/5] Test handle", "jammy:linux", "2", "5", True),
    ("[SRU][jammy:linux-ein][PATCH 2/5] Test handle", "jammy:linux-ein", "2", "5", True),
    ("[SRU][J][PATCH 5/5] Test handle", "J", "5", "5", True),
    ("[SRU][J/X][PATCH 5/5] Test handle", "J", "5", "5", True),
    ("[SRU][J][X][PATCH 5/5] Test handle", "J", "5", "5", True),
    ("[SRU][J][PATCH 2/5] Test handle", "J", "3", "5", False),
    ("[SRU][Jammy:linux-ein][PATCH 2/5] Test handle", "J", "2", "5", False),
    ("[SRU][J][PATCH 2/5] Test handle", "X", "2", "5", False),
    ("[SRU][X][PATCH 2/5] Test handle", "J", "2", "5", False),
]


@pytest.mark.parametrize("subject, expected", handle_data)
def test_handle(subject, expected):
    assert expected == match_handle(subject)


@pytest.mark.parametrize("subject, expected", subject_data)
def test_handles(subject, expected):
    assert expected == match_handles(subject)


@pytest.mark.parametrize("subject, expected", patch_count_data)
def test_patch_count(subject, expected):
    assert expected == match_patch_count(subject)


@pytest.mark.parametrize("subject, raw_handle, index, patch_count, expected", patch_matching_data)
def test_patch_subject(subject, raw_handle, index, patch_count, expected):
    assert expected == match_patch_subject(subject, raw_handle, index, patch_count)


def test_failed_handle():
    with pytest.raises(AttributeError):
        match_handles("[SRU][PATCH 0/1] Test handle")


def test_failed_patch_cnt():
    with pytest.raises(AttributeError):
        match_patch_count("[SRU][PULL] Test handle")
