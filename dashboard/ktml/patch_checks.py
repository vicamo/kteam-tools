"""Module to run checks on patchset already prepared

"""


import re
import subprocess
from pathlib import Path


# To be retried later
class TemporaryError(Exception):
    pass


class CheckError(Exception):
    pass


class PatchChecks:
    def __init__(self, official_handle, patches, patchset_cover):
        self.official_handle = official_handle
        self.patches = patches
        self.kernel_path = (
            subprocess.run(
                ["cranky", "shell-helper", "tree-main-path", official_handle], stdout=subprocess.PIPE, check=True
            )
            .stdout.decode("utf-8")
            .strip("\n")
        )
        self.patchset_cover = patchset_cover

    def check_am(self):
        # checkout correct kernel dir
        subprocess.run(["cranky", "checkout", self.official_handle, "--pristine"], check=True)

        # Apply patches
        cmd = ["git", "am", "--ignore-space-change"]
        cmd += [x[":path"] for x in self.patches]
        try:
            subprocess.run(cmd, cwd=self.kernel_path, check=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git", "am", "--abort"], cwd=self.kernel_path, check=True)
            raise CheckError("git am failed")

    def check_build(self):
        unique_id = Path(self.patchset_cover["path"]).name
        try:
            result = subprocess.run(
                ["git", "push", "--progress", "cbd", f"HEAD:refs/heads/{unique_id}"],
                cwd=self.kernel_path,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError:
            raise TemporaryError(f"Failed to push {unique_id} for {self.official_handle}")
        search = re.search("\\S+/BUILD-FAILED", result.stdout.decode("utf-8"))
        if search:
            raise CheckError(f"{search[0]}")
        else:
            search = re.search("\\S+/BUILD-OK", result.stdout.decode("utf-8"))
            return search[0]
