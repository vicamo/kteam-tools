import contextlib
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "libs")))

from ktl.kernel_series import KernelSeries  # noqa: E402 Import not at top of file
from ktl.debian import Debian, DebianError  # noqa: E402 Import not at top of file
from ktl.git import GitError  # noqa: E402 Import not at top of file

from crl.config import Config  # noqa: E402 Import not at top of file


class HandleError(ValueError):
    pass


@contextlib.contextmanager
def change_directory(new_dir):
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(previous_dir)


class HandleHelper:
    @staticmethod
    def main_link(directory):
        git_dir = os.path.join(directory, ".git")
        if os.path.isfile(git_dir):
            with open(git_dir) as gfd:
                git_dir = gfd.readline()
            if git_dir[0:7] != "gitdir:":
                raise GitError("invalid .git format")
            git_dir = git_dir[7:].strip()
        return os.path.join(git_dir, "cranky-main")

    @classmethod
    def main_directory(cls, directory):
        main_dir = cls.main_link(directory)
        if os.path.exists(main_dir):
            return main_dir

        return directory


class HandleCore:
    def __init__(self, series=None, package=None, source=None, config=None, ks=None):
        self.series = series
        self.package = package
        self.source = source
        self.config = Config.load() if config is None else config
        self.ks = KernelSeries() if ks is None else ks
        self.name = "" if series is None or package is None else "{}:{}".format(series.codename, package.name)

        # TODO: Remove lookup of deprecated option package-path.base-path
        self.base_path = os.path.expanduser(
            self.config.lookup("base-path", self.config.lookup("package-path.base-path", ""))
        )  # noqa: E128

        if self.base_path == "":
            # Bail out if base-path is not set
            raise HandleError(
                "No 'base-path' option found in your cranky config file. "
                "Check the config example in kteam-tools/cranky/docs/"
                "snip-cranky.yaml for more information."
            )

    def lookup_config(self, key, default=None):
        """
        Lookup a config option and encode it if necessary
        """
        # TODO: Remove lookup of deprecated option package-path.base-path
        if key == "base-path" or key == "package-path.base-path":
            return self.base_path

        val = self.config.lookup(key, default=default)

        if val and key.endswith("-path"):
            # It's a path so we need to encode it and make it absolute
            val = val.format(series=self.series.codename)
            return os.path.join(self.base_path, val)

        return val

    def encode_directory(self, package):
        suffix = "" if package.type == "main" else "-" + package.type

        for key in ("{series}--{source}--{package}", "{series}--{source}", "{series}", "{type}", "default"):
            key = key.format(
                series=package.series.codename, source=package.source.name, package=package.name, type=package.type
            )

            package_path = self.config.lookup("package-path." + key)
            if package_path:
                break
        if package_path is None:
            package_path = "{series}/{package}"

        package_path = package_path.format(
            series=package.series.codename,
            source=package.source.name,
            package=package.name,
            type=package.type,
            type_suffix=suffix,
        )

        if package_path.startswith("/") or package_path.startswith("~"):
            print(
                "The 'package-path' option in your cranky config file is "
                "an absolute path rather than a path relative to "
                "'base-path'. Fix that to get rid of this warning.",
                file=sys.stderr,
            )
            print(
                "Check the config example in kteam-tools/cranky/docs/" "snip-cranky.yaml for more information.",
                file=sys.stderr,
            )
            return os.path.expanduser(package_path)

        return os.path.join(self.base_path, package_path)

    def set_minimal_suffixes(self, source):
        # Built a set of directory names for all of the packages in the source.
        paths = {}
        for package_entry in source.packages:
            path = self.encode_directory(package_entry)
            paths[package_entry.type if package_entry.type else "main"] = path

        # Remove the longest common prefix.
        prefix = os.path.commonprefix(list(paths.values()))
        prefix_len = len(prefix)
        for key in paths:
            paths[key] = paths[key][prefix_len:]

        # Build a list, longest suffix first.
        longest = sorted(paths.values(), key=lambda p: -len(p))  # noqa: E203

        return (longest, paths)

    def identify_directory(self, directory):
        try:
            with change_directory(directory):
                changelog = Debian.changelog()
        except (DebianError, GitError) as e:
            raise HandleError("{}: bad directory handle -- {}".format(directory, e))

        # Always use topmost entry for package name, even if unreleased
        package = changelog[0]["package"]

        if len(changelog) > 0 and changelog[0]["series"] == "UNRELEASED":
            changelog.pop(0)

        if len(changelog) == 0:
            raise HandleError("{}: Unable to identify directory handle".format(directory))

        return (changelog[0]["series"], package)

    @property
    def handle_name(self):
        """Returns handle name in series:package format"""
        if not self.source:
            return None
        return "{}:{}".format(self.series.codename, self.source.name)


