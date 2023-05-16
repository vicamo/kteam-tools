#!/usr/bin/env python3
#
# Python wrapper for the cranky shell script
#

import os
import subprocess
import sys

def main():
    cranky = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                          "cranky")
    return subprocess.call([cranky] + sys.argv[1:])

if __name__ == "__main__":
    sys.exit(main())
