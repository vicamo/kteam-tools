import sys
import os

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "py3")))

from os import unlink
from datetime import datetime
import json
import re
import apt_pkg
import urllib
import atexit
import shutil
import time
from lpltk.LaunchpadService import LaunchpadService
from ktl.kernel_series import KernelSeries
from lib.archive import Archive
from logging import basicConfig, DEBUG
from ktl.log import cdebug, cerror


# BugEntry
#
class BugEntry:

    def __init__(self, lp_bug):
        self.title = lp_bug.title
        self.tags = list(lp_bug.tags)
        self.owner = lp_bug.owner.display_name


# SruReport
#
class SruReport:
    # __init__
    #
    def __init__(self, cfg={}, lp_service=None, lp=None):
        self.cfg = cfg

        if lp_service is not None:
            self.lp = lp_service.launchpad
        else:
            self.lp = lp

        self.archive_root = "http://archive.ubuntu.com/ubuntu"
        self.ports_root = "http://ports.ubuntu.com/ubuntu-ports"

        self.components = ["main", "universe"]

        kernel_series = KernelSeries()
        self.all_series = [
            series.codename
            for series in sorted(kernel_series.series, key=KernelSeries.key_series_name)
            if (series.supported or series.development) and not series.opening and not series.old_releases
        ]
        self.requested_series = []

        self.tempdir = None

        if "debug" in self.cfg:
            log_format = "%(levelname)s - %(message)s"
            basicConfig(level=DEBUG, format=log_format)

        self._changelog_cache = {}
        self._changelog_cache_out = {}
        if self.cfg.get("cache") is not None and os.path.exists(self.cfg["cache"]):
            with open(self.cfg["cache"]) as cfd:
                self._changelog_cache = json.load(cfd)

    def _dbg(self, system, msg):
        if "debug" in self.cfg:
            if system in self.cfg["debug"]:
                cdebug("SruReport: %s" % (msg))

    # _initialize
    #
    def _initialize(self):
        self._dbg("core", "_initialize: enter")
        apt_pkg.init_system()
        # note that only 'LP: #1234' is official, but sometimes people get it wrong
        self.changelog_bug_pattern = re.compile(r'(?:lp(?::| |#)+|href="/bugs/)([0-9]+)')
        self.published_date_pattern = re.compile(r"Published.*\n.*on ([-0-9]+)")

        if self.lp is None:
            self.cfg["launchpad_client_name"] = "kernel-team-sru-report"
            self.lp = LaunchpadService(self.cfg).launchpad

        if self.cfg["archive-versions"]:
            ar = Archive()
            self.ppa = ar.ppa_versions(force=False)
            self.dversions = ar.distro_versions(force=False)

        if len(self.cfg["series"]) > 0:
            self.requested_series = self.cfg["series"]
        else:
            self.requested_series = self.all_series

        self._dbg("core", "_initialize: leave")
        return

    # _decompress_open
    #
    def _decompress_open(self, tagfile):
        resp = {"content-type": ""}
        if tagfile.startswith("http:") or tagfile.startswith("ftp:"):
            url = tagfile
            tagfile, resp = urllib.request.urlretrieve(url)
            atexit.register(unlink, tagfile)

        if tagfile.endswith(".gz"):
            if resp["content-type"].startswith("text"):
                self._dbg("core", "        tagfile not found\n")
                return
            import gzip
            import tempfile

            if not self.tempdir:
                self.tempdir = tempfile.mkdtemp(prefix="suite-diff")
                atexit.register(shutil.rmtree, self.tempdir, True)
            decompressed = tempfile.mktemp(dir=self.tempdir)
            fin = gzip.GzipFile(filename=tagfile)
            fout = open(decompressed, "wb")
            fout.write(fin.read())
            fout.close()
            atexit.register(unlink, decompressed)
            return open(decompressed, "r")
        else:
            return open(tagfile, "r")

    # _tagfile_to_dict
    #
    def _tagfile_to_dict(self, tagfile):
        self._dbg("core", "    tagfile_to_dict Enter")
        self._dbg("core", "        tagfile: '%s'" % (tagfile))
        rls = {}
        p = apt_pkg.TagFile(self._decompress_open(tagfile))
        while p.step() == 1:
            rls[p.section["Package"]] = p.section["Version"]
        self._dbg("core", "    tagfile_to_dict Leave")
        return rls

    # _get_changelog_info
    #
    def _get_changelog_info_direct(self, url):
        """Parse LP per-version/per-release page URL and return tuple (date, bugs)
        with a publishing date (time record) and a bug list string."""

        # enable this for quick testing
        # return (time.localtime(), '')

        chlog = urllib.request.urlopen(url).read()
        chlog = chlog.decode("utf-8")

        m = self.published_date_pattern.search(chlog)
        if m:
            date = time.strptime(m.group(1), "%Y-%m-%d")
        else:
            # less than a day ago (Soyuz uses "... hours ago")
            date = time.localtime()

        # cut out the actual changelog
        chlog = chlog[chlog.find("<pre ") : chlog.find("</pre>")]

        bugnums = []
        for m in self.changelog_bug_pattern.finditer(chlog):
            bug = m.group(1)
            if bug.startswith("#"):
                bug = bug[1:]
            if bug not in bugnums:
                bugnums.append(bug)

        return (date, bugnums)

    def _get_changelog_info(self, url):
        if url not in self._changelog_cache:
            self._dbg("cache", "_get_changelog_info({}) (MISS)".format(url))
            self._changelog_cache[url] = self._get_changelog_info_direct(url)
        else:
            self._dbg("cache", "_get_changelog_info({}) (HIT)".format(url))
        date, bugs = self._changelog_cache[url]
        if isinstance(date, list):
            date = time.struct_time(date)
        self._changelog_cache_out[url] = (date, bugs)
        return date, bugs

    def cache_save(self):
        if "cache" in self.cfg:
            with open(self.cfg["cache"] + ".new", "w") as cfd:
                json.dump(self._changelog_cache_out, cfd, sort_keys=True, indent=4)
                os.rename(self.cfg["cache"] + ".new", self.cfg["cache"])

    _bug_cache = {}

    def bug_data(self, bug):
        if bug not in self._bug_cache:
            self._dbg("cache", "bug_data({}) (MISS)".format(bug))
            self._bug_cache[bug] = BugEntry(self.lp.bugs[bug])
        else:
            self._dbg("cache", "bug_data({}) (HIT)".format(bug))
        return self._bug_cache[bug]

    # generate
    #
    def generate(self):
        results = {}
        pending = {}  # suite -> package -> (release_ver, proposed_ver, update_ver)
        cleanup = {}  # suite -> package
        try:
            self._initialize()

            results["releases"] = {}
            if self.cfg["archive-versions"]:
                # -----------------------------------------------------------------------------
                # Go through the archive data and find all the relevant series and packages
                # and thier versions. Seed the results dictionary with this information.
                #
                for series in self.requested_series:
                    if series not in results["releases"]:
                        results["releases"][series] = {}

                    # Add any versions from the ppa
                    #
                    for ppa_entry in self.ppa:
                        if self.ppa[ppa_entry]["series"] != series:
                            continue

                        sp = self.ppa[ppa_entry]["source_package_name"]
                        pocket = "ppa"
                        spv = self.ppa[ppa_entry]["source_package_version"]
                        if sp not in results["releases"][series]:
                            results["releases"][series][sp] = {}
                        results["releases"][series][sp][pocket] = spv

                    # Add all the versions from the archive
                    #
                    for archive_entry in self.dversions:
                        if self.dversions[archive_entry]["series"] != series:
                            continue

                        sp = self.dversions[archive_entry]["source_package_name"]
                        pocket = self.dversions[archive_entry]["pocket"]
                        spv = self.dversions[archive_entry]["source_package_version"]
                        if sp not in results["releases"][series]:
                            results["releases"][series][sp] = {}
                        results["releases"][series][sp][pocket] = spv

            # -----------------------------------------------------------------------------
            # Now go through all the packages that are currently in proposed and pull out
            # the bug (and any other) information.
            #
            for rls in self.requested_series:
                self._dbg("core", "Series: '%s'" % (rls))
                self._dbg("core", "    Coponents: '%s'" % (self.components))
                for component in self.components:
                    self._dbg("core", "    Component: '%s'" % (component))

                    try:
                        release = self._tagfile_to_dict(
                            "%s/dists/%s/%s/source/Sources.gz" % (self.archive_root, rls, component)
                        )
                        proposed = self._tagfile_to_dict(
                            "%s/dists/%s-proposed/%s/source/Sources.gz" % (self.archive_root, rls, component)
                        )
                        updates = self._tagfile_to_dict(
                            "%s/dists/%s-updates/%s/source/Sources.gz" % (self.archive_root, rls, component)
                        )
                        security = self._tagfile_to_dict(
                            "%s/dists/%s-security/%s/source/Sources.gz" % (self.archive_root, rls, component)
                        )
                    except:
                        cerror("    Failed to run tagfile_to_dict, skipped")
                        raise

                    for package in sorted(proposed.keys()):
                        if "linux" != package[:5]:
                            continue
                        self._dbg("core", "        Proposed Package: '%s'" % (package))
                        update_ver = updates.get(package, "")
                        if apt_pkg.version_compare(proposed[package], update_ver) > 0:
                            security_ver = security.get(package, "")
                            pending.setdefault(rls, {})[package] = (
                                release.get(package, ""),
                                proposed[package],
                                update_ver,
                                security_ver,
                            )

                            # security_ver = security.get(package, '')
                            # if apt_pkg.version_compare(proposed[package], security_ver) < 0:
                            #    security_superseded.setdefault(rls, {})[package] = (proposed[package], security_ver)
                        else:
                            cleanup.setdefault(rls, []).append(package)

            # Pending Ubuntu Stable Release Updates
            #
            for rls in self.requested_series:
                if rls not in results["releases"]:
                    results["releases"][rls] = {}
                if rls in pending:
                    if "pkgs" in self.cfg:
                        pkgs = self.cfg["pkgs"]
                    else:
                        pkgs = pending[rls].keys()

                    for pkg in pkgs:
                        lpurl = "https://launchpad.net/ubuntu/%s/+source/%s/" % (rls, pkg)
                        (vrel, vprop, vupd, vsec) = pending[rls][pkg]

                        (date, bugs) = self._get_changelog_info(lpurl + vprop)
                        age = int((time.time() - time.mktime(date)) / 86400)

                        if pkg not in results["releases"][rls]:
                            results["releases"][rls][pkg] = {}

                        if "Release" not in results["releases"][rls][pkg]:
                            results["releases"][rls][pkg]["Release"] = vrel
                        if "Proposed" not in results["releases"][rls][pkg]:
                            results["releases"][rls][pkg]["Proposed"] = vprop
                        if "Updates" not in results["releases"][rls][pkg]:
                            results["releases"][rls][pkg]["Updates"] = vupd
                        if "Security" not in results["releases"][rls][pkg]:
                            results["releases"][rls][pkg]["Security"] = vupd
                        results["releases"][rls][pkg]["url"] = lpurl
                        results["releases"][rls][pkg]["age"] = age
                        results["releases"][rls][pkg]["bugs"] = {}

                        self._dbg("cache", "rls={} package={}".format(rls, pkg))
                        for bug in bugs:
                            self._dbg("core", "        bug: '%s'" % (bug))
                            results["releases"][rls][pkg]["bugs"][bug] = {}
                            spammed_v1 = "kernel-spammed-{}-{}".format(rls, pkg)
                            spammed_v2 = spammed_v1 + "-v2"
                            try:
                                lp_bug = self.bug_data(bug)
                                if spammed_v1 in lp_bug.tags:
                                    key = rls
                                else:
                                    key = rls + "-" + pkg

                                state = "missing"
                                if "kernel-tracking-bug" in lp_bug.tags:
                                    state = "release-tracker"
                                elif "kernel-release-tracker" in lp_bug.tags:
                                    state = "release-tracker"
                                elif "kernel-release-tracking-bug" in lp_bug.tags:
                                    state = "release-tracker"
                                elif "kernel-cve-tracker" in lp_bug.tags:
                                    state = "cve-tracker"
                                elif "kernel-cve-tracking-bug" in lp_bug.tags:
                                    state = "cve-tracker"
                                elif "kernel-stable-tracking-bug" in lp_bug.tags:
                                    state = "stable-tracker"
                                elif "kernel-packaging-tracking-bug" in lp_bug.tags:
                                    state = "packaging-tracker"

                                # By making these checks separately and after the previous ones, we
                                # can add the correct state for tracking bugs.
                                #
                                if "verification-failed-%s" % key in lp_bug.tags:
                                    state = "failed"
                                elif "verification-reverted-%s" % key in lp_bug.tags:
                                    state = "reverted"
                                elif "verification-done-%s" % key in lp_bug.tags:
                                    state = "verified"
                                elif "verification-needed-%s" % key in lp_bug.tags:
                                    state = "needed"
                                elif "verification-done" in lp_bug.tags:
                                    state = "verified"

                                # If this was not spammed in our name by SWM then it is being validated in our parent.
                                if (
                                    not state.endswith("-tracker")
                                    and spammed_v1 not in lp_bug.tags
                                    and spammed_v2 not in lp_bug.tags
                                ):
                                    state = "parent-validated"

                                results["releases"][rls][pkg]["bugs"][bug]["title"] = lp_bug.title
                                results["releases"][rls][pkg]["bugs"][bug]["owner"] = lp_bug.owner
                                results["releases"][rls][pkg]["bugs"][bug]["state"] = state

                                results["releases"][rls][pkg]["bugs"][bug]["tags"] = []
                                for t in lp_bug.tags:
                                    results["releases"][rls][pkg]["bugs"][bug]["tags"].append(t)
                            except:
                                results["releases"][rls][pkg]["bugs"][bug][
                                    "title"
                                ] = "--- Error accessing this bugs Launchpad information. Possibly private?"
                                results["releases"][rls][pkg]["bugs"][bug]["owner"] = "unknown"
                                results["releases"][rls][pkg]["bugs"][bug]["state"] = "unknown"
                                results["releases"][rls][pkg]["bugs"][bug]["tags"] = []

            self.cache_save()

            results["updated"] = datetime.utcnow().strftime("%A, %d. %B %Y %H:%M UTC")
            results["releases_order"] = self.requested_series
            return json.dumps(results, sort_keys=True, indent=4)

        # Handle the user presses <ctrl-C>.
        #
        except KeyboardInterrupt:
            pass

        return None
