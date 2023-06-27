#!/usr/bin/env python3
import os
import unittest
from subprocess import getstatusoutput
from typing import List, Tuple

from testfixtures import TempDirectory

from crl.cycle_ref import CycleRef, Git
from crl.exceptions import CrankyException
from crl.handle import Config, Handle, KernelSeries, change_directory


class CrankyContext:
    """Context helps keep track of all the paths cranky needs to know about"""

    def __init__(
        self,
        handle_name: str,
        package_name: str,
        tracking_bug_path: str,
        handle_config: Config,
    ):
        self.handle_name = handle_name
        self.tracking_bug_path = tracking_bug_path
        self.handle_config = handle_config
        ks = KernelSeries()
        self.handle = Handle(config=handle_config, ks=ks).lookup_set(
            handle_name, validate=False
        )
        self.repo = next(
            iter([t for t in self.handle.trees if t.package.name == package_name]), None
        )
        if not self.repo:
            raise CrankyException("Main repo not found")
        self.git = Git(repo_directory=self.repo.directory)


class BaseCrankyTest(unittest.TestCase):
    def __init__(self, methodName: str = ...) -> None:
        super().__init__(methodName)
        self.context = None

    def setup_run_cmd(self, path: str, cmd: str):
        """Run shell command and assert that return code is 0"""
        with change_directory(path):
            (status, output) = getstatusoutput(cmd)
            if status != 0:
                print("CMD FAILED:", output)
            self.assertEqual(status, 0)

    def setup_source(self, d: TempDirectory, series: str, package: str, branch: str):
        """Setup a minimal repo that can be used with a KernelSeries"""

        #
        # Initialize empty repo using specified branch name
        git_path = os.path.join(d.path, series, package)
        d.makedir(git_path)
        self.setup_run_cmd(git_path, f"git init --initial-branch={branch}")

        #
        # Create $debian structure
        debian = "debian.master"
        data_env = f"DEBIAN={debian}\n"
        d.makedir(os.path.join(git_path, "debian"))
        d.write(
            os.path.join(git_path, "debian", "debian.env"), data_env.encode("utf-8")
        )
        self.setup_run_cmd(git_path, "git add debian/debian.env")

        #
        # Create changelog
        data_changelog = (
            f"{package} (4.15.0-1.2) {series}; urgency=medium\n  * foo\n -- ME\n"
        )
        d.write(
            os.path.join(git_path, debian, "changelog"), data_changelog.encode("utf-8")
        )
        self.setup_run_cmd(git_path, f"git add {debian}/changelog")

        #
        # Create tracking-bug
        tracking_bug_path = None
        if package != "linux-meta":
            tracking_bug_path = os.path.join(
                d.path, os.path.join(git_path, debian, "tracking-bug")
            )
            d.write(tracking_bug_path, "".encode("utf-8"))
            self.setup_run_cmd(git_path, f"git add {debian}/tracking-bug")

        #
        # Create file that represents code changes
        d.write(os.path.join(git_path, "test.txt"), "0".encode("utf-8"))
        self.setup_run_cmd(git_path, "git add test.txt")
        self.setup_run_cmd(git_path, 'git commit -a -m "Initial"')

        #
        # Generate a context using our temporary directory
        config_yaml = f"base-path:                      '{d.path}'"
        handle_config = Config(data=config_yaml)
        self.context = CrankyContext(
            f"{series}:linux",
            package,
            tracking_bug_path,
            handle_config=handle_config,
        )
        return self.context

    def add_tracking_bugs(self, context, bug_contents, create_tags=True):
        """Add commits that emulate tracking-bug changes"""
        dummy_file = os.path.join(context.repo.directory, "test.txt")
        tracking_bug_file = context.tracking_bug_path

        tag_counter = 1
        for tb, cycle, dummy_commits in bug_contents:

            #
            # Emulate commits in between tags
            for _ in range(dummy_commits):
                with open(dummy_file, "r+") as f:
                    counter = int(f.read().strip())
                    f.seek(0)
                    f.write(str(counter + 1))
                context.git("add test.txt")
                context.git("commit -m 'dummy changes'")

            #
            # Update tracking bug in a commit separate from the closing commit
            with open(tracking_bug_file, "w") as f:
                f.write(f"{tb} {cycle}")
            context.git(f"add {tracking_bug_file}")
            context.git("commit -m 'update tracking bug'")

            #
            # Emulate closing commit
            context.git("commit --allow-empty -m 'release foo'")
            if create_tags:
                context.git(f"tag Ubuntu-4.15.0-{tag_counter}.{tag_counter}")
            tag_counter += 1

    def setup_package_set(
        self,
        d: TempDirectory,
        series: str,
        bug_contents: List[Tuple[str, str, int]] = None,
        create_tags: bool = False,
    ):
        """Setup all packages for a series

        The context of the main package is returned
        :param series: Series name, e.g. focal, bionic
        :param bug_contents: Option list of (LP Bug id, cycle name, count of commits between each bug) to inject
        :param create_tags: Generate git tags for each bug commit if bug_contents is specified
        """

        main_context = None
        packages = ("linux", "linux-meta", "linux-restricted-modules", "linux-signed")
        branches = ("master-next", "master", "master", "master")
        for package, branch in zip(packages, branches):
            context = self.setup_source(d, series, package, branch)

            if bug_contents and context.tracking_bug_path:
                self.add_tracking_bugs(context, bug_contents, create_tags)

            if not main_context:
                main_context = context
        return main_context

    def context_git_is_clean(self):
        self.context.git("status --porcelain")


