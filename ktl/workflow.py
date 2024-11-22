#!/usr/bin/env python
#

from ktl.kernel_series import KernelSeries
from ktl.log import cdebug

import re


# UbuntuError
#
class UbuntuError(Exception):
    # __init__
    #
    def __init__(self, error):
        self.msg = error


# DefaultAssigneeMissing
#
class DefaultAssigneeMissing(Exception):
    pass


# Methods related to workflow in tracking bugs
#


class Properties:
    # __init__
    #
    def __init__(self, bug):
        # get the current properties and save them
        self.bug = bug
        self.oldprops = bug.properties
        self.newprops = {}

    # setBugProperties
    #
    # Note - this should perhaps be in lpltk
    def set(self, newprops):
        """
        Set key:value pairs in the bug description. This
        follows a convention established in lpltk
        Input: a lpltk bug object and a dictionary
        of key:value pairs
        This function only stages the changes and does not write them to the
        bug description, to avoid rewriting the description
        multiple times
        """
        self.newprops.update(newprops)

    # flushBugProperties
    #
    # Note - this should perhaps be in lpltk
    def flush(self):
        """
        If needed, rewrite the bug description including
        changes staged by calls to setBugProperties
        """
        # See whether we really need to write anything new
        rmlist = []
        for keyname in self.newprops:
            if keyname in self.oldprops:
                if self.oldprops[keyname] == self.newprops[keyname]:
                    rmlist.append(keyname)
                    continue
        for keyname in rmlist:
            del self.newprops[keyname]
        if len(self.newprops) == 0:
            return

        # Set a name:value pair in a bug description
        olddescr = self.bug.description
        newdscr = ""
        re_kvp = re.compile(r"^(\s*)([\.\-\w]+):\s*(.*)$")
        last_key = {"": "bar"}
        # copy everything, removing an existing one with this name if it exists
        foundProp = False
        for line in olddescr.split("\n"):
            # Skip empty lines after we start properties
            if line == "" and foundProp:
                continue
            m = re_kvp.match(line)
            if m:
                foundProp = True
                # There is a property on this line (assume only one per line)
                # see if it matches the one we're adding
                level = m.group(1)
                item = m.group(2)
                key = item
                if len(level) > 0:
                    key = "%s.%s" % (last_key[""], item)
                last_key[level] = item
                if key in self.newprops:
                    # we're going to be adding this one, remove the existing one
                    continue
            newdscr = newdscr + line + "\n"

        for k in self.newprops:
            if self.newprops[k]:
                newdscr = newdscr + "%s:%s\n" % (k, self.newprops[k])
        self.bug.description = newdscr
        return


