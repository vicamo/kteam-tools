#!/usr/bin/env python3
#
# Python wrapper for the cranky shell script
#

import os
import subprocess
import sys

def main():
    realhome = os.environ.get("SNAP_REAL_HOME")
    if realhome:
        # If run as a snap, snapd sets HOME to a snap-specific directory
        # ~/snap/cranky/<version> which breaks cranky completely, so reset
        # it to its real value.
        os.environ["HOME"] = realhome

    cranky = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          "cranky")
    return subprocess.call([cranky] + sys.argv[1:])

if __name__ == "__main__":
    sys.exit(main())
