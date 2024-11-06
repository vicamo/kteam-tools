#
# Cranky push-refs
#

import sys

from crankylib import cli
from crankylib.cranky import Cranky

from ktl.log import cerror, Clog

from crl.exceptions import CrankyException
from crl.git import GitError
from crl.handle import HandleError

epilog_push_refs = """
Examples:

$ cranky push-refs xenial:linux

    Push the HEAD of 'linux', 'linux-meta' and 'linux-signed' to their
    corresponding remotes. Also push tags.

$ cranky push-refs .

    Push the HEAD of 'linux', 'linux-meta' and 'linux-signed' using
    current dir as a reference. Also push tags.
"""


@cli.command(epilog=epilog_push_refs)
@cli.option_color()
@cli.option_dry_run(help="Do not push any refs.")
@cli.option_deprecated_nc()
@cli.argument_handle()
def push_refs(color, dry_run, nc, handle):
    """Push the refs (HEAD and tags) to all remotes"""
    if nc:
        cli.option_deprecated_warn("push-refs", "--nc")
        color = False
    Clog.color = color
    try:
        Cranky().push_refs(handle, dry_run=dry_run)
    except (HandleError, GitError, CrankyException) as e:
        cerror(e)
        sys.exit(1)