class HandleTree(HandleCore):
    def __init__(self, series, package, source=None, directory=None, validate=True, config=None, ks=None):
        super().__init__(series=series, package=package, source=source, config=config, ks=ks)

        if directory is None:
            directory = self.encode_directory(package)

        directory = os.path.abspath(directory)
        if validate and os.path.exists(directory):
            (series_name, package_name) = self.identify_directory(directory)
            if series_name != series.codename:
                raise HandleError(f"{directory}: tree inconsistent, series {series_name} != {series.codename}")
            if package_name != package.name:
                raise HandleError(f"{directory}: tree inconsistent, package {package_name} != {package.name}")

        self.directory = directory

    @property
    def remote(self):
        cross_series = False
        cross_source = False
        cross_type = False
        primary_package = None
        for series in self.ks.series:
            for source in series.sources:
                for package in source.packages:
                    # We work against the remote name for the first package
                    # which references our repository.
                    if primary_package is None and self.package.repo and package.repo:
                        if self.package.repo.url == package.repo.url:
                            primary_package = package
                    if self.package == package:
                        continue
                    directory = os.path.abspath(self.encode_directory(package))
                    if os.path.realpath(self.directory) == os.path.realpath(directory):
                        if self.series != series:
                            cross_series = True
                        if self.package.source != source:
                            cross_source = True
                        if self.package.type != package.type:
                            cross_type = True

        if primary_package is None:
            primary_package = self.package
        bits = []
        if cross_series:
            bits.append(primary_package.series.codename)
        if cross_source and primary_package.source.name != "linux":
            bits.append(primary_package.source.name.replace("linux-", ""))
        if cross_type and primary_package.type != "main":
            bits.append(primary_package.type)

        remote = "-".join(bits)
        return remote if remote != "" else "origin"


class HandleSet(HandleCore):
    def __init__(self, handle, series, source, validate=True, trees=None, sample=None, ks=None, config=None):
        super().__init__(series=series, source=source, config=config, ks=ks)

        if trees:
            self.trees = trees

        elif sample is not None:
            self.trees = [sample]
            (remove, add) = self.set_minimal_suffixes(source)

            prefix = None
            directory = sample.directory
            for remove_entry in remove:
                if remove_entry == "":
                    prefix = directory
                    break
                elif directory.endswith(remove_entry):
                    prefix = directory[: -len(remove_entry)]
                    break

            if prefix is None:
                raise HandleError("{}: directory handle does not match set forms".format(handle))

            for package_entry in source.packages:
                if package_entry == sample.package:
                    continue
                # There is no sense in having a directory handle for something
                # which does not have repository.
                if package_entry.repo is None:
                    continue
                directory = prefix + add[package_entry.type if package_entry.type else "main"]
                self.trees.append(
                    HandleTree(
                        series,
                        package_entry,
                        source=source,
                        directory=directory,
                        validate=validate,
                        ks=self.ks,
                        config=self.config,
                    )
                )

        else:
            self.trees = []
            for package_entry in source.packages:
                # There is no sense in having a directory handle for something
                # which does not have repository.
                if package_entry.repo is None:
                    continue
                self.trees.append(
                    HandleTree(series, package_entry, source=source, validate=validate, ks=self.ks, config=self.config)
                )

    def get_tree_by_package_type(self, package_type):
        """Returns HandleTree for the request package or None if not found"""
        result = None
        for tree in self.trees:
            if tree.package.type == package_type:
                result = tree
                break
            # When package.type is None or an empty string that indicates 'main'
            # Support both options like the rest of the codebase.
            if not tree.package.type and package_type in (None, "", "main"):
                result = tree
                break
        return result


