#!/usr/bin/env python3
#
# Cranky entry point
#

import os
import sys

# HACK: This seems to be required when packaging for the snap
sys.path.append(os.path.dirname(__file__))

from crankylib import cli  # noqa (E402: Module level import not at top of file)


def main():
    realhome = os.environ.get("SNAP_REAL_HOME")
    if realhome:
        # If run as a snap, snapd sets HOME to a snap-specific directory
        # ~/snap/cranky/<version> which breaks cranky completely, so reset
        # it to its real value.
        os.environ["HOME"] = realhome

    # Run
    cli.cranky_cli()


if __name__ == "__main__":
    sys.exit(main())
