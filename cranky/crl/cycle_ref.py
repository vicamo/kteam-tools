import re
import shlex
import subprocess

from ktl.log import cdebug, cerror
from ktl.ubuntu_tag import UbuntuTag

from crl.exceptions import CrankyException


def run(cmd, allow_non_zero_exit_code=False, dry_run=False):
    output = ""
    dbg_cmd = " ".join(cmd)
    if dry_run:
        cdebug(f"Dry-run: {dbg_cmd}")
    else:
        cdebug(f"{dbg_cmd}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = result.stdout.decode("utf-8").strip()
        if result.returncode != 0 and not allow_non_zero_exit_code:
            output = result.stderr.decode("utf-8").strip()
            raise CrankyException(output)
    return output


class Git:
    """Git wrapper that does not modify your working directory
    git("subcommand [args]")
    """

    def __init__(self, repo_directory=None, git="git"):
        self.git = [git]
        if repo_directory:
            self.git += ["-C", repo_directory]
        cdebug(self.git)

    def __call__(self, args, split=None, allow_non_zero_exit_code=False, dry_run=False):
        cmd = self.git + shlex.split(args)
        result = run(cmd, allow_non_zero_exit_code, dry_run)
        if split and result:
            result = result.split(split)
        return result


def make_tag_prefix(handle):
    pkg = handle.package
    sep = "." if pkg.type == "meta" else "-"
    prefix = pkg.source.name.replace("linux", "Ubuntu")
    upstream = pkg.source.versions[-1]
    # FIXME: find out backports suffix (sans "upload" number)
    suffix = ""
    tag_prefix = prefix + "-" + upstream + sep + "*" + suffix
    return tag_prefix


def read_cycle(git, tag):
    """Return debian folder for this handle"""
    tracking_bug_contents = ""
    if git(f"ls-files {tag} debian/debian.env", split="\n"):
        debian_env = git(f"show {tag}:debian/debian.env", split="\n")

        debian_dir = "debian.master"
        for line in debian_env:
            if "DEBIAN=" in line:
                (var, val) = line.split("=", 1)
                val = val.rstrip()

                if var == "DEBIAN":
                    debian_dir = val
                    break
        tracking_bug_path = f"{debian_dir}/tracking-bug"
        try:
            tracking_bug_contents = git(f"show {tag}:{tracking_bug_path}")
        except:
            # Older tags might not have a tracking-bug, ignore them
            pass

    _, _, cycle = tracking_bug_contents.partition(" ")

    #
    # Fix old-style cycle
    cycle = cycle.replace("kernel-sru-cycle-", "")
    return cycle


def find_tag_matching(target_tag, tags):
    """Find tag matching the target prefix and abi number
    If there are duplicate abi numbers, the greatest upload is returned.
    If there are duplicate upload numbers, the greatest respin is returned.

    target_tag = Ubuntu-5.4.0-100.12

    Ubuntu-5.4.0-100.10
    Ubuntu-5.4.0-100.11
    Ubuntu-5.4.0-100.12
    Ubuntu-5.4.0-100.12+1
    Ubuntu-5.4.0-100.12+2 <- match
    """
    result = None
    best_match = None
    target_tag = UbuntuTag(target_tag)

    for tag in tags:
        this_tag = UbuntuTag(tag)
        # Protect against unfiltered tag lists
        if not target_tag.can_compare(this_tag):
            continue
        abi = int(this_tag.abi)
        if abi == target_tag.abi:
            if best_match is None or this_tag > best_match:
                best_match = this_tag
                result = best_match.raw_tag

    return result


class CycleRef:
    def __init__(self, cycle, tag, object_id):
        self.cycle = cycle
        self.tag = tag
        self.object_id = object_id

    def __str__(self) -> str:
        return f"{self.cycle} {self.tag} {self.object_id}"

    @staticmethod
    def make_ref(handle, cycle):
        """Returns the ref name that tracks this cycle
        Spin number will be removed from cycle if present
        """
        unfriendly = r"[^\d\w-]"
        handle = re.sub(unfriendly, "_", handle)
        cycle, _, _ = cycle.partition("-")
        ref = "refs/swm/{handle}/{cycle}".format(handle=handle, cycle=cycle)
        return ref

    @staticmethod
    def generate(handle, remote=None, dry_run=False):
        """Generate cycle refs for all trees in the specified Handle
        :param handle: Handle cranky handle
        :param dry_run: bool True for a dry run
        """
        #
        # Collect git handle and all tags for each tree
        tree_git_tags = {}
        for tree in handle.trees:
            #
            # For tree that contain multiple kernels we need to be
            # use a tag prefix to filter out unrelated kernels. All
            # packages in a HandleSet *should* have the same prefix
            # but we'll generate the prefix for each tree just in case.
            tag_prefix = make_tag_prefix(tree)
            cdebug(f"Using tag prefix {tag_prefix}")

            #
            # Ensure we have all the latest tags if a remote is specified
            this_git = Git(tree.directory)
            if remote:
                cdebug(f"Fetching tags from {remote}")
                this_git(
                    f"fetch {remote} 'refs/tags/{tag_prefix}:refs/tags/{tag_prefix}'"
                )

            #
            # Locate all tags from oldest to newest so latest respin is observed last
            tags = this_git(f"tag --list --sort=creatordate {tag_prefix}*", split="\n")
            tree_git_tags[tree] = this_git, tags

        #
        # Only main and lrm packages have a tracking-bug file which tracks
        # the cycle name. Use the main package as our source of truth for
        # the cycle name to associate with each tag.
        main_tree = handle.get_tree_by_package_type("main")
        main_git, main_tags = tree_git_tags[main_tree]

        for main_tag in main_tags:
            #
            # Read cycle from tracking-bug at this reference
            cycle = read_cycle(main_git, main_tag)
            if not cycle:
                cdebug(f"No tracking-bug containing a cycle name found at '{main_tag}'")
                continue
            cdebug(f"tag={main_tag}, cycle={cycle}")

            #
            # All packages use the same ref name for the same cycle
            ref = CycleRef.make_ref(handle.handle_name, cycle)

            #
            # Locate matching tag in main and all dependent packages
            for tree, (this_git, tags) in tree_git_tags.items():
                matching_tag = find_tag_matching(main_tag, tags)
                if not matching_tag:
                    cdebug(
                        f"No matching tag matching '{main_tag}' found in {tree.name} using filter prefix '{tag_prefix}'"
                    )
                    continue
                cdebug(f"Matching {main_tag} to {matching_tag} for {tree.name}")
                this_git(f"update-ref {ref} {matching_tag}", dry_run=dry_run)

    @staticmethod
    def get_list(handle_tree, descending=False, before=None, after=None):
        """Returns a list of CycleRefs found in the specified git repo
        :param handle_tree: a HandleTree (or any interface with directory and handle_name)
        :param descending: bool True to return newest->oldest
        :param before: str return all cycle refs before this cycle, exclusive
        :param after: str return all cycle refs after this cycle, exclusive
        :return: list(CycleRef)
        """
        repo_path = handle_tree.directory
        handle_name = handle_tree.handle_name
        unfriendly = r"[^\d\w-]"
        handle_name = re.sub(unfriendly, "_", handle_name)
        git = Git(repo_path)
        try:
            # HACK the format option doesn't escape correctly so omit ' and replace space with |
            raw = git(
                "for-each-ref --sort=creatordate --format=%(refname)|%(tag)|%(object) refs/swm/{}/*".format(handle_name),
                split="\n",
            )
        except CrankyException as ex:
            cerror(ex)
            return []

        #
        # Parsing is dependent on the --format options passed to git for-each-ref
        result = []
        for line in raw:
            ref, tag, object_id = line.split("|")
            _, _, cycle = ref.rpartition("/")
            result.append(CycleRef(cycle, tag, object_id))

        #
        # Filter out before and after which may be provided
        # together or separately
        if not before and not after:
            filtered = result
        else:
            filtered = list(result)
            if after:
                for i, r in enumerate(result):
                    if r.cycle == after:
                        filtered = result[i + 1 :]
                        break
            if before:
                for i, r in enumerate(filtered):
                    if r.cycle == before:
                        filtered = filtered[:i]
                        break

        if descending:
            filtered.reverse()

        return filtered

    @staticmethod
    def get_cycle_ref(handle_tree, cycle):
        """Returns CycleRef for the specified cycle name or None
        :param handle_tree: a HandleTree (or any interface with directory and handle_name)
        :param cycle: str name of cycle to locate
        :return: Optional[CycleRef]
        """
        result = None
        for cycle_ref in CycleRef.get_list(handle_tree):
            if cycle_ref.cycle == cycle:
                result = cycle_ref
                break
        return result