class Handle:
    def __init__(self, config=None):
        if config is None:
            config = Config.load()
        self.config = config

    def directory_identity(self, directory):
        """Return tuple of names for (cycle, series, package)
        The directory must contain or link to a tracking-bug file for this
        tree set. The cycle name may be None in the returned tuple.
        :raises: HandleError if directory cannot be identified
        """
        cycle_name = None
        try:
            with change_directory(directory):
                changelog = Debian.changelog()
            base = HandleHelper.main_directory(directory)
            with change_directory(base):
                debian_env = Debian.debian_env() or "debian"
                tracking_file = os.path.join(debian_env, "tracking-bug")
                if os.path.exists(tracking_file):
                    with open(tracking_file) as tfd:
                        try:
                            _, cycle_name = tfd.readline().strip().split()[0:2]
                        except ValueError as e:
                            raise HandleError("{}: expecting tracking id and cycle name -- {}".format(tracking_file, e))

        except (DebianError, GitError) as e:
            raise HandleError("{}: bad directory handle -- {}".format(directory, e))

        # Always use topmost entry for package name, even if unreleased
        package = changelog[0]["package"]

        if len(changelog) > 0 and changelog[0]["series"] == "UNRELEASED":
            changelog.pop(0)

        if len(changelog) == 0:
            raise HandleError("{}: Unable to identify directory handle".format(directory))

        if cycle_name is not None:
            cycle_name = cycle_name.rsplit("-", 1)[0]

        return cycle_name, changelog[0]["series"], package

    def lookup_package(self, package, validate=True):
        return HandleTree(package.series, package, validate=validate, ks=package._ks, config=self.config)

    def decode_handle(self, handle):
        # A directory passed as a handle.
        if os.path.exists(handle):
            cycle_name, series_name, package_name = self.directory_identity(handle)
            if cycle_name and cycle_name[0] in ("d",):
                cycle_name = None
            directory = handle

        else:
            bits = handle.split(":")
            if len(bits) != 2:
                raise HandleError("{}: handle format unknown".format(handle))
            series_name, package_name = bits
            cycle_name = None
            directory = None

        return cycle_name, series_name, package_name, directory

    def lookup_tree(self, handle, cycle=None, validate=True, ks=None):
        package = None
        source = None

        cycle_name, series_name, package_name, directory = self.decode_handle(handle)
        if cycle is None:
            cycle = cycle_name

        if ks is None:
            ks = KernelSeries.for_cycle(cycle)
            if ks is None:
                raise HandleError("{}: cycle {} configuration not found".format(handle, cycle))
        series = ks.lookup_series(codename=series_name)
        if series is None:
            series = ks.lookup_series(series=series_name)
        if series is None:
            raise HandleError(
                "{}: handle directory contains series {} which is not known in cycle {}".format(
                    handle, series_name, cycle
                )
            )

        for source_entry in series.sources:
            for package_entry in source_entry.packages:
                if package_entry.name == package_name:
                    source = source_entry
                    package = package_entry
                    break
            if package:
                break

        if package is None:
            raise HandleError(
                "{}: handle directory contains package {} which is not known in cycle {}".format(
                    handle, package_name, cycle
                )
            )

        return HandleTree(
            series, package, source=source, directory=directory, validate=validate, ks=ks, config=self.config
        )

    def lookup_set(self, handle, cycle=None, validate=True, ks=None):
        # A directory passed as a handle.
        if os.path.exists(handle):
            tree = self.lookup_tree(handle, cycle=cycle, validate=validate, ks=ks)
            return HandleSet(
                handle, tree.series, tree.package.source, validate=validate, sample=tree, ks=ks, config=self.config
            )

        cycle_name, series_name, source_name, directory = self.decode_handle(handle)

        cycle = cycle if cycle is not None else cycle_name

        ks = ks if ks is not None else KernelSeries.for_cycle(cycle)
        if ks is None:
            raise HandleError("{}: cycle {} configuration not found".format(handle, cycle))

        series = ks.lookup_series(codename=series_name)
        series = series if series is not None else ks.lookup_series(series=series_name)
        if series is None:
            raise HandleError("{}: handle contains series not known in cycle {}".format(series_name, cycle))

        source = series.lookup_source(source_name)
        if source is None:
            raise HandleError("{}: handle contains source not known in cycle {}".format(source_name, cycle))

        return HandleSet(handle, series, source, validate=validate, ks=ks, config=self.config)
