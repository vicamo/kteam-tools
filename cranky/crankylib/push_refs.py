#
# push-refs subcommand
#

from dataclasses import dataclass
from typing import Optional

from crl.git import GitHandleSet

from ktl.log import cerror, cnotice


@dataclass
class PushSummary:
    """Represents a push performed by push_refs."""

    package_name: str
    directory: str
    url: str
    pushed: str
    dry_run: bool = False
    forced: bool = False

    @classmethod
    def from_git_handle(cls, gh, pushed: str, dry_run: bool = False, forced: bool = False):
        return cls(
            package_name=gh.package.name,
            directory=gh.directory,
            url=gh.get_url(),
            pushed=pushed,
            dry_run=dry_run,
            forced=forced,
        )

    def __str__(self):
        dry_run = "(dry run) " if self.dry_run else ""
        forced = " (forced)" if self.forced else ""

        return f"{dry_run}{self.package_name} ({self.directory}): pushed '{self.pushed}' to '{self.url}'{forced}"


def push_current_tag(gh, dry_run: bool = False) -> Optional[PushSummary]:
    current_tag = gh.get_current_tag()

    if not current_tag:
        cerror(f"No tag found for HEAD in {gh.directory}")
        return

    gh.push_ref(gh.remote, current_tag, dry_run=dry_run)
    return PushSummary.from_git_handle(gh, pushed=current_tag, dry_run=dry_run)


def push_head(gh, dry_run: bool = False) -> Optional[PushSummary]:
    forced = False
    rc = gh.push_ref(gh.remote, gh.remote_branch, "HEAD", dry_run=dry_run)

    if rc != 0:
        cerror(f"Unable to push HEAD to {gh.remote_branch}")
        user_input = input("Do you want to push --force-with-lease? [y/N]")
        if user_input == "y":
            rc = gh.push_ref(gh.remote, gh.remote_branch, "HEAD", force=True, dry_run=dry_run)
            forced = True
        else:
            return

    return PushSummary.from_git_handle(gh, pushed="HEAD:" + gh.remote_branch, dry_run=dry_run, forced=forced)


def push_refs(handle, cycle=None, dry_run: bool = False):
    """Push refs (HEADs and tags) that make up the set of kernel packages"""
    ghs = GitHandleSet(handle, cycle)

    cnotice(f"push_refs: codename: {ghs.codename}, source: {ghs.source.name}")

    summaries = []
    for gh in ghs:
        tag_summary = push_current_tag(gh, dry_run)
        if tag_summary is not None:
            summaries.append(tag_summary)

        head_summary = push_head(gh, dry_run)
        if head_summary is not None:
            summaries.append(head_summary)

    # The logs can get clogged by the stdout of the git commands ran. Group summaries
    # and print them at once.
    for tag_summary in summaries:
        cnotice(tag_summary)
