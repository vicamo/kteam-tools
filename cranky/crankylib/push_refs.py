#
# push-refs subcommand
#

from crl.git import GitHandleSet
from ktl.log import cerror, cnotice


def push_refs(handle, cycle=None, dry_run=False):
    """Push refs (HEADs and tags) that make up the set of kernel packages"""
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
