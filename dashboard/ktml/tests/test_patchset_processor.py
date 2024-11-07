from patchset_processor import PatchsetProcessor
from unittest.mock import Mock, patch
import os
import json
from matching import MatchHandles

# ruff: noqa: E501
expected_big = [
    (
        ["noble:linux-nvidia-lowlatency/ready:[SRU][N:nvidia-lowlatency][PATCH 0/2] Fix packaging"],
        [],
    ),
    (
        [],
        # Expected, missing handle in patches
        ["parsing", "fail", "jammy:linux-bluefield", ""],
    ),
    (
        [],
        # Expected, missing handle in patches
        ["parsing", "fail", "oracular:linux", ""],
    ),
    (
        [
            "noble:linux/ready:[SRU][N][PATCH 0/2] Backport some AppArmor complain-mode profile bugfixes from Oracular to Noble"
        ],
        [],
    ),
    (
        [],
        # Very complicated handle, not supported right now
        ["parsing", "fail", "Unknown", ""],
    ),
    (
        [
            "jammy:linux-bluefield/ready:[SRU][J:linux-bluefield][PATCH v1 0/1] UBUNTU: SAUCE: i2c-mlxbf: Repeated start support"
        ],
        [],
    ),
    (
        ["focal:linux-aws/ready:[SRU][F:aws][PATCH v2 0/1] Set CONFIG_LOG_BUF_SHIFT=18 on all 64bit arches"],
        [],
    ),
    (
        [],
        # Missing handle entirely
        ["parsing", "fail", "Unknown", ""],
    ),
]


class TestMatchHandle:
    @classmethod
    def setup_class(cls):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "handles.list")) as handle_data:
            handles = [handle.strip() for handle in handle_data.readlines() if handle != ""]
        MatchHandles.handle_cache = handles

    @patch("ktl.log.cdebug")
    def test_big_data(self, cdebug):
        index_expected = 0
        with open("dashboard/ktml/tests/fixtures/pending_big.json") as input:
            pending_patchsets_search = json.load(input)
        for patchset in pending_patchsets_search:
            cdebug.reset_mock()
            p = PatchsetProcessor(patchset, True)
            p.patch_result.update = Mock()
            p.patchset_processing()
            if expected_big[index_expected][0]:
                cdebug.was_called_with(expected_big[index_expected][0])
            if expected_big[index_expected][1]:
                p.patch_result.update.was_called_with(
                    expected_big[index_expected][1][0],
                    expected_big[index_expected][1][1],
                    expected_big[index_expected][1][2],
                    expected_big[index_expected][1][3],
                )
            index_expected += 1