class TestCycleRef(BaseCrankyTest):
    def test_cycle_ref_list_none(self):
        """A git repo with no cycle history in $debian/tracking-bug should be handled"""
        with TempDirectory() as d:
            # Setup
            context = self.setup_package_set(d, "bionic")

            # Execute
            actual = CycleRef.get_list(context.repo)

            # Assert
            self.assertEqual(len(actual), 0, "No cycles should have been returned")
            self.context_git_is_clean()

    def test_cycle_ref_list_no_tags(self):
        """A git repo with some cycle history in $debian/tracking-bug but no tags should be handled"""
        with TempDirectory() as d:
            # Setup
            bug_contents = (
                # LP bug       Cycle          Commits before tb is updated
                ("111111111", "2022.01.01-1", 3),
                ("111111111", "2022.02.01-1", 6),
                ("111111111", "2022.03.01-1", 9),
            )
            context = self.setup_package_set(
                d, "bionic", bug_contents, create_tags=False
            )
            CycleRef.generate(context.handle)

            # Execute
            actual = CycleRef.get_list(context.repo)

            # Assert
            self.assertEqual(len(actual), 0, "No cycles should have been returned")
            self.context_git_is_clean()

    def test_cycle_ref_list_some(self):
        """A git repo with some cycle history in $debian/tracking-bug should be handled"""
        with TempDirectory() as d:
            # Setup
            bug_contents = (
                # LP bug       Cycle          Commits before tb is updated
                ("111111111", "2022.01.01-1", 3),
                ("111111111", "2022.02.01-1", 6),
                ("111111111", "2022.03.01-1", 9),
            )
            context = self.setup_package_set(
                d, "bionic", bug_contents, create_tags=True
            )
            CycleRef.generate(context.handle)

            # Execute
            actual = CycleRef.get_list(context.repo)

            # Assert
            self.assertEqual(len(actual), 3)
            self.context_git_is_clean()

    def test_cycle_ref_list_some_descending(self):
        """Descending order should work"""
        with TempDirectory() as d:
            # Setup
            bug_contents = (
                # LP bug       Cycle          Commits before tb is updated
                ("111111111", "2022.01.01-1", 3),
                ("111111111", "2022.02.01-1", 6),
                ("111111111", "2022.03.01-1", 9),
            )
            context = self.setup_package_set(
                d, "bionic", bug_contents, create_tags=True
            )
            CycleRef.generate(context.handle)

            # Execute
            actual = CycleRef.get_list(context.repo, descending=True)

            # Assert
            self.assertEqual(len(actual), len(bug_contents))
            # actual is reversed but let's reverse the expected instead
            # so we can extract the cycle for easier comparison
            expected = (b[1] for b in reversed(bug_contents))
            for i, expect in enumerate(expected):
                expect, _, _ = expect.partition("-")
                self.assertEqual(actual[i].cycle, expect)
            self.context_git_is_clean()

    def test_cycle_ref_list_some_before_after(self):
        """Descending order with before and after should work"""
        with TempDirectory() as d:
            # Setup
            bug_contents = (
                # LP bug       Cycle          Commits before tb is updated
                ("111111111", "2022.01.01-1", 3),
                ("111111111", "2022.02.01-1", 6),
                ("111111111", "2022.03.01-1", 9),
            )
            context = self.setup_package_set(
                d, "bionic", bug_contents, create_tags=True
            )
            CycleRef.generate(context.handle)

            # Execute
            actual = CycleRef.get_list(
                context.repo,
                descending=True,
                before="2022.03.01",
                after="2022.01.01",
            )

            # Assert
            self.assertEqual(len(actual), 1)
            expect, _, _ = bug_contents[1][1].partition("-")
            self.assertEqual(actual[0].cycle, expect)
            self.context_git_is_clean()
