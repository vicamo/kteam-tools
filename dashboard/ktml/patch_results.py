"""Module to store and retrieve previous patch test results

"""

from glob import glob
from pathlib import Path
import re


class PatchResults:
    def __init__(self, path, dry_run):
        self.path = path
        self.results = []
        self.dry_run = dry_run
        # Find all results associated
        for results in glob(path + ".*.*_*"):
            match = re.search(path + "\\.(.*)\\.(.*)_(.*)", results)
            status = {"handle": match.group(1), "operation": match.group(2)}
            res = match.group(3)
            if "fail" in res:
                status["ret"] = False
            if "succeed" in res or "pass" in res:
                status["ret"] = True
            with open(results) as f:
                status["comment"] = f.read()
            self.results.append(status)

    def exist(self, operation, handle):
        for result in self.results:
            if result["handle"] == handle and result["operation"] == operation:
                return True
        return False

    def update(self, operation, result, handle, msg):
        if self.dry_run:
            return
        # Remove previous result
        previous_result = glob(f"{self.path}.{handle}.{operation}_*")
        if previous_result:
            Path.unlink(previous_result[0])
        with open(f"{self.path}.{handle}.{operation}_{result}", "w") as f:
            print(msg, file=f)
