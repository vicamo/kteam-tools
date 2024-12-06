#
# Cranky format-kernel-series
#

import os
import sys

from crankylib import cli
from ktl.log import cinfo, cerror
from ktl.git import Git
from ktl.format_kernel_series import KernelSeriesYamlFormat

epilog_format_kernel_series = """
Examples:

$ cranky format-kernel-series

    Formats the kernel-series.yaml files modified in the current kernel-versions repo

    It MUST be run from the top of the kernel-versions repo
"""


@cli.command(epilog=epilog_format_kernel_series)
def format_kernel_series():
    """Formats the kernel-series.yaml files modified in the current kernel-versions repo
    It MUST be run from the top of the kernel-versions repo
    In case there are multiple files that need to be formatted, it does this file by file
    If manual intervention is needed for one file (i.e to remove a duplicate key), the script
    stops. To continue reformatting the rest of the file, the command should be run again
    """
    # It should be run in the kernel-versions repo.
    # info/kernel-series.yaml will always be there so it's safe to check
    # if the file exists
    if not Git.is_repo():
        cerror("This directory is not a git repo")
        sys.exit(1)

    if not os.path.isfile("info/kernel-series.yaml"):
        cerror("You must run this script from the top directory of the kernel-versions repo")
        sys.exit(1)

    modified_ks_files = [f for f in Git.list_modified_files() if "kernel-series.yaml" in f]
    for ks_file in modified_ks_files:
        cinfo("Formatting {}".format(ks_file))
        try:
            KernelSeriesYamlFormat.reformat(ks_file)
        except Exception as e:
            cerror(e)
            sys.exit(1)
