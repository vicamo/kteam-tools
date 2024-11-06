#!/usr/bin/env python
#

# from ktl.kernel               import *
from launchpadlib.launchpad import Launchpad
from urllib.request import urlopen
import json
import re
from os import path, mkdir
from ktl.kernel_series import KernelSeries
from os.path import exists, getmtime
from time import time


def cmp_to_key(mycmp):
    "Convert a cmp= function into a key= function"

    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0

    return K


def compare_versions(version1, version2):
    # print 'comparing ', version1, 'and', version2
    # 2.6.35-26.46

    r1 = re.split(r"[-\.\~\+]", version1)
    r2 = re.split(r"[-\.\~\+]", version2)
    for i in range(0, len(r1)):
        if r1[i] != r2[i]:
            return int(r1[i]) - int(r2[i])

    return 0


pocket_list = ["Proposed", "Updates", "Security", "Release"]


# fileage
#
def fileage(filename):
    # get time last modified
    if not exists(filename):
        return None

    # time in seconds since last change to file
    return time() - getmtime(filename)


# ArchiveError
#
class ArchiveError(Exception):
    # __init__
    #
    def __init__(self, error):
        self.msg = error


# Kernel
#
class Archive:
    debug = False

    # for Launchpad API
    lp_cachedir = path.join(path.expanduser("~"), ".cache", "ktl.archive.lp")

    # For the ckt-ppa.json and distro-archive.json files. By having them in a central
    # location, all apps wherever they are run can take advantage of them.
    #
    archive_cachedir = path.join(path.expanduser("~"), ".cache", "ktl.archive")
    if not path.exists(archive_cachedir):
        mkdir(archive_cachedir)

    # How often should we fetch files? (seconds)
    archive_cache_lifetime = 900  # 15 minutes

    statuses = ["Published"]

    # related to the kernel ppa
    __ppa_get_deleted = False
    __ppa_get_obsolete = False
    __ppa_get_superseded = False
    ppa = None
    allppainfo = False
    teamname = "canonical-kernel-team"
    ppaname = "ppa"
    ppafilename = path.join(archive_cachedir, "ckt-ppa.json")

    # related to the kernel distro archive
    __distro_get_deleted = False
    __distro_get_obsolete = False
    __distro_get_superseded = False
    distro = None
    alldistroinfo = False
    distrofilename = path.join(archive_cachedir, "distro-archive.json")

    # version
    #
    def ppa_versions(self, force=False):
        self.__fetch_ppa_if_needed(force)
        return self.ppa

    # version
    #
    def distro_versions(self, force=False):
        self.__fetch_distro_if_needed(force)
        return self.distro

    # __fetch_ppa_if_needed
    #
    def __fetch_ppa_if_needed(self, force):
        # see if there is a local json file that is recent
        # if there is, return the data
        age = fileage(self.ppafilename)

        if (not force) and age and (age < self.archive_cache_lifetime):
            # Try to fetch from the local file
            f = open(self.ppafilename, "r")
            self.ppa = json.load(f)
            f.close()
            if self.debug:
                print("Read cached PPA data, records:", len(self.ppa))
            if len(self.ppa) != 0:
                return
            else:
                print("Got nothing for PPA from cached results, fetching from Launchpad")

        # fetch from the PPA
        if self.debug:
            print("Fetching from Launchpad")

        statuses = list(self.statuses)
        if self.__ppa_get_deleted:
            statuses.append("Deleted")
        if self.__ppa_get_obsolete:
            statuses.append("Obsolete")
        if self.__ppa_get_superseded:
            statuses.append("Superseded")

        outdict = {}
        lp = Launchpad.login_anonymously("kernel team tools", "production", self.lp_cachedir)
        person = lp.people[self.teamname]
        ppa = person.getPPAByName(name=self.ppaname)

        for astatus in statuses:
            psrc = ppa.getPublishedSources(status=astatus)
            for p in psrc:
                fd = urlopen(p.self_link)
                sourceinfo = json.loads(fd.read().decode("utf-8"))

                # Add some plain text fields for some info
                sourceinfo["creator"] = sourceinfo["package_creator_link"].split("/")[-1].strip("~")
                sourceinfo["signer"] = sourceinfo["package_signer_link"].split("/")[-1].strip("~")
                rm = re.match(r"[0-9]\.[0-9](\.[0-9][0-9])*", sourceinfo["source_package_version"])
                if rm is None:
                    continue  # skip this one
                sourceinfo["series"] = sourceinfo["display_name"].split()[-1]
                # And strip some things we don't care about
                if not self.allppainfo:
                    for delkey in [
                        "archive_link",
                        "distro_series_link",
                        "http_etag",
                        "package_maintainer_link",
                        "resource_type_link",
                        "package_creator_link",
                        "package_signer_link",
                        "section_name",
                        "scheduled_deletion_date",
                        "removal_comment",
                        "removed_by_link",
                    ]:
                        del sourceinfo[delkey]

                key = p.source_package_name + "-" + p.source_package_version
                outdict[key] = sourceinfo

        jf = open(self.ppafilename, "w+")
        jf.write(json.dumps(outdict, sort_keys=True, indent=4))
        jf.close()

        self.ppa = outdict
        return

    # __fetch_distro_if_needed
    #
    def __fetch_distro_if_needed(self, force):
        # see if there is a local json file that is recent
        # if there is, return the data
        age = fileage(self.distrofilename)

        if (not force) and age and (age < self.archive_cache_lifetime):
            # read from the local file
            f = open(self.distrofilename, "r")
            self.distro = json.load(f)
            f.close()
            if self.debug:
                print("Read cached Distro data, records:", len(self.distro))
            if len(self.distro) != 0:
                return
            else:
                print("Got nothing for distro from cached results, fetching from Launchpad")

        # fetch from the PPA
        if self.debug:
            print("Fetching from Distro archives")

        statuses = list(self.statuses)
        if self.__distro_get_deleted:
            statuses.append("Deleted")
        if self.__distro_get_obsolete:
            statuses.append("Obsolete")
        if self.__distro_get_superseded:
            statuses.append("Superseded")

        lp = Launchpad.login_anonymously("kernel team tools", "production", self.lp_cachedir)
        masteroutdict = {}

        # archive = lp.distributions['ubuntu'].getSeries(name_or_version=info['name']).main_archive
        archive = lp.distributions["ubuntu"].getArchive(name="primary")
        kernel_series = KernelSeries()

        # Grab a list of all of the supported debian package names.
        kernel_source_packages = []
        for series in kernel_series.series:
            if not series.supported:
                continue
            for source in series.sources:
                if not source.supported:
                    continue
                for package in source.packages:
                    if package.name not in kernel_source_packages:
                        kernel_source_packages.append(package.name)

        for astatus in statuses:
            for pname in kernel_source_packages:
                if self.debug:
                    print("fetching for package", pname, "status", astatus)
                outdict = {}
                psrc = archive.getPublishedSources(status=astatus, exact_match=True, source_name=pname)
                for p in psrc:
                    fd = urlopen(p.self_link)
                    sourceinfo = json.loads(fd.read().decode("utf-8"))
                    if self.debug:
                        print("fetched", sourceinfo["source_package_name"], sourceinfo["source_package_version"])

                    # Add some plain text fields for some info
                    field = sourceinfo["package_creator_link"]
                    if field:
                        sourceinfo["creator"] = field.split("/")[-1].strip("~")
                    else:
                        sourceinfo["creator"] = "Unknown"
                    field = sourceinfo["package_signer_link"]
                    if field:
                        sourceinfo["signer"] = field.split("/")[-1].strip("~")
                    else:
                        sourceinfo["signer"] = "Unknown"
                    rm = re.match(r"[0-9]\.[0-9](\.[0-9][0-9])*", sourceinfo["source_package_version"])
                    if rm is None:
                        print("  ** Error: The source package version failed to match the regular expression.")
                        raise
                    version = rm.group(0)
                    sourceinfo["series"] = sourceinfo["display_name"].split()[-1]
                    # And strip some things we don't care about
                    if not self.allppainfo:
                        for delkey in [
                            "archive_link",
                            "distro_series_link",
                            "http_etag",
                            "package_maintainer_link",
                            "resource_type_link",
                            "package_creator_link",
                            "package_signer_link",
                            "section_name",
                            "scheduled_deletion_date",
                            "removal_comment",
                            "removed_by_link",
                        ]:
                            del sourceinfo[delkey]

                    key = p.source_package_name + "-" + p.source_package_version + "-" + p.pocket
                    if self.debug:
                        print("    found: ", key)
                    outdict[key] = sourceinfo

                if len(outdict) == 0:
                    if self.debug:
                        print("Nothing from ", astatus, pname)
                    continue

                #
                # Now we have all the data for this package name and status
                # Remove all the unsupported ones
                if self.debug:
                    print("records in outdict after fetch", len(outdict))
                unsupported = []
                serieslist = []
                for series in kernel_series.series:
                    if not series.supported:
                        if self.debug:
                            print("DEBUG: Fetching from archive, will skip release ", series.codename)
                        unsupported.append(series.codename)
                    else:
                        serieslist.append(series.codename)
                # remove unwanted ones
                purge = []
                for name, sourceinfo in outdict.items():
                    if sourceinfo["series"] in unsupported:
                        if self.debug:
                            print("DEBUG: Fetching from archive, skipping ", name)
                        purge.append(name)
                for k in purge:
                    del outdict[k]

                #
                # We now have a collection of all supported packages for a given
                # package name and status. Within each permutation of series and
                # pocket, keep only the highest version
                for series in serieslist:
                    for pocket in pocket_list:
                        templist = {}
                        for name, sourceinfo in outdict.items():
                            if sourceinfo["pocket"] == pocket and sourceinfo["series"] == series:
                                if self.debug:
                                    print("found matching", json.dumps(sourceinfo, sort_keys=True, indent=4))
                                templist[sourceinfo["source_package_version"]] = name
                        # Now sort the templist
                        slist = sorted(templist, key=cmp_to_key(compare_versions), reverse=True)
                        # and delete all but the highest version from the main list
                        for k in range(1, len(slist)):
                            if self.debug:
                                print("deleting", templist[slist[k]])
                            # If the same version was in Security and Updates . . .
                            del outdict[templist[slist[k]]]

                if self.debug:
                    print("Updating Master")
                    print("records in outdict", len(outdict))
                    print("records in masteroutdict", len(masteroutdict))
                    # print json.dumps(outdict, sort_keys=True, indent=4)
                masteroutdict.update(outdict)

        jf = open(self.distrofilename, "w+")
        jf.write(json.dumps(masteroutdict, sort_keys=True, indent=4))
        jf.close()
        self.distro = masteroutdict
        return


# vi:set ts=4 sw=4 expandtab:
