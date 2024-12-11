#
# update-changelog subcommand
#

import os
import re
import textwrap
import time

import apt_pkg
import git
import requests

from debian.changelog import ChangeBlock, Changelog, format_date

from . import error


def wrap_line(line, width=0):
    """Wrap and indent a line"""
    if width == 0 or isinstance(line, _nowrap):
        return [line]

    if line.startswith("* "):
        prefix = "* "
        line = line[2:]
    elif line.startswith("  - "):
        prefix = "  - "
        line = line[4:]
    else:
        return [line]

    # Prevent wrapping in LP and //
    line = line.replace("LP: ", "LP__").replace(" //", "_//")

    wrapped = []
    for text in textwrap.wrap(line, width - len(prefix)):
        text = text.replace("LP__", "LP: ").replace("_//", " //")
        wrapped.append(prefix + text)
        prefix = " " * len(prefix)
    return wrapped


def url_get(url):
    """http get with retries"""
    for _ in range(2):
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code not in (429, 500, 502, 503, 504):
                return resp
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    raise error.CrankyError(f"Failed to get {url}")


def get_title_from_lp(bug):
    """Get a bug title from Launchpad"""
    url = f"https://api.launchpad.net/devel/bugs/{bug}"
    resp = url_get(url)
    if resp.status_code == 200:
        data = resp.json()
        title = data["title"]
        for line in data.get("description", "").split("\n"):
            if line.startswith("Kernel-Description:"):
                title = line.split(" ", 1)[1]
                break
    else:
        title = "INVALID or PRIVATE BUG"

    return f"{title} (LP: #{bug})"


class _nowrap(str):
    pass


class CommitEntry:
    def __init__(self, commit):
        self.commit = commit
        self.subject = None
        self.bugs = []
        self.cves = []
        self.ignore = False
        self.key = None

        self._parse_message()
        self._generate_key()

    def _parse_message(self):
        """Parse the commit message and fill in the blanks"""
        message = [m.strip() for m in self.commit.message.split("\n")]

        self.subject = message[0]
        self.bugs = set()
        self.cves = set()

        for line in message[1:]:
            # BugLink
            if line.startswith("BugLink: "):
                bits = line.split(" ", 2)
                if len(bits) > 2:
                    # There is text after the URL, so use that (after stripping the
                    # enclosing characters)
                    self.bugs.add(bits[2][1:-1])
                elif "launchpad.net" in bits[1]:
                    # Extract the bug number from the Launchpad URL
                    bug = bits[1].split("/")[-1]
                    self.bugs.add(bug)
                else:
                    raise error.CrankyError(f"Invalid BugLink: {line}")
                continue

            # CVE
            if line.startswith("CVE-"):
                self.cves.add(line)
                continue

            # Ignore
            if line.replace(" ", "").lower() in ("ignore:yes", "ignore:true"):
                self.ignore = True
                continue

            # Properties
            if line.startswith("Properties:"):
                for prop in line.split(" ")[1:]:
                    if prop in ("ignore", "no-changelog"):
                        self.ignore = True
                        break
                continue

        self.bugs = list(self.bugs)
        self.cves = list(self.cves)

    def _generate_key(self):
        """Generate a key for later sorting and combining"""
        if self.subject == "UBUNTU: link-to-tracker: update tracking bug":
            self.key = "__tracker__"
        elif self.bugs or self.cves:
            # Make this a tuple so it's hashable
            self.key = tuple(sorted(self.bugs + self.cves))
        elif self.subject.startswith("UBUNTU"):
            self.key = "__ubuntu__"
        else:
            self.key = "__mainline__"


class CommitSet:
    def __init__(self, version=None):
        self.version = version
        self.tracker = None
        self.ubuntu = []
        self.mainline = []
        self.fixes = {}
        self.fixes_keys = []

    def add(self, entry):
        """Add a single commit entry to the set"""
        if entry.ignore:
            return

        if entry.key == "__tracker__":
            if self.tracker:
                raise error.CrankyError("Only one tracking bug allowed")
            self.tracker = entry
            return

        if entry.key == "__ubuntu__":
            self.ubuntu.append(entry)
            return

        if entry.key == "__mainline__":
            self.mainline.append(entry)
            return

        # Collect all entries with same BugLink and CVE tags into separate lists
        if entry.key not in self.fixes_keys:
            self.fixes_keys.append(entry.key)
            self.fixes[entry.key] = []
        self.fixes[entry.key].append(entry)

    def changes(self):
        """Yield the list of changes in this set"""
        # 1. log entry: tracking bug
        if self.tracker:
            bug = self.tracker.bugs[0]
            title = get_title_from_lp(bug)
            yield _nowrap("* " + title)

        # 2. log entry: BugLink and CVE fixes
        for key in self.fixes_keys:
            title = []
            for token in key:
                if token.isdigit():
                    title.append(get_title_from_lp(token))
                else:
                    title.append(token)
            yield "* " + " // ".join(title)
            for entry in reversed(self.fixes[key]):
                yield "  - " + entry.subject.removeprefix("UBUNTU:").strip()

        # 3. log entry: Misc Ubuntu changes
        if self.ubuntu:
            yield "* Miscellaneous Ubuntu changes"
            for entry in reversed(self.ubuntu):
                yield "  - " + entry.subject.removeprefix("UBUNTU:").strip()

        # 4. log entry: Misc upstream changes
        if self.mainline:
            yield "* Miscellaneous upstream changes"
            for entry in reversed(self.mainline):
                yield "  - " + entry.subject

    def log(self, header=False):
        """Yield the log of this set"""
        if header and self.version:
            version = re.sub(r"(\D)-(\d)", r"\1: \2", self.version, count=1)
            yield f"[ {version} ]"

        for change in self.changes():
            yield change


def yield_rev_range(rev_range, header=False):
    """Yield the changes for the given commit revision range"""
    commit_set = CommitSet()
    for commit in git.Repo().iter_commits(rev_range):
        # Load the commit
        entry = CommitEntry(commit)

        # New release commit
        if entry.subject.startswith("UBUNTU: Ubuntu-"):
            # Yield the log of the current sent
            yield from commit_set.log(header=header)

            # Initialize a new set
            commit_set = CommitSet(entry.subject.removeprefix("UBUNTU:").strip())
            continue

        # Add the commit to the current set
        commit_set.add(entry)

    # Yield the log of the current set
    yield from commit_set.log(header=header)


def update_changelog(changelog=None, from_commit=None, from_version=None, from_changelog=None):
    """Update the Ubuntu kernel changelog"""
    if from_commit and from_version:
        raise error.CrankyUsageError("Only one of --from-commit or --from-version may be provided.")

    if not from_commit and not from_version:
        raise error.CrankyUsageError("One of --from-commit or --from-version must be provided.")

    if from_version and not from_changelog:
        raise error.CrankyUsageError("--from-changelog is required with --from-version.")

    if from_commit:
        # Collect the changes from the provided --from-commit commit-ish
        changes = []
        for line in yield_rev_range(f"{from_commit}..HEAD", header=True):
            if line.startswith("[ ") or line.startswith("* "):
                changes.append("")
                if not changelog:
                    print()

            for wrap in wrap_line(line, width=76):
                changes.append("  " + wrap)
                if not changelog:
                    print("  " + wrap)

    if from_changelog:
        apt_pkg.init()

        # Read the provided --from-changelog file
        with open(from_changelog, encoding="utf-8") as fh:
            ch = Changelog(fh)

        # Walk through the changelog and collect all changes up until
        # the provided --from-version version
        changes = []
        for cb in ch:
            if apt_pkg.version_compare(str(cb.version), from_version) <= 0:
                break

            header = ["", f"  [ Ubuntu{cb.package.removeprefix('linux')}: {cb.version} ]", ""]
            changes.extend(header)
            if not changelog:
                print("\n".join(header))

            for line in cb.changes():
                if not line.strip():
                    # Ignore empty lines
                    continue
                changes.append(line)
                if not changelog:
                    print(line)

    if not changelog:
        return

    # Read the provided --changelog file
    with open(changelog, encoding="utf-8") as fh:
        ch = Changelog(fh)

    # Get the top changeblock
    cb = ch[0]
    if cb.distributions != "UNRELEASED":
        raise error.CrankyError(f"Top changelog entry must be UNRELEASED but is: {cb.distributions}")

    # Collect the current changes from the top changeblock, drop any "CHANGELOG:" lines
    cur_changes = [line for line in cb.changes() if not line.startswith("  CHANGELOG: ")]

    # Assemble the new changes list
    new_changes = [""] + changes + [""] + cur_changes

    # Squeeze multiple subsequent empty lines
    squeezed = []
    prev_line = "foo"
    for line in new_changes:
        if line or (not line and prev_line):
            squeezed.append(line)
        prev_line = line
    new_changes = squeezed

    # Create the new top changeblock
    new_cb = ChangeBlock(
        package=cb.package,
        version=cb.version,
        distributions=cb.distributions,
        urgency=cb.urgency,
        urgency_comment=cb.urgency_comment,
        changes=new_changes,
        author=f"{os.getenv('DEBFULLNAME')} <{os.getenv('DEBEMAIL')}>",
        date=format_date(),
    )

    # Now we need to replace the current top block of the changelog with the newly
    # constructed one. python-debian doesn't really support this so we need to hack
    # around that limitation.
    new_cb.add_trailing_line("")
    ch._blocks[0] = new_cb

    # Finally write the changelog
    with open(changelog, "w", encoding="utf-8") as fh:
        ch.write_to_open_file(fh)
