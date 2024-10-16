#
# Cranky push-refs
#

import sys

from crankylib import cli

from ktl.log import cerror, cnotice, Clog

from crl.exceptions import CrankyException
from crl.git import GitHandleSet, GitError
from crl.handle import HandleError


def _push_refs(handle, cycle=None, dry_run=False):
    """Push refs that make up the set of kernel packages"""
    ghs = GitHandleSet(handle, cycle)

    cnotice("Codename: {}".format(ghs.codename))
    cnotice("Source:   {}".format(ghs.source.name))

    summary = []
    for gh in ghs:
        pkg = gh.package
        remote = gh.remote
        rmt_branch = gh.remote_branch
        local_ref = "HEAD"
        current_tag = gh.get_current_tag()
        if not current_tag:
            cerror(f"No tag found for HEAD in {gh.directory}")
        else:
            gh.push_ref(remote, current_tag, dry_run=dry_run)
            summary.append({"name": pkg.name, "dir": gh.directory, "pushed": current_tag, "url": gh.get_url()})
        rc = gh.push_ref(remote, rmt_branch, local_ref, dry_run=dry_run)
        if rc != 0:
            cerror(f"Unable to push {local_ref} to {rmt_branch}")
            user_input = input("Do you want to push --force-with-lease? [y/N]")
            if user_input == "y":
                rc = gh.push_ref(remote, rmt_branch, local_ref, force=True, dry_run=dry_run)
        else:
            summary.append({"name": pkg.name, "dir": gh.directory, "pushed": "HEAD:" + rmt_branch, "url": gh.get_url()})

    # Print the summary
    cnotice("Summary:")
    for s in summary:
        cnotice("  Pkg '{name}' in directory '{dir}'\n" "   '{pushed}' to '{url}'".format(**s))


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
@cli.argument_handle()
def push_refs(color, dry_run, handle):
    """Push the refs (HEAD and tags) to all remotes"""
    Clog.color = color
    try:
        _push_refs(handle, dry_run=dry_run)
    except (HandleError, GitError, CrankyException) as e:
        cerror(e)
        sys.exit(1)