# Workflow
#
class Workflow:
    # Stable tasks, tags, etc vary according to the package name. This
    # is a dictionary with information necessary for the scripts to
    # to create and handle stable tracking bugs. Each entry corresponds
    # to a package name entry, and the following fields:
    # * task_assignment: dictionary with launchpad series nominations
    #   for stable kernel tracking bugs and their assignee (that is, the
    #   tasks on stable SRU updates, nominated on the tracking bugs, and
    #   the launchpad user name responsible for that task).
    # * initial_bug_tags: tags to be added on the tracking bug when it's
    #   created
    # * subscribers: launchpad persons or teams to subscribe
    #   automatically to the tracking bugs when they are created
    # * invalidate_tasks: task assignments that should be invalid on the
    #   tracking bugs when they are created, depending on the kernel
    #   version. The list of kernel versions where the task is invalid
    #   is the value which must be provided
    tdb = {
        "linux": {
            "task_assignment": {
                "snap-prepare": "canonical-kernel-team",
                "snap-release-to-beta": "canonical-kernel-team",
                "snap-release-to-candidate": "canonical-kernel-team",
                "snap-release-to-edge": "canonical-kernel-team",
                "snap-release-to-stable": "canonical-kernel-team",
                "snap-qa-testing": "canonical-kernel-team",
                "snap-publish": "canonical-kernel-team",
                "snap-certification-testing": "canonical-hw-cert",
                "prepare-package": "canonical-kernel-team",
                "prepare-package-lbm": "canonical-kernel-team",
                "prepare-package-lrg": "ubuntu-kernel-bot",
                "prepare-package-lrm": "canonical-kernel-team",
                "prepare-package-lrs": "ubuntu-kernel-bot",
                "prepare-package-lum": "canonical-kernel-team",
                "prepare-package-meta": "canonical-kernel-team",
                "prepare-package-ports-meta": "canonical-kernel-team",
                "prepare-package-signed": "canonical-kernel-team",
                "automated-testing": "canonical-kernel-team",
                "promote-to-proposed": "ubuntu-sru",
                "promote-signing-to-proposed": "ubuntu-sru",
                "verification-testing": "canonical-kernel-team",
                "certification-testing": "canonical-hw-cert",
                "regression-testing": "canonical-kernel-team",
                "promote-to-updates": "ubuntu-sru",
                "promote-to-security": "ubuntu-sru",
                "security-signoff": "canonical-security",
                "stakeholder-signoff": "canonical-kernel-team",
                "kernel-signoff": "canonical-kernel-team",
                "signing-signoff": "canonical-kernel-team",
            },
            "initial_bug_tags": ["kernel-release-tracking-bug", "kernel-release-tracking-bug-live"],
            "subscribers": ["ubuntu-sru", "hardware-certification"],
            "invalidate_tasks": {
                "certification-testing": ["3.5.0"]  # Kernels that are supported but Cert. no longer tests
            },
        },
        "default": {
            "task_assignment": {
                "snap-prepare": "canonical-kernel-team",
                "snap-release-to-beta": "canonical-kernel-team",
                "snap-release-to-candidate": "canonical-kernel-team",
                "snap-release-to-edge": "canonical-kernel-team",
                "snap-release-to-stable": "canonical-kernel-team",
                "snap-qa-testing": "oem-qa",
                "snap-publish": "canonical-kernel-team",
                "snap-certification-testing": "canonical-hw-cert",
                "prepare-package": "canonical-kernel-team",
                "prepare-package-lbm": "canonical-kernel-team",
                "prepare-package-lrg": "ubuntu-kernel-bot",
                "prepare-package-lrm": "canonical-kernel-team",
                "prepare-package-lrs": "ubuntu-kernel-bot",
                "prepare-package-lum": "canonical-kernel-team",
                "prepare-package-meta": "canonical-kernel-team",
                "prepare-package-ports-meta": "canonical-kernel-team",
                "prepare-package-signed": "canonical-kernel-team",
                "automated-testing": "canonical-kernel-team",
                "promote-to-proposed": "ubuntu-sru",
                "verification-testing": "canonical-kernel-team",
                "certification-testing": "canonical-hw-cert",
                "regression-testing": "canonical-kernel-team",
                "promote-to-updates": "ubuntu-sru",
                "promote-to-security": "ubuntu-sru",
                "security-signoff": "canonical-security",
                "stakeholder-signoff": "canonical-kernel-team",
                "kernel-signoff": "canonical-kernel-team",
                "signing-signoff": "canonical-kernel-team",
            },
            "initial_bug_tags": ["kernel-release-tracking-bug", "kernel-release-tracking-bug-live"],
            "subscribers": ["sru-verification", "ubuntu-sru", "hardware-certification"],
        },
    }

    # Development tasks, tags, etc vary according to the package name.
    # This is a dictionary with information necessary for the scripts
    # to create and handle tracking bugs for development kernels. Each
    # entry corresponds to a package name entry, and the following fields:
    # * task_assignment: dictionary with launchpad series nominations
    #   for development kernel tracking bugs and their assignee (that
    #   is, the tasks on development kernel releases, nominated on the
    #   tracking bugs, and the launchpad user name responsible for that
    #   task)
    # * initial_bug_tags: tags to be added on the tracking bug when it's
    #   created
    # * subscribers: launchpad persons or teams to subscribe
    #   automatically to the tracking bugs when they are created
    devel_workflow = {
        "default": {
            "task_assignment": {
                "prepare-package": "canonical-kernel-team",
                "prepare-package-lbm": "canonical-kernel-team",
                "prepare-package-meta": "canonical-kernel-team",
                "prepare-package-signed": "canonical-kernel-team",
                "automated-testing": "canonical-kernel-team",
                "promote-to-release": "ubuntu-archive",
                "promote-to-proposed": "canonical-kernel-team",
                "regression-testing": "canonical-kernel-team",
            },
            "initial_bug_tags": ["kernel-release-tracking-bug", "kernel-release-tracking-bug-live"],
            "subscribers": [],
        }
    }

    # assignee
    #
    def assignee_ex(self, series_codename, packagename, taskname, devel):
        """ """
        retval = None
        if taskname in ["stakeholder-signoff"]:
            ks = KernelSeries()
            cursor = ks.lookup_series(codename=series_codename)
            cursor = cursor.lookup_source(packagename)
            if cursor is not None:
                retval = cursor.stakeholder
        if retval is None:
            retval = self.assignee(packagename, taskname, devel)
        return retval

    def assignee(self, packagename, taskname, devel):
        """
        Using the given package name and task name, return the launchpad
        team or person who should be assigned that task. If the
        package name is not in the dictionary, return the default
        """
        retval = None
        if devel:
            db = self.devel_workflow
        else:
            db = self.tdb

        if packagename in db:
            if taskname in db[packagename]["task_assignment"]:
                retval = db[packagename]["task_assignment"][taskname]
        else:
            try:
                retval = db["default"]["task_assignment"][taskname]
            except KeyError:
                raise DefaultAssigneeMissing("There is no default assignee in the database for '%s'." % (taskname))
        return retval

    # initial_tags
    #
    def initial_tags(self, packagename, devel):
        """
        Lookup the given package name and return the tags which
        should be initially applied to the tracking bug
        """
        if devel:
            db = self.devel_workflow
        else:
            db = self.tdb
        if packagename in db:
            return db[packagename]["initial_bug_tags"]
        else:
            return db["default"]["initial_bug_tags"]

    # subscribers
    #
    def subscribers(self, packagename, devel):
        """
        Lookup the given package name and return a list of
        teams who should be initially subscribed to the tracking bug
        """
        if devel:
            db = self.devel_workflow
        else:
            db = self.tdb
        if packagename in db:
            return db[packagename]["subscribers"]
        else:
            return db["default"]["subscribers"]

    # is task invalid for that series version
    #
    def is_task_invalid(self, packagename, taskname, version):
        """
        Return if the task is invalid for that package version
        """
        if packagename not in self.tdb:
            return False
        if "invalidate_tasks" not in self.tdb[packagename]:
            return False
        if taskname not in self.tdb[packagename]["invalidate_tasks"]:
            return False
        version_list = self.tdb[packagename]["invalidate_tasks"][taskname]
        return version in version_list

    def is_task_valid(s, wf_series, ks_source, variant, snap_name=None):
        """
        Internal helper to decide whether a certain workflow task should be
        added to a launchpad bug.

        Returns: True (task is valid) or False (otherwise)
        """
        retval = False
        ks_series = ks_source.series

        # Some tasks only really make sense in development or stable series.
        if ks_series.development is True:
            exclude = "devel"
            exclusions = {
                "promote-to-updates": True,
                "promote-to-security": True,
                "certification-testing": True,
                "verification-testing": True,
                "security-signoff": True,
                "stakeholder-signoff": True,
                "kernel-signoff": True,
            }
        else:
            exclude = "stable"
            exclusions = {
                "promote-to-release": True,
            }

        task_name = wf_series.name
        while True:
            if not wf_series.active:
                break
            if task_name in ["trunk", "latest"]:
                break
            if task_name.endswith("-dnu"):
                cdebug('    {} marked "do not use"'.format(task_name[:-4]), "yellow")
                break
            if task_name in exclusions:
                cdebug("    off-{} no {} ".format(exclude, task_name), "yellow")
                break

            # SELECT: drop any series for a different variant.
            if variant in ("debs"):
                if task_name.startswith("snap-"):
                    cdebug("    off-variant no {} ".format(task_name), "yellow")
                    break
            elif variant in ("snap-debs"):
                if not task_name.startswith("snap-"):
                    cdebug("    off-variant no {}".format(task_name), "yellow")
                    break

            # DEBS: exclusions related to debs.
            if task_name.startswith("prepare-package-"):
                pkg_type = task_name.replace("prepare-package-", "")
                ks_pkg = None
                for entry in ks_source.packages:
                    if entry.type == pkg_type:
                        ks_pkg = entry
                        break
                if ks_pkg is None:
                    cdebug("    no {}".format(task_name), "yellow")
                    break
            elif task_name == "stakeholder-signoff":
                if ks_source.stakeholder is None:
                    cdebug("    no stakeholder-signoff", "yellow")
                    break
            elif task_name == "kernel-signoff":
                if ks_source.derived_from is not None:
                    cdebug("    no kernel-signoff (manual for derivatives)", "yellow")
                    break
            elif task_name == "signing-signoff":
                cdebug("    no signing-signoff (manual always)", "yellow")
                break
            elif task_name == "promote-signing-to-proposed":
                ks_route = ks_source.routing
                if ks_route is not None:
                    ks_dst = ks_route.lookup_destination("signing")
                else:
                    ks_dst = None

                if ks_dst is None:
                    cdebug("    no promote-signing-to-proposed", "yellow")
                    break

            # SNAPS: exclusions related to snaps.
            if task_name.startswith("snap-"):
                snap = None
                for entry in ks_source.snaps:
                    if entry.name == snap_name or (snap_name is None and entry.primary):
                        snap = entry
                        break
                if snap is None:
                    cdebug("    no {}".format(task_name), "yellow")
                    break
                if task_name == "snap-certification-testing":
                    if not snap.hw_cert:
                        cdebug("    no {}".format(task_name), "yellow")
                        break
                elif task_name == "snap-qa-testing":
                    if not snap.qa:
                        cdebug("    no {}".format(task_name), "yellow")
                        break
                elif task_name == "snap-publish":
                    if not snap.gated:
                        cdebug("    no {}".format(task_name), "yellow")
                        break

            retval = True
            break

        return retval


if __name__ == "__main__":
    workflow = Workflow()
    db = workflow.tdb

    print(workflow.assignee("linux", "prepare-package"))
    print(workflow.assignee("linux", "nonexistent-task"))
