#!/usr/bin/env python
#
from __future__                         import absolute_import

# Note: It would be nice to not tie the debian class to the git class but
#       be able to handle projects that are under bzr as well. But for
#       now, we need to be practical for now.

import subprocess
from debian.changelog                   import Changelog, get_maintainer
from os                                 import path, listdir, system
from re                                 import compile, findall, finditer
from sys                                import stdout
from glob                               import glob

from ktl.git                            import Git, GitError
from ktl.utils                          import debug, run_command
from ktl.kernel_series                  import KernelSeries


# DebianError
#
class DebianError(Exception):
    # __init__
    #
    def __init__(self, error):
        self.msg = error

# Note: Think about cacheing the decoded, changelog dictionary.
#

class Debian:
    verbose = False
    debug = False
    version_line_rc = compile("^(linux[-\S]*) \(([0-9]+\.[0-9]+\.[0-9]+[-\.][0-9]+\.[0-9]+[~\S]*)\) (\S+); urgency=\S+$")
    version_rc      = compile("^([0-9]+\.[0-9]+\.[0-9]+)[-\.]([0-9]+)\.([0-9]+)([~\S]*)$")

    package_rc = compile("^(linux[-\S])*.*$")
    ver_rc     = compile("^linux[-\S]* \(([0-9]+\.[0-9]+\.[0-9]+[-\.][0-9]+\.[0-9]+[~a-z0-9]*)\).*$")
    bug_rc = compile("LP:\s*#[0-9]+(?:\s*,\s*#[0-9]+)*")
    bug_nr_rc = compile("#([0-9]+)")

    parent_bug_section_rc = compile("^\s*\[ Ubuntu: .*\]")
    endsection_line_rc = compile("^ -- ")

    @classmethod
    def fdr(cls, cmd, dry_run=False):
        """
        Execute fakeroot debian/rules cmd.
        Print its output when it fails, and returns its exit status.
        The dry_run option may be used to just print the command that would be run.
        """
        (status, output) = run_command('fakeroot debian/rules %s' % (cmd), dry_run=dry_run)
        if status:
            print("\n".join(output))
        return status

    @classmethod
    def dch(cls, release):
        fname = "%s/changelog" % (cls.debian_env())
        changelog = Changelog(open(fname))
        # Date and time library compatibility between python 2 and 3
        # is a real pain. Use the good and old date command instead:
        dt = subprocess.check_output(["date", "-R"],
                                     env={"LC_ALL": "C"}).strip()
        (maintainer, email) = get_maintainer()
        changelog.set_distributions(release)
        changelog.set_author("%s <%s>" % (maintainer, email))
        changelog.set_date(dt)
        changelog.write_to_open_file(open(fname, "w"))

    # debian_env
    #
    @classmethod
    def debian_env(cls):
        # Find the correct debian directory for this branch of this repository.
        #
        current_branch = Git.current_branch()
        debenv = None

        # If we have a debian/debian.env then open and extract the DEBIAN=...
        # location.
        debug("Checking debian/debian.env", cls.debug)
        try:
            debian_env = Git.show("debian/debian.env", branch=current_branch)
            for line in debian_env:
                if 'DEBIAN=' in line:
                    (var, val) = line.split('=', 1)
                    val = val.rstrip()

                    if var == 'DEBIAN':
                        debenv = val
                        break
            debug("SUCCEEDED\n", cls.debug, False)
        except GitError:
            pass
        return debenv

    # debian_directories
    #
    @classmethod
    def debian_directories(cls):
        debdirs = []
        debenv = None
        debenv = cls.debian_env()
        if debenv:
            debdirs.append(debenv)
            debug("SUCCEEDED\n", cls.debug, False)
        else:
            debug("FAILED\n", cls.debug, False)
            debdirs += ['debian', 'meta-source/debian']

        return debdirs

    # master_changelog
    #
    @classmethod
    def master_changelog(cls):
        '''
        The 'changelog' method returns the changelog related to the current branch. This
        method always returns the changelog from the debian.master directory.
        '''
        fid = 'debian.master/changelog'
        if path.exists(fid):
            with open(fid, 'r') as f:
                changelog_contents = f.read()

            retval = cls.changelog_as_list(changelog_contents.split('\n'))
        else:
            raise DebianError('Failed to find the master changelog.')
        return retval

    # raw_changelog
    #
    @classmethod
    def raw_changelog(cls, local=False):

        # Find the correct changelog for this branch of this repository.
        #
        current_branch = Git.current_branch()

        # Check each possible directory for a changelog
        debian_dirs = cls.debian_directories()
        for debdir in debian_dirs:
            chglog = debdir + '/changelog'
            debug("Trying '%s': " % chglog, cls.debug)
            try:
                if local:
                    changelog_contents = open(chglog, 'r').read().split('\n')
                else:
                    changelog_contents = Git.show(chglog, branch=current_branch)
                return changelog_contents, chglog
            except (GitError, OSError, IOError):
                debug("FAILED\n", cls.debug, False)

        # Not there anywhere, barf
        raise DebianError('Failed to find the changelog.')

    # changelog
    #
    @classmethod
    def changelog(cls, local=False):
        changelog_contents, changelog_path = cls.raw_changelog(local)
        return cls.changelog_as_list(changelog_contents)

    # changelog_as_list
    #
    @classmethod
    def changelog_as_list(cls, changelog_contents):
        retval = []

        # The first line of the changelog should always be a version line.
        #
        m = cls.version_line_rc.match(changelog_contents[0])
        if m is None:
            if cls.debug:
                m = cls.package_rc.match(changelog_contents[0])
                if m is None:
                    debug('The package does not appear to be in a recognized format.\n', cls.debug)

                m = cls.ver_rc.match(changelog_contents[0])
                if m is None:
                    debug('The version does not appear to be in a recognized format.\n', cls.debug)

            raise DebianError("The first line in the changelog is not a version line.")

        content = []
        own_content = []
        bugs = []
        own_bugs = []
        parsing_own_bugs = True

        for line in changelog_contents:
            m = cls.version_line_rc.match(line)
            if m is not None:
                version = ""
                release = ""
                pocket  = ""
                package = m.group(1)
                version = m.group(2)
                rp = m.group(3)
                if '-' in rp:
                    release, pocket = rp.split('-')
                else:
                    release = rp

                section = {}
                section['version'] = version
                section['release'] = release
                section['series']  = release
                section['pocket']  = pocket
                section['package'] = package

                m = cls.version_rc.match(version)
                if m is not None:
                    section['linux-version'] = m.group(1)
                    section['ABI']           = m.group(2)
                    section['upload-number'] = m.group(3)
                else:
                    debug('The version (%s) failed to match the regular expression.\n' % version, cls.debug)

                content = []
                own_content = []
                bugs = []
                own_bugs = []
                parsing_own_bugs = True
                continue

            content.append(line)
            if parsing_own_bugs:
                own_content.append(line)

            if cls.parent_bug_section_rc.match(line):
                parsing_own_bugs = False

            # find bug numbers and append them to the list
            for bug_line_match in finditer(cls.bug_rc, line):
                bug_matches = findall(cls.bug_nr_rc, bug_line_match.group(0))
                bugs.extend(bug_matches)
                if parsing_own_bugs:
                    own_bugs.extend(bug_matches)

            m = cls.endsection_line_rc.match(line)
            if m is not None:
                section['content'] = content
                section['own-content'] = own_content
                section['bugs'] = set(bugs)
                section['own-bugs'] = set(own_bugs)
                retval.append(section)

        return retval

    # abi
    #
    @classmethod
    def abi(cls):

        # Check each possible directory for an abi file
        debian_dirs = cls.debian_directories()
        retvals = []
        for debdir in debian_dirs:
            abidir = debdir + '/abi'
            debug("Trying '%s': \n" % abidir, cls.debug)
            if path.isdir(abidir):
                debug("  '%s' is a directory\n" % abidir, cls.debug)
                contents = listdir(abidir)
                for item in contents:
                    debug("  Contains: '%s'\n" % item, cls.debug)
                    if path.isdir(abidir + '/' + item):
                        retvals.append(item)
                return retvals

        # Not there anywhere, barf
        raise DebianError('Failed to find the abi files.')

    # abi_arch
    #
    @classmethod
    def abi_arch(cls):

        # Return contents of all arch directories within an ABI
        debian_dirs = cls.debian_directories()
        retvals = {}
        empty = []
        abiarch = []
        for debdir in debian_dirs:
            abidir = debdir + '/abi'
            debug("Trying '%s': \n" % abidir, cls.debug)
            if path.isdir(abidir):
                debug("  '%s' is a directory\n" % abidir, cls.debug)
                contents = listdir(abidir)
                for item in contents:
                    debug("  Contains: '%s'\n" % item, cls.debug)
                    if path.isdir(abidir + '/' + item):
                        abisubdirs = listdir(abidir + '/' + item)
                        for subdir in abisubdirs:
                            fullpath = path.join(abidir, item, subdir)
                            if path.isdir(fullpath):
                                abiarch.append(fullpath)
                for archdir in abiarch:
                    arch = path.basename(archdir)
                    contents = listdir(archdir)
                    retvals[arch] = contents
                    # Now, check each ignore file to make sure it's not empty,
                    # as empty files don't work to trigger ABI ignore in the PPA
                    # but will in a test build !!!!!
                    for fname in contents:
                        if 'ignore' in fname:
                            fpath = path.join(archdir, fname)
                            fsize = path.getsize(fpath)
                            if fsize == 0:
                                debug("  Found empty ABI file: '%s'\n" % fpath, cls.debug)
                                empty.append(fpath)
                return retvals, empty

        # Not there anywhere, barf
        raise DebianError('Failed to find the abi files.')

    # get_source_from_kernel_series
    #
    @classmethod
    def get_source_from_kernel_series(cls):
        """
        Return a ktl.kernel_series.KernelSourceEntry object representing
        the kernel on the current directory.  The changelog
        information is used for the series and source package lookup.
        """
        # Get the changelog
        changelog = cls.changelog()
        if not changelog and len(changelog) < 1:
            raise DebianError("No changelog entries.")
        # Find the first valid entry
        series = package = None
        for centry in changelog:
            if centry['series'] != 'UNRELEASED':
                series = centry['series']
                package = centry['package']
                break
        # Check if the entry is valid
        if not series:
            raise DebianError("Can't find a valid series in the changelog.")
        if not package:
            raise DebianError("Can't find a valid package name in the changelog.")
        # Get the kernel series info
        info_series = KernelSeries().lookup_series(codename=series)
        if not info_series:
            raise DebianError("Unknown series: %s. Please check the " +
                              "info/kernel-series.yaml file." %
                              series)
        info_package = info_series.lookup_source(package)
        if not info_package:
            raise DebianError("Unknown package: %s. Please check the " +
                              "info/kernel-series.yaml file." %
                              package)
        return info_package

    @classmethod
    def update_from_master(cls, dry_run=False):
        """
        Call the debian.<branch>/etc/update-from-*master script.
        Print its output when it fails, and returns its exit status.
        The dry_run option may be used to just print the command that would be run.
        """
        debiandir = Debian.debian_env()
        scripts = glob(debiandir + "/etc/update-from-*master")
        for script in scripts:
            (status, output) = run_command(script, dry_run=dry_run)
            if status:
                print("\n".join(output))
                return status
        return 0

    # is_backport
    #
    @classmethod
    def is_backport(cls):
        # Check each possible directory for an update script
        debian_dirs = cls.debian_directories()
        for debdir in debian_dirs:
            flag = debdir + '/backport'
            if path.exists(flag):
                # It is a backport kernel
                return True
        # Not there anywhere, it's a regular kernel
        return False

# vi:set ts=4 sw=4 expandtab:
