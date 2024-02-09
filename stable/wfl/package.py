#!/usr/bin/env python
#

import re
from datetime                           import datetime, timedelta, timezone
from hashlib                            import sha384
import json
import yaml

from  debian.debian_support             import version_compare

from lazr.restfulclient.errors          import NotFound, Unauthorized, ServerError
from httplib2.socks                     import HTTPError

from ktl.msgq                           import MsgQueue, MsgQueueCkct
from ktl.utils                          import date_to_string, dump

from .check_component                   import CheckComponent
from .context                           import ctx
from .errors                            import ShankError, ErrorExit, WorkflowCrankError
from .git_tag                           import GitTag, GitTagError
from .log                               import cdebug, cerror, cwarn, center, cleave, Clog, cinfo, centerleave, centerleaveargs

# PackageError
#
class PackageError(ShankError):
    '''
    Thrown when some basic information about the package that is associated with the
    shankbug could not be determined.
    '''
    pass


# SeriesLookupFailure
#
class SeriesLookupFailure(ShankError):
    '''
    Thrown when the series lookup throws a KeyError exception.
    '''
    pass


# PackageBuildRouteEntry
#
class PackageBuildRouteEntry:
    """
    Represents a package-build on a specified source package
    route-entry.

    This object represents all infomation related to both the
    top-level Debian source package for the `package` and the
    related Debian binary binary-packages including the current
    Launchpad build stati where relevant.

    :ivar bug:
        the associated WorkflowBug (or None)
    :ivar series:
        the Ubuntu distribution series codename for this build
    :ivar dependent:
        the package-type for this build
    :ivar route_name:
        the human visible name for this route entry
    :ivar route_entry:
        the human visible offset for this route entry
    :ivar archive:
        the Launchpad archive object for this route entry
    :ivar pocket:
        the Launchpad pocket name this route entry
    :ivar package:
        the source package name for this build
    """

    def __init__(self, series, dependent, route_name, route_entry, archive, pocket, package, bug=None):
        """
        :param series:
            the Ubuntu distribution series codename for this build
        :param dependent:
            the package-type for this build
        :param route_name:
            the human visible name for route entry
        :param route_entry:
            the human visible offset for this route entry
        :param archive:
            the Launchpad archive object for this route entry
        :param pocket:
            the Launchpad pocket name this route entry
        :param package:
            the source package name for this build
        """
        self.bug = bug
        self.series = series
        self.dependent = dependent
        self.route_name = route_name
        self.route_entry = route_entry
        self.archive = archive
        self.pocket = pocket
        self.package = package

        self.route_name_entry = "{}#{}".format(self.route_name, self.route_entry)

        self._source = False
        self._binary_analysis = False

        self.monitors = []

    def monitor_add(self, monitor):
        cinfo("monitor_add({})".format(monitor))
        self.monitors.append(monitor)

    @property
    def reference(self):
        """the archive reference for this route entry"""
        return self.archive.reference

    @property
    def source(self):
        """the Launchpad source package object"""
        if self._source is False:
            cdebug("SOURCE {} {} {}".format(self.dependent, self.route_name_entry, self.package))
            srcs = self.archive.getPublishedSources(
                order_by_date=True,
                exact_match=True,
                distro_series=self.series,
                source_name=self.package,
                pocket=self.pocket,
            )
            # Only consider positive states as present.
            if len(srcs) > 0 and srcs[0].status in ("Pending", "Published"):
                src = srcs[0]
            else:
                src = None
            self._source = src

            # Generate a monitor record for this source.
            monitor = {
                "type": "launchpad-source",
                "reference": self.archive.reference,
                "pocket": self.pocket,
                #"series": s.series,
                "package": self.package,
                "last-scanned": self.bug.tracker_instantiated, # XXX: can we fill this in at conversion?
            }
            if src:
                monitor['status'] = src.status
                monitor['lp-api'] = src.self_link
            self.monitor_add(monitor)
        return self._source

    @property
    def version(self):
        """the Launchpad source package version"""
        src = self.source
        return src.source_package_version if src is not None else None

    @property
    def changes_url(self):
        """the Launchpad source package changes URL"""
        src = self.source
        return src.changesFileUrl() if src is not None else None

    @property
    def creator(self):
        """the Launchpad source package creator"""
        src = self.source
        return src.package_creator if src is not None else None

    @property
    def signer(self):
        """the Launchpad source package signer"""
        src = self.source
        return src.package_signer if src is not None else None

    @property
    def binary_analysis(self):
        source = self.source
        if self._binary_analysis is False and source is None:
            self._binary_analysis = {}

        elif self._binary_analysis is False:
            cdebug("BINARY {} {} {}".format(self.dependent, self.route_name_entry, self.package))
            published = source.date_published
            latest_build = source.date_published
            status = set()
            status.add('UNKNOWN')

            status_detail = []

            cdebug("source status={}".format(source.status))
            if source.status == "Pending":
                status.add('PENDING')
            elif source.status == "Published":
                status.add('FULLYBUILT')
            else:
                # Anything else is broken.
                #  Superseded
                #  Deleted
                #  Obsolete
                status.add('FAILEDTOBUILD')

            arch_build = set()
            arch_complete = set()
            builds = source.getBuilds()
            if len(builds) == 0:
                self.monitor_add({
                        'type': 'launchpad-nobuilds',
                        'reference': self.archive.reference,
                        'pocket': self.pocket,
                        #'status': source.status,
                        'lp-api': source.self_link,
                        'last-scanned': self.bug.tracker_instantiated}) # XXX: can we fill this in at conversion?
            for build in builds:
                buildstate = build.buildstate
                ##print(build, build.buildstate, build.datebuilt)
                cdebug("build arch={} status={}".format(build.arch_tag, buildstate))
                if build.buildstate in (
                    "Needs building",
                    "Currently building",
                    "Gathering build output",
                    "Uploading build",
                ):
                    status.add('BUILDING')

                elif buildstate == 'Dependency wait':
                    status.add('DEPWAIT')

                elif buildstate == 'Successfully built':
                    status.add('FULLYBUILT')
                    arch_complete.add(build.arch_tag)

                else:
                    # Anything else is a failure, currently:
                    #  Build for superseded Source
                    #  Failed to build
                    #  Chroot problem
                    #  Failed to upload
                    #  Cancelling build
                    #  Cancelled build
                    status.add('FAILEDTOBUILD')

                if build.buildstate in (
                    "Failed to build",
                    "Needs building",
                    "Currently building",
                    "Gathering build output",
                    "Uploading build",
                    "Dependency wait",
                ):
                    self.monitor_add({
                            'type': 'launchpad-build',
                            'reference': self.reference,
                            'pocket': self.pocket,
                            'status': buildstate,
                            'lp-api': build.self_link,
                            'last-scanned': self.bug.tracker_instantiated}) # XXX: (as above)

                #if buildstate != 'Successfully built':
                #    # XXX: do we use the maintenance records any more ?
                #    self.bug.maintenance_add({
                #        'type': 'deb-build',
                #        'target': self.bug.target,
                #        'detail': {
                #            'state': buildstate,
                #            'type': self.dependent,
                #            'package': build.source_package_name,
                #            'url': build.web_link,
                #            'lp-api': build.self_link,
                #            'log': build.build_log_url,
                #        }})

                # Accumulate the latest build completion.
                if build.datebuilt is not None and (latest_build is None or latest_build < build.datebuilt):
                    latest_build = build.datebuilt

                # Accumulate the architectures we are meant to build for.
                arch_build.add(build.arch_tag)

            one_per_build = set()
            arch_published = set()
            # Grab all the binaries, including those superseded so we can tell if
            # we have been dominated away.
            binaries_all = source.getPublishedBinaries(active_binaries_only=False)

            # NOTE: that this set may contain more than record for a binary if that
            # binary has been republished to change components, or if it was simply
            # deleted and reinstated.  The records are guarenteed to be in reverse
            # date order within an arch/package combination.  Pick just the first one
            # for each combination.
            binaries = []
            binaries_seen = set()
            for binary in binaries_all:
                arch_tag = binary.distro_arch_series_link.split('/')[-1] if binary.architecture_specific else 'all'
                binary_key = (binary.distro_arch_series_link, binary.binary_package_name)
                if binary_key in binaries_seen:
                    cdebug("binary-duplicate arch={} status={} binary_package_name={} binary_package_version={} component_name={}".format(arch_tag, binary.status, binary.binary_package_name, binary.binary_package_version, binary.component_name))
                    continue
                binaries.append(binary)
                binaries_seen.add(binary_key)

            # Run the relevant binary records and make sure they are all live publications.
            for binary in binaries:
                ##print(binary, binary.status, binary.date_published)
                arch_tag = binary.distro_arch_series_link.split('/')[-1] if binary.architecture_specific else 'all'
                cdebug("binary arch={} status={} binary_package_name={} binary_package_version={} component_name={}".format(arch_tag, binary.status, binary.binary_package_name, binary.binary_package_version, binary.component_name))
                if binary.status == 'Pending':
                    status.add('PENDING')
                    status_detail.append("{} {} pending".format(arch_tag, binary.binary_package_name))
                elif binary.status  == 'Published':
                    status.add('FULLYBUILT')
                elif self.bug.accept_present("superseded-binaries") and binary.status == "Superseded":
                    cdebug("binary arch={} status={} binary_package_name={} binary_package_version={} component_name={} binary superseded accepted".format(arch_tag, binary.status, binary.binary_package_name, binary.binary_package_version, binary.component_name))
                    status.add('FULLYBUILT')
                elif binary.status == "Superseded":
                    status.add('SUPERSEDED')
                    status_detail.append("{} {} superceded".format(arch_tag, binary.binary_package_name))
                else:
                    # Anything else is broken.
                    #  Superseded
                    #  Deleted
                    #  Obsolete
                    cinfo("binary arch={} status={} binary_package_name={} binary_package_version={} component_name={}".format(arch_tag, binary.status, binary.binary_package_name, binary.binary_package_version, binary.component_name))
                    status.add('FAILEDTOBUILD')

                if binary.status == 'Pending' and binary.build_link not in one_per_build:
                    one_per_build.add(binary.build_link)
                    self.monitor_add({
                            'type': 'launchpad-binary',
                            'reference': self.reference,
                            'pocket': self.pocket,
                            'status': binary.status,
                            'lp-api': binary.self_link,
                            'last-scanned': self.bug.tracker_instantiated}) # XXX: (as above)

                # Accumulate the latest publication time.
                if published is None or (binary.date_published is not None and
                        published < binary.date_published):
                    published = binary.date_published

                # Accumulate the architectures we have publications for.
                if binary.architecture_specific:
                    arch_published.add(binary.distro_arch_series_link.split('/')[-1])

            # Ensure we have publications in every architecture for which we have a build.
            # In the case of a copy (with binaries) of a package we may have more published
            # architectures than we have builds.  If we have architecuture builds which are not
            # published check the publications to see if they are missing because they are in
            # the uploads or approval queues.
            if not arch_build.issubset(arch_published):
                cinfo("build/published missmatch arch_build={} arch_published={}".format(arch_build, arch_published))
                if arch_build == arch_complete:
                    uploads = source.distro_series.getPackageUploads(exact_match=True,
                            archive=self.archive, pocket=self.pocket, name=source.source_package_name,
                            version=source.source_package_version)
                    queued = False
                    for upload in uploads:
                        if upload.status == 'Rejected':
                            status.add('FAILEDTOBUILD')
                        elif upload.status != 'Done':
                            if upload.status in ('New', 'Unapproved', 'Accepted'):
                                queued = True
                            cinfo("upload not complete status={}".format(upload.status))
                            self.monitor_add({
                                    'type': 'launchpad-upload',
                                    'reference': self.reference,
                                    'pocket': self.pocket,
                                    'status': upload.status,
                                    'lp-api': upload.self_link,
                                    'last-scanned': self.bug.tracker_instantiated}) # XXX: (as above)
                    if queued:
                        status.add('QUEUED')
                    else:
                        status.add('PENDING')

                else:
                    status.add('BUILDING')

            # Pick out the stati in a severity order.
            for state in ('FAILEDTOBUILD', 'SUPERSEDED', 'DEPWAIT', 'BUILDING', 'QUEUED', 'PENDING', 'FULLYBUILT', 'UNKNOWN'):
                if state in status:
                    break

            if published is not None:
                published = published.replace(tzinfo=None)
            if latest_build is not None:
                latest_build = latest_build.replace(tzinfo=None)

            self._binary_analysis = {
                "published": published,
                "latest_build": latest_build,
                "status": state,
                "status_detail": status_detail,
            }

        return self._binary_analysis

    @property
    def published(self):
        """the most recent publication source and binary timestamp"""
        return self.binary_analysis.get("published")

    @property
    def latest_build(self):
        """the most recent build completion timestamp"""
        return self.binary_analysis.get("latest_build")

    # XXX: legacy interface.
    most_recent_build = latest_build

    @property
    def status(self):
        """the overall status of this build"""
        return self.binary_analysis.get("status")

    @property
    def built(self):
        return self.status == "FULLYBUILT"

    @property
    def status_detail(self):
        """the overall status details of this build"""
        return self.binary_analysis.get("status_detail")


# PackageBuildRoute
#
class PackageBuildRoute:
    """
    Represents a package build (source and binaries) on a specified source
    package route (proposed etc).

    :ivar bug:
        the associated WorkflowBug (or None)
    :ivar series:
        the Ubuntu distribution series codename for this build
    :ivar dependent:
        the package-type for this build
    :ivar route_name:
        the human visible name for this route
    :ivar routing:
        the routing (reference, pocket) pairs list for this route
    :ivar package:
        the source package name for this buidl
    :ivar stream_route:
        a boolean indicating whether this is route is affected by streaming
    """

    def __init__(self, series, dependent, route_name, routing, package, bug=None):
        """
        :param series:
            the Ubuntu distribution series codename for this build
        :param dependent:
            the package-type for this build
        :param route_name:
            the human visible name for the route (e.g. proposed)
        :param routing:
            a list of (reference, pocket) pairs representing the archive
            which make up this pocket
        :param package:
            the source package name for this build
        """
        self.bug = bug
        self.series = series
        self.dependent = dependent
        self.route_name = route_name
        self.routing = routing
        self.package = package

        self.stream_route = self.route_name in ('ppa', 'Proposed', 'as-proposed') or self.route_name.startswith('build')

        self._publications = False

    @property
    def publications(self):
        """
        Lazily instantiated list of publications in each route element

        :return:
            List of publications one per route element
        """
        cdebug("PUBLICATIONS {} {} {}".format(self.dependent, self.route_name, self.package))

        if self._publications is False:
            publications = []
            archive_num = 0
            for archive, pocket in self.routing:
                archive_num += 1
                if archive is None:
                    route_name_entry = "{}#{}".format(self.route_name, archive_num)
                    raise WorkflowCrankError("Routing table entry {} invalid".format(route_name_entry))
                publications.append(PackageBuildRouteEntry(self.series, self.dependent, self.route_name, archive_num, archive, pocket, self.package, bug=self.bug))

            self._publications = publications
        return self._publications

    def publications_match(self, limit_stream=None):
        """
        Return the publications in this route appropriate for ``limit_stream``
        if present.

        :param limit_stream:
            optional stream number to select from the route
        :return:
            list of ``PackageBuildRouteEntry`` objects representing selected
            builds
        """
        archive_only = limit_stream if self.stream_route else None
        return [pub for pub in self.publications if archive_only is None or pub.route_entry == archive_only]

    def version_match(self, exact=None, prefix=None, limit_stream=None):
        """
        Return the publications in this route which match the supplied criteria.

        :param exact:
            requests an exact version match
        :param prefix:
            requests a version prefix match
        :param limit_stream:
            requests consideration of entries in that stream
        :return:
            ``PackageBuildRouteEntry`` for the matching build
            ``None`` if no match is found
        """
        for pub in self.publications_match(limit_stream=limit_stream):
            if exact is not None and pub.version == exact:
                return pub
            if prefix is not None and pub.version is not None and pub.version.startswith(prefix):
                return pub
            if exact is None and prefix is None and pub.version is not None:
                return pub
        return None


# PackageBuild
#
class PackageBuild:

    def __init__(self, bug, series, dependent, pocket, routing, package, version, abi, sloppy):
        self.bug = bug
        self.series = series
        self.dependent = dependent
        self.pocket = pocket
        self.routing = routing
        self.package = package
        self.srch_version = version
        self.srch_abi = abi
        self.srch_sloppy = sloppy

        self._data = None

    # __is_fully_built
    #
    def __is_fully_built(s, package, abi, archive, release, pocket, sloppy):
        '''
        Have the source package specified been fully built?
        '''
        center(s.__class__.__name__ + '.__is_fully_built')
        cdebug('package: %s' % package, 'yellow')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('archive: %s' % archive.reference, 'yellow')
        cdebug('release: %s' % release, 'yellow')
        cdebug(' pocket: %s' % pocket, 'yellow')
        cdebug(' sloppy: %s' % pocket, 'yellow')

        # Do a loose match, we will select for the specific version we wanted
        # in __find_matches but this way we have the published version for
        # pocket emptyness checks.
        ps = archive.getPublishedSources(distro_series=s.series, exact_match=True, source_name=package, pocket=pocket, order_by_date=True)
        matches = s.__find_matches(ps, abi, release, sloppy)
        if len(matches) > 0 and matches[0].status in ('Pending', 'Published'):
            cdebug('    match: %s (%s)' % (release, abi), 'green')
            data = s.__sources_built(matches, archive, package, release, pocket)
            source = matches[0]
            data["version"] = source.source_package_version
            data["changes"] = source.changesFileUrl()
            data["source"] = source
        else:
            data = {
                "built": False,
                "creator": None,
                "signer": None,
                "published": None,
                "most_recent_build": None,
                "status": "",
                "changes": None,
            }
            source = None
            version = None
            if len(ps) > 0:
                source = ps[0]
                if source.status in ('Pending', 'Published'):
                    version = source.source_package_version
            data["source"] = source
            data["version"] = version

            monitor = {
                'type': 'launchpad-source',
                'reference': archive.reference,
                'pocket': pocket,
                #'series': s.series,
                'package': package,
                'last-scanned': s.bug.tracker_instantiated}
            if source:
                monitor['status'] = source.status
                monitor['lp-api'] = source.self_link
            s.bug.debs.monitor_debs_add(monitor)

        cleave(s.__class__.__name__ + '.__is_fully_built')
        return data

    # __find_matches
    #
    def __find_matches(s, ps, abi, release, sloppy):
        center('Sources::__find_matches')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('release: %s' % release, 'yellow')
        cdebug(' sloppy: %s' % release, 'yellow')
        cdebug('records: %d' % len(ps), 'yellow')

        match = False
        matches = []
        if abi:
            cdebug('abi match only')
            dep_ver1 = '%s-%s' % (release, abi)
            dep_ver2 = '%s.%s' % (release, abi)
            for p in ps:
                src_ver = p.source_package_version
                cdebug('examining: %s' % src_ver)
                if ((src_ver.startswith(dep_ver1 + '.') or src_ver.startswith(dep_ver2 + '.'))):
                    cdebug('adding: %s' % src_ver, 'green')
                    matches.append(p)
                    match = True
        else:
            cdebug('exact version match required')
            for p in ps:
                src_ver = p.source_package_version
                # Exact match or exact prefix plus '+somethingN'
                if src_ver == release or (sloppy and src_ver.startswith(release + '+')):
                    cdebug('adding: %s' % src_ver, 'green')
                    matches.append(p)
                    match = True

        cleave('Sources::__find_matches (%s)' % match)
        return matches

    # __sources_built
    #
    def __sources_built(s, sources, archive, package, release, pocket):
        '''
        '''
        center('Sources::__sources_built')
        cdebug('sources: %s' % sources, 'yellow')
        cdebug('archive: %s' % archive.reference, 'yellow')
        cdebug('package: %s' % package, 'yellow')
        cdebug('release: %s' % release, 'yellow')
        cdebug(' pocket: %s' % pocket, 'yellow')

        # If we do get more than one match we should be picking the latest.
        if len(sources) == 0:
            raise ValueError("too few sources")

        source = sources[0]

        package_creator = source.package_creator
        package_signer = source.package_signer
        published = source.date_published
        latest_build = source.date_published
        status = set()
        status.add('UNKNOWN')

        status_detail = []

        cdebug("source status={}".format(source.status))
        if source.status == "Pending":
            status.add('PENDING')
        elif source.status == "Published":
            status.add('FULLYBUILT')
        else:
            # Anything else is broken.
            #  Superseded
            #  Deleted
            #  Obsolete
            status.add('FAILEDTOBUILD')

        arch_build = set()
        arch_complete = set()
        builds = source.getBuilds()
        if len(builds) == 0:
            s.bug.debs.monitor_debs_add({
                    'type': 'launchpad-nobuilds',
                    'reference': archive.reference,
                    'pocket': pocket,
                    #'status': source.status,
                    'lp-api': source.self_link,
                    'last-scanned': s.bug.tracker_instantiated})
        for build in builds:
            buildstate = build.buildstate
            ##print(build, build.buildstate, build.datebuilt)
            cdebug("build arch={} status={}".format(build.arch_tag, buildstate))
            if build.buildstate in (
                "Needs building",
                "Currently building",
                "Gathering build output",
                "Uploading build",
            ):
                status.add('BUILDING')

            elif buildstate == 'Dependency wait':
                status.add('DEPWAIT')

            elif buildstate == 'Successfully built':
                status.add('FULLYBUILT')
                arch_complete.add(build.arch_tag)

            else:
                # Anything else is a failure, currently:
                #  Build for superseded Source
                #  Failed to build
                #  Chroot problem
                #  Failed to upload
                #  Cancelling build
                #  Cancelled build
                status.add('FAILEDTOBUILD')

            if build.buildstate in (
                "Failed to build",
                "Needs building",
                "Currently building",
                "Gathering build output",
                "Uploading build",
                "Dependency wait"
            ):
                s.bug.debs.monitor_debs_add({
                        'type': 'launchpad-build',
                        'reference': archive.reference,
                        'pocket': pocket,
                        'status': buildstate,
                        'lp-api': build.self_link,
                        'last-scanned': s.bug.tracker_instantiated})

            if buildstate != 'Successfully built':
                s.bug.maintenance_add({
                    'type': 'deb-build',
                    'target': s.bug.target,
                    'detail': {
                        'state': buildstate,
                        'type': s.dependent,
                        'package': build.source_package_name,
                        'url': build.web_link,
                        'lp-api': build.self_link,
                        'log': build.build_log_url,
                    }})

            # Accumulate the latest build completion.
            if build.datebuilt is not None and (latest_build is None or latest_build < build.datebuilt):
                latest_build = build.datebuilt

            # Accumulate the architectures we are meant to build for.
            arch_build.add(build.arch_tag)

        one_per_build = set()
        arch_published = set()
        # Grab all the binaries, including those superseded so we can tell if
        # we have been dominated away.
        binaries_all = source.getPublishedBinaries(active_binaries_only=False)

        # NOTE: that this set may contain more than record for a binary if that
        # binary has been republished to change components, or if it was simply
        # deleted and reinstated.  The records are guarenteed to be in reverse
        # date order within an arch/package combination.  Pick just the first one
        # for each combination.
        binaries = []
        binaries_seen = set()
        for binary in binaries_all:
            arch_tag = binary.distro_arch_series_link.split('/')[-1] if binary.architecture_specific else 'all'
            binary_key = (binary.distro_arch_series_link, binary.binary_package_name)
            if binary_key in binaries_seen:
                cdebug("binary-duplicate arch={} status={} binary_package_name={} binary_package_version={} component_name={}".format(arch_tag, binary.status, binary.binary_package_name, binary.binary_package_version, binary.component_name))
                continue
            binaries.append(binary)
            binaries_seen.add(binary_key)

        # Run the relevant binary records and make sure they are all live publications.
        for binary in binaries:
            ##print(binary, binary.status, binary.date_published)
            arch_tag = binary.distro_arch_series_link.split('/')[-1] if binary.architecture_specific else 'all'
            cdebug("binary arch={} status={} binary_package_name={} binary_package_version={} component_name={}".format(arch_tag, binary.status, binary.binary_package_name, binary.binary_package_version, binary.component_name))
            if binary.status == 'Pending':
                status.add('PENDING')
                status_detail.append("{} {} pending".format(arch_tag, binary.binary_package_name))
            elif binary.status  == 'Published':
                status.add('FULLYBUILT')
            elif s.bug.accept_present("superseded-binaries") and binary.status == "Superseded":
                cdebug("binary arch={} status={} binary_package_name={} binary_package_version={} component_name={} binary superseded accepted".format(arch_tag, binary.status, binary.binary_package_name, binary.binary_package_version, binary.component_name))
                status.add('FULLYBUILT')
            elif binary.status == "Superseded":
                status.add('SUPERSEDED')
                status_detail.append("{} {} superceded".format(arch_tag, binary.binary_package_name))
            else:
                # Anything else is broken.
                #  Superseded
                #  Deleted
                #  Obsolete
                cinfo("binary arch={} status={} binary_package_name={} binary_package_version={} component_name={}".format(arch_tag, binary.status, binary.binary_package_name, binary.binary_package_version, binary.component_name))
                status.add('FAILEDTOBUILD')

            if binary.status == 'Pending' and binary.build_link not in one_per_build:
                one_per_build.add(binary.build_link)
                s.bug.debs.monitor_debs_add({
                        'type': 'launchpad-binary',
                        'reference': archive.reference,
                        'pocket': pocket,
                        'status': binary.status,
                        'lp-api': binary.self_link,
                        'last-scanned': s.bug.tracker_instantiated})

            # Accumulate the latest publication time.
            if published is None or (binary.date_published is not None and
                    published < binary.date_published):
                published = binary.date_published

            # Accumulate the architectures we have publications for.
            if binary.architecture_specific:
                arch_published.add(binary.distro_arch_series_link.split('/')[-1])

        # Ensure we have publications in every architecture for which we have a build.
        # In the case of a copy (with binaries) of a package we may have more published
        # architectures than we have builds.  If we have architecuture builds which are not
        # published check the publications to see if they are missing because they are in
        # the uploads or approval queues.
        if not arch_build.issubset(arch_published):
            cinfo("build/published missmatch arch_build={} arch_published={}".format(arch_build, arch_published))
            if arch_build == arch_complete:
                uploads = source.distro_series.getPackageUploads(exact_match=True,
                        archive=archive, pocket=pocket, name=source.source_package_name,
                        version=source.source_package_version)
                queued = False
                for upload in uploads:
                    if upload.status == 'Rejected':
                        status.add('FAILEDTOBUILD')
                    elif upload.status != 'Done':
                        if upload.status in ('New', 'Unapproved', 'Accepted'):
                            queued = True
                        cinfo("upload not complete status={}".format(upload.status))
                        s.bug.debs.monitor_debs_add({
                                'type': 'launchpad-upload',
                                'reference': archive.reference,
                                'pocket': pocket,
                                'status': upload.status,
                                'lp-api': upload.self_link,
                                'last-scanned': s.bug.tracker_instantiated})
                if queued:
                    status.add('QUEUED')
                else:
                    status.add('PENDING')

            else:
                status.add('BUILDING')

        # Pick out the stati in a severity order.
        for state in ('FAILEDTOBUILD', 'SUPERSEDED', 'DEPWAIT', 'BUILDING', 'QUEUED', 'PENDING', 'FULLYBUILT', 'UNKNOWN'):
            if state in status:
                break

        if published is not None:
            published = published.replace(tzinfo=None)
        if latest_build is not None:
            latest_build = latest_build.replace(tzinfo=None)

        cleave('Sources::__sources_built' )
        return {
            "built": state == 'FULLYBUILT',
            "creator": package_creator,
            "signer": package_signer,
            "published": published,
            "most_recent_build": latest_build,
            "status": state,
            "status_detail": status_detail,
        }

    def instantiate(self):
        cdebug("INSTANTIATING {} {} {} {} {} {}".format(self.dependent, self.pocket, self.package, self.srch_version, self.srch_abi, self.srch_sloppy))

        build_route = self.pocket == 'ppa' or self.pocket.startswith('build')
        stream_route = self.pocket in ('ppa', 'Proposed', 'as-proposed') or self.pocket.startswith('build')

        publications = []
        archive_num = 0
        archive_only = self.bug.built_in if stream_route else None
        for (src_archive, src_pocket) in self.routing:
            archive_num += 1
            if archive_only is not None and archive_num != archive_only:
                continue
            if src_archive is None:
                raise WorkflowCrankError("Routing table entry {}#{} invalid".format(self.pocket, archive_num))
            info = self.__is_fully_built(self.package, self.srch_abi, src_archive, self.srch_version, src_pocket, self.srch_sloppy)
            publications.append(info)
            # If this archive pocket contains the version we are looking for then scan
            # no further.
            if info["status"] != '':
                break

        # If we have a match use that, else use the first one.
        if len(publications) == 0:
            publications = [{
                "built": False,
                "creator": None,
                "signer": None,
                "published": None,
                "most_recent_build": None,
                "status": "",
                "changes": None,
                "source": None,
                "version": None,
            }]
        if publications[-1]["status"] != '':
            info = publications[-1]
        else:
            info = publications[0]

        # XXX: __is_fully_built has this ... ?
        info["route"] = (src_archive, src_pocket)

        self._data = info

        cinfo('DELAYED %-8s %-8s : %-20s : %-5s / %-10s    (%s : %s) %s [%s %s]' % (self.dependent, self.pocket, self.package, info["built"], info["status"], info["published"], info["most_recent_build"], info["version"], src_archive.reference, src_pocket), 'cyan')

        # If we find a build is now complete, record _where_ it was built.
        if build_route and self._data['status'] != '':
            # NOTE: copy-proposed-kernel et al treat auto select build-private so just call this build.
            self.bug.built_in = archive_num

    def __getattr__(self, name):
        if self._data is None:
            self.instantiate()
        if name not in self._data:
            raise AttributeError()
        return self._data[name]

    def __getitem__(self, name):
        if self._data is None:
            self.instantiate()
        return self._data[name]

    def get(self, name, default=None):
        if self._data is None:
            self.instantiate()
        return self._data.get(name, default)


# Package
#
class Package():

    # __init__
    #
    def __init__(s, shankbug):
        center('package::__init__')
        s.bug = shankbug

        s.__distro_series = None

        # debs record their versions in their title -- sync back canonical form.
        s.bug.version_from_title()
        s.bug.update_title()

        # Handle version changes.
        clamp = s.bug.clamp('self')
        if s.bug.version != s.bug.clamp('self'):
            cinfo("tracker version has changed resetting tracker {} -> {}".format(clamp, s.bug.version))
            s.bug.clamp_assign('self', s.bug.version)

            if 'versions' in s.bug.bprops:
                cinfo("tracker version has changed dropping package version data")
                del s.bug.bprops['versions']

        # XXX: TRANSITION -- use the cycle information to work out which stream
        # we are going to default to.
        stream = s.bug.built_in
        if stream is None:
            sru_cycle = s.bug.sc.lookup_spin(s.bug.sru_spin_name)
            if sru_cycle is not None and sru_cycle.stream is not None:
                stream = sru_cycle.stream
                cinfo("APW: STREAM2 -- no stream set, set to {}".format(int(stream)))
                s.bug.built_in = stream
                s.bug.flag_assign('stream-from-cycle', True)
            else:
                cinfo("APW: STREAM2 -- no stream set, cannot set for {}".format(s.bug.sru_spin_name))
        else:
            cinfo("APW: STREAM2 -- stream already present {}".format(stream))

        # Pick up versions from our bug as needed.
        s.series = s.bug.series
        s.name = s.bug.name
        s.version = s.bug.version
        s.source = s.bug.source
        s.kernel = s.bug.kernel
        s.abi = s.bug.abi
        s._pkgs = False

        # Look the package routing destinations up in kernel-series, convert the
        # archives to real archive objects.
        s._routing = {}
        s.routing_mode = 'None'
        if s.source is not None:
            try:
                routing = s.source.routing
            except ValueError as e:
                raise PackageError(e.args[0])
            for (key, destination) in (
                ('ppa', 'build'),
                ('build', 'build'),
                ('build-private', 'build-private'),
                ('Signing', 'signing'),
                ('Proposed', 'proposed'),
                ('as-proposed', 'as-proposed'),
                ('Updates', 'updates'),
                ('Security', 'security'),
                ('Release', 'release'),
                ):
                routes = routing.lookup_destination(destination)
                if routes is None:
                    continue
                route_list = []
                for route in routes:
                    archive = s.lp.archives.getByReference(reference=route[0])
                    route_list.append((archive, route[1]))
                s._routing[key] = route_list
            s.routing_mode = s.source.routing.name


        cinfo('     test_flavours: %s' % (s.test_flavours()), 'blue')
        cinfo('test_flavour_meta4: %s' % (s.test_flavour_meta()), 'blue')
        cinfo('     Routing mode: {}'.format(s.routing_mode), 'blue')
        cinfo('    Routing table:', 'blue')
        for pocket, pocket_data in s._routing.items():
            if pocket_data is None:
                cerror('        {}: {} {}'.format(pocket, 'NONE', 'NONE', 'red'))
            else:
                for route in pocket_data:
                    route_reference = "NONE" if route[0] is None else route[0].reference
                    cinfo('        {}: {} {}'.format(pocket, route_reference, route[1]), 'blue')

        if s.source is None:
            raise PackageError('Unable to check package builds for this bug: the package/series combination is invalid')

        s._cache = None
        s._builds = None
        s._version_tried = {}

        s._monitor_debs = []

        cleave('package::__init__')

    @property
    def lp(self):
        return ctx.lp

    @property
    def kernel_series(self):
        return self.bug.kernel_series

    @property
    def monitor_debs(s):
        return s._monitor_debs

    def monitor_debs_add(s, what):
        if what not in s._monitor_debs:
            s._monitor_debs.append(what)

    @property
    def pkgs(self):
        if self._pkgs is False:
            self._pkgs = self.pkgs_qualified
        return self._pkgs

    def routing(self, pocket):
        center(self.__class__.__name__ + '.routing')
        routes = self._routing.get(pocket)
        cleave(self.__class__.__name__ + '.routing')
        return routes

    def monitor_routes(self, routes):
        if 'ppa' in routes:
            routes.remove('ppa')
            routes.append('build')
            routes.append('build-private')
        for route_name in routes:
            route_found = self.pocket_route(route_name)
            if route_found is not None:
                cinfo("monitor_routes: {} location found {}".format(route_name, route_found))
                route_list = [route_found]
            else:
                route_list = self.routing(route_name)
            if route_list is None:
                continue
            cinfo("monitor_routes: {} using {}".format(route_name, route_list))
            for route_archive, route_pocket in route_list:
                # Copy over any build related monitors for this archive/pocket.
                for monitor in self.monitor_debs:
                    if (monitor['reference'] == route_archive.reference and
                            monitor['pocket'] == route_pocket):
                        self.bug.monitor_add(monitor)

    @property
    def prepare_id(s):
        # If we have no versions, then special case the result as None.
        if 'versions' not in s.bug.bprops:
            return None

        # Create a stable hash of the versions table for this package.
        signature = sorted(s.bug.bprops.get('versions', {}).items())
        id_hash = sha384()
        id_hash.update(str(signature).encode())
        return id_hash.hexdigest()[:16]

    def package_version_exact(self, pkg):
        ancillary_for = self.ancillary_package_for(pkg)
        if ancillary_for is not None:
            pkg = ancillary_for
        return self.bug.bprops.get('versions', {}).get(pkg)

    def package_version(s, pkg):
        # Look up the specific version of a package for this tracker.
        version = s.bug.bprops.get('versions', {}).get(pkg)
        if version is None and s._version_tried.get(pkg) is None:
            s._version_tried[pkg] = True

            # Lookup the kernel-series package we are referring to.
            package_package = None
            for package in s.source.packages:
                if (package.type == pkg or (
                    package.type is None and pkg == 'main')
                    ):
                    package_package = package
                    break
            if not package_package:
                return None

            # If the package is an ancillary package then if that package has a version
            # then we should take it.
            ancillary_for = s.ancillary_package_for(pkg)
            if ancillary_for is not None:
                return s.bug.bprops.get('versions', {}).get(ancillary_for)

            # Work out the package version form based on its type.
            if pkg == 'lbm':
                version_lookup, version_sloppy = (s.bug.kernel + '-' + s.bug.abi, '.')
            elif pkg in ('meta', 'ports-meta'):
                version_lookup, version_sloppy = (s.bug.kernel + '.' + s.bug.abi, '.')
            else:
                version_lookup, version_sloppy = (s.bug.version, '+')

            # Try and find a matching
            try:
                git_tag = GitTag(package_package, version_lookup, version_sloppy)
                if git_tag.verifiable and git_tag.present:
                    version = git_tag.version
            except GitTagError as e:
                cerror("{} {} ({}): Tag lookup failed -- {}".format(
                    package_package, version_lookup, version_sloppy, e))

            # Cache any positive version matches.
            if version is not None:
                s.bug.bprops.setdefault('versions', {})[pkg] = version

        return version

    def ancillary_package_for(self, ptype):
        """
        Returns the package-type of the package for which ``ptype`` is an
        ancillary, if any.  That is the package which owns ``ptype``.

        :param ptype:
            package-type of the package to examine.
        :return:
            package-type of our owning package.
            ``None`` if ``ptype`` is not an ancillary.
        """
        pkg = self.source.lookup_package(type=ptype)
        if pkg is None:
            return None
        owner = pkg.ancillary_for
        if owner is None:
            return None
        return owner.type or "main"

    def signing_package_for(self, ptype):
        """
        Returns the package-type of the package for which ``ptype`` is a signing
        consumer, if any.  That is the package which produces the signable material
        which ``ptype`` consumes.

        :param ptype:
            package-type of the package to examine.
        :return:
            package-type of our signing producer.
            ``None`` if ``ptype`` is not a signing consumer.
        """
        pkg = self.source.lookup_package(type=ptype)
        if pkg is None:
            return None
        signing = pkg.signing_from
        if signing is None:
            return None
        return signing.type or "main"

    def generate_package_for(self, ptype):
        """
        Returns the package-type of the package for which ``ptype`` is a signing
        producer, if any.  That is the package which consumes the signable material
        which ``ptype`` produces.

        :param ptype:
            package-type of the package to examine.
        :return:
            package-type of our signing consumer.
            ``None`` if ``ptype`` is not a signing producer.
        """
        pkg = self.source.lookup_package(type=ptype)
        if pkg is None:
            return None
        generate = pkg.signing_to
        if generate is None:
            return None
        return generate.type or "main"

    def prereq_package_for(self, ptype):
        """
        Returns the package-type of the package which ``ptype`` follows in
        the build sequence, if any.

        :param ptype:
            package-type of the package to examine.
        :return:
            package-type of our prereq package.
            ``None`` if ``ptype`` is a top-level package.
        """
        pkg = self.source.lookup_package(type=ptype)
        if pkg is None:
            return None
        prereq = pkg.depends
        if prereq is None:
            return None
        return prereq.type or "main"

    def prereq_key(self, ptype):
        """
        Returns a sorting key representing the order in which packages are
        built.  This is determined from the prereq chain.

        :param ptype:
            package-type of the package to generate the key.
        :return:
            list of package-types for our entire prereq chain, top to bottom.
        """
        pkg = ptype
        key = []
        while pkg is not None:
            key.insert(0, pkg)
            pkg = self.prereq_package_for(pkg)
        return key

    def adjunct_package(self, ptype):
        """
        Returns a boolean indicating if ``ptype`` is an adjunct package.  That is
        an embargoed package which should only be expressed in private archives.
        For example the linux-restricted-generate packages.

        :param ptype:
            package-type of the package to examine.
        :return:
            boolean indicating if ``ptype`` is an adjunct package
        """
        pkg = self.source.lookup_package(type=ptype)
        if pkg is None:
            return None
        return pkg.adjunct

    # __determine_build_status
    #
    def __determine_build_status(s):
        center('Sources::__determine_build_status')

        s._cache = {}
        s._builds = {}

        cinfo('')
        cinfo('Build Status:', 'cyan')

        for dep in iter(s.pkgs):
            cdebug('')
            cinfo('%s: ' % dep, 'blue')
            cinfo('--------------------------------------------------------------------------------', 'blue')
            if dep in s._cache:
                break
            Clog.indent += 4

            # Lookup the package version we are expecting -- if we have it match on explicit version.
            version = s.package_version(dep)
            cinfo("APW: package_version({}) = {}".format(dep, version))
            if version is not None:
                abi = None
                sloppy = False

            # For the linux and linux-signed packages the versions must be an exact match for the other
            # packages only the abi needs to match the linux packages abi number.
            #
            elif dep in ['lbm', 'meta', 'ports-meta'] and s.abi:
                abi = s.abi
                version = s.kernel
                sloppy = True

            else:
                abi = None
                version = s.version
                sloppy = True

            cinfo("{} {} abi={} sloppy={}".format(s.pkgs[dep], version, abi, sloppy))

            s._cache[dep] = {}
            s._builds[dep] = {}
            if not s.bug.is_development_series:
                cdebug('Stable Package', 'cyan')
                cdebug('')
                scan_pockets = ['ppa', 'Signing', 'Proposed', 'as-proposed', 'Security', 'Updates']
            else:
                cdebug('Development Package', 'cyan')
                cdebug('')
                scan_pockets = ['ppa', 'Signing', 'Proposed', 'as-proposed', 'Release']
            s.scan_pockets = list(scan_pockets)
            scan_pockets[0] = 'build' if not s.adjunct_package(dep) else 'build-private'

            for pocket in scan_pockets:
                pocket_from = pocket
                if pocket_from not in s._routing:
                    continue
                if s._routing[pocket_from] is None:
                    s.bug.overall_reason = "{} pocket routing archive specified but invalid {}".format(pocket_from, s.source)
                    cwarn(s.bug.overall_reason)
                    continue

                s._cache[dep][pocket] = PackageBuild(s.bug, s.distro_series, dep, pocket_from, s._routing[pocket_from], s.pkgs[dep], version, abi, sloppy)
                s._builds[dep][pocket] = PackageBuildRoute(s.distro_series, dep, pocket_from, s._routing[pocket_from], s.pkgs[dep], bug=s.bug)
                if pocket == scan_pockets[0]:
                    s._cache[dep]['ppa'] = s._cache[dep][pocket]
                    s._builds[dep]['ppa'] = s._builds[dep][pocket]
                #cinfo('%-8s : %-5s / %-10s    (%s : %s) %s [%s %s]' % (pocket, info[0], info[5], info[3], info[4], info[6], src_archive.reference, src_pocket), 'cyan')
            Clog.indent -= 4

        # Scan across the build locations and dertermine if we see an upload in an appropriate
        # version.  Use this to set the built_in if we don't have one.
        built_in = None
        for pkg in s.pkgs:
            package_published = s.builds[pkg]["ppa"].version_match(exact=s.bug.version, limit_stream=s.bug.built_in)
            if package_published is None:
                if pkg == "lbm":
                    version_sloppy = s.bug.kernel + "-" + s.bug.abi + "."
                elif pkg in ("meta", "ports-meta"):
                    version_sloppy = s.bug.kernel + "." + s.bug.abi + "."
                else:
                    version_sloppy = s.bug.version + "+"
                package_published = s.builds[pkg]["ppa"].version_match(prefix=version_sloppy, limit_stream=s.bug.built_in)
            if package_published is not None:
                cinfo("APW: NEW package_version found {} in {} ({}#{})".format(package_published.version, package_published.reference, package_published.route_name, package_published.route_entry))
                cinfo("APW: NEW package_version monitors={}".format(package_published.monitors))
                if s.bug.bprops.get("versions", {}).get(pkg) is None and s.ancillary_package_for(pkg) is None:
                    cinfo("APW: NEW package_version found {} in {} ({}#{}) -- setting".format(package_published.version, package_published.reference, package_published.route_name, package_published.route_entry))
                    s.bug.bprops.setdefault('versions', {})[pkg] = package_published.version
                    if built_in is False:
                        pass
                    elif built_in is None:
                        built_in = package_published.route_entry
                    elif package_published.route_entry != built_in:
                        cwarn("APW: NEW package_version built_in={} != {}".format(built_in, package_published.route_entry))
        if built_in is not None and built_in is not False:
            s.bug.built_in = built_in

        #cdebug('')
        #cdebug('The Cache:', 'cyan')
        #for d in sorted(s._cache):
        #    cdebug('    %s' % d, 'cyan')
        #    for p in sorted(s._cache[d]):
        #        cdebug('        %-8s : %-5s   (%s)' % (p, s._cache[d][p]['built'], date_to_string(s._cache[d][p]['published'])), 'cyan')

        cleave('Sources::__determine_build_status')
        return None

    def __all_arches_built(s, matches):
        '''
        Determine if all the builds that have been done for all of the arches. This helps
        us detect when a build has been canceled.
        '''
        center(s.__class__.__name__ + '__all_arches_built')
        retval = False
        if len(matches) > 0:
            for match in matches:
                binary_list = match.getPublishedBinaries()

                # Determine how many arches we have builds for.
                #
                sa = {} # series arches
                for binary in binary_list:
                    if binary.architecture_specific:
                        try:
                            sa[binary.distro_arch_series_link] += 1
                        except KeyError:
                            sa[binary.distro_arch_series_link] = 1
                for arch in sa:
                    cdebug('series/arch : %s' % arch)

                arches_to_build = len(sa)

                # Determine how many builds there actually are. This includes
                # canceled builds which are important to us.
                #
                builds = match.getBuilds()

                if arches_to_build == len(builds):
                    retval = True
                else:
                    cdebug('Only %s of %s arches were built' % (len(builds), arches_to_build))
        else:
            cdebug('No matches found')
        cleave(s.__class__.__name__ + '__all_arches_built (%s)' % retval)
        return retval

    __states_present = ['DEPWAIT', 'BUILDING', 'FULLYBUILT', 'PENDING', 'QUEUED', 'SUPERSEDED', 'FAILEDTOBUILD']
    __pockets_uploaded = ('ppa', 'Signing', 'Proposed', 'Security', 'Updates', 'Release')
    __pockets_signed = ('Proposed', 'Security', 'Updates', 'Release')

    # build_info
    #
    @property
    def build_info(s):
        if s._cache is None:
            s.__determine_build_status()
        return s._cache

    # builds
    #
    @property
    def builds(self):
        if self._builds is None:
            self.__determine_build_status()
        return self._builds

    # srcs
    #
    @property
    def srcs(s):
        if s._cache is None:
            s.__determine_build_status()
        return s._cache

    # legacy_info
    #
    @property
    def legacy_info(s):
        if s._cache is None:
            s.__determine_build_status()
        return s._cache

    # pkgs_qualified
    #
    @property
    def pkgs_qualified(s):
        '''
        Put together a list of all the packages that depend on this package.
        '''
        if 'packages' not in s.bug.bprops:
            pkgs = {}
            series = s.kernel_series.lookup_series(codename=s.series)
            source = series.lookup_source(s.name)
            if source is None:
                return None
            for package in source.packages:
                pkgs[package.type if package.type else 'main'] = package.name
            s.bug.bprops['packages'] = pkgs

        retval = {}
        for package_type, package_name in sorted(s.bug.bprops['packages'].items()):
            if s.bug.task_status(s.__pkg_task(package_type)) != 'Invalid':
                retval[package_type] = package_name

        return retval

    # dependent_packages
    #
    def dependent_packages(self):
        return sorted(self.builds.keys())

    # dependent_packages_for_pocket
    #
    def dependent_packages_for_pocket(self, pocket):
        pkgs = []
        for pkg in self.dependent_packages():
            if self.generate_package_for(pkg) is not None and pocket not in ('ppa', 'build-private', 'Signing'):
                continue
            pkgs.append(pkg)
        cdebug("dependent_packages_for_pocket({})={}".format(pocket, pkgs))
        return pkgs

    # distro_series
    #
    @property
    def distro_series(s):
        '''
        Return the LP distro series link to the series associated with this version
        of this package.
        '''
        if s.__distro_series is None:
            if s.series:
                sc = s.lp.distributions["ubuntu"].series_collection
                for ds in sc:
                    if ds.name == s.series:
                        s.__distro_series = ds
                        break

            if s.__distro_series is None:
                emsg = "        ERROR: can't figure out the distro series for %s-%s\n" % (s.name, s.version)
                cerror(emsg)
                raise ErrorExit(emsg)

        return s.__distro_series

    # built_and_in_pocket
    #
    def built_and_in_pocket(s, pkg, pocket):
        '''
        Dependent package is fully built and in the pocket 'pocket'.
        '''
        center(s.__class__.__name__ + '.built_and_in_pocket')
        pkg_built = s.__pkg_built(pkg, pocket)
        if not pkg_built:
            cinfo('        {} is either not fully built yet or not in {}.'.format(pkg, pocket), 'red')

        cleave(s.__class__.__name__ + '.built_and_in_pocket ({})'.format(pkg_built))
        return pkg_built

    # built_and_in_pocket
    #
    def built_and_in_pocket_or_after(s, pkg, pocket):
        '''
        Dependent package is fully built and in the pocket 'pocket'.
        '''
        center(s.__class__.__name__ + '.built_and_in_pocket_or_after')
        found_start = False
        for find_pocket in s.scan_pockets:
            if find_pocket == pocket:
                found_start = True
            if not found_start:
                continue

            pkg_built = s.__pkg_built(pkg, find_pocket)
            if pkg_built:
                break

        if not pkg_built:
            cinfo('        {} is either not fully built yet or not in {} or after.'.format(pkg, pocket), 'red')

        cleave(s.__class__.__name__ + '.built_and_in_pocket_or_after ({})'.format(pkg_built))
        return pkg_built

    # all_in_pocket
    #
    @centerleaveargs
    def all_in_pocket(self, pocket):
        found = True
        for pkg in s.pkgs:
            package_published = None
            package_version = self.package_version_exact(pkg)
            if package_version is not None:
                package_published = s.builds[pkg][pocket].version_match(exact=package_version, limit_stream=s.bug.built_in)
            if package_published is None:
                found = False
            cdebug("all_in_pocket({}) {} {}".format(pocket, pkg, "Missing" if package_published is None else "Present"))
        return found

    # __pockets_from
    #
    def __pockets_from(s, pocket_from):
        pockets = []
        found_from = False
        for pocket_next in s.scan_pockets:
            if pocket_next == pocket_from:
                found_from = True
            if found_from:
                pockets.append(pocket_next)
        return pockets

    # pocket_after
    #
    def pocket_after(s, pocket_from):
        pockets = s.__pockets_from(pocket_from)
        if len(pockets) < 2:
            return None
        return pockets[1]

    # __pkg_in
    #
    def __pkg_in(self, pkg, pocket):
        build_route_entry = self.__pkg_pocket_route_entry(pkg, pocket)
        if build_route_entry is None:
            return False
        return True

    # __pkg_built
    #
    def __pkg_built(self, pkg, pocket):
        build_route_entry = self.__pkg_pocket_route_entry(pkg, pocket)
        if build_route_entry is None:
            return False
        if not build_route_entry.built:
            return False
        return True

    # __pkg_pocket_route_entry
    #
    def __pkg_pocket_route_entry(self, pkg, pocket, exact_match=True):
        package_version = None
        if exact_match:
            package_version = self.package_version_exact(pkg)
            if package_version is None:
                return None
        build_route = self.builds.get(pkg, {}).get(pocket)
        if not build_route:
            return None
        build_route_entry = build_route.version_match(exact=package_version, limit_stream=self.bug.built_in)
        return build_route_entry

    build_route_entry = __pkg_pocket_route_entry

    # __pkg_task
    #
    def __pkg_task(s, pkg):
        if pkg == 'main':
            suffix = ''
        else:
            suffix = '-' + pkg
        return 'prepare-package' + suffix

    # delta_src_dst
    #
    def delta_src_dst(s, src, dst, pair_signing=False):
        '''
        List of dependent packages in src which are not in dst or later.
        '''
        center(s.__class__.__name__ + '.delta_src_dst({}, {})'.format(src, dst))

        retval = []
        for pkg in s.dependent_packages_for_pocket(dst):
            pkg_in_dst = None
            pkg_in_src = s.__pkg_in(pkg, src)
            pocket = dst
            for pocket in s.__pockets_from(dst):
                pkg_in_dst = s.__pkg_built(pkg, pocket)
                if pkg_in_dst:
                    break

            if pkg_in_src and not pkg_in_dst:
                cinfo('        {} is in {} and not yet in {} or later.'.format(pkg, src, dst), 'red')
                retval.append(pkg)

            elif src == 'ppa' and s.bug.task_status(s.__pkg_task(pkg)) not in ('Fix Released', 'Invalid'):
                cinfo('        {} is missing from {} or later.'.format(pkg, src), 'red')
                retval.append(pkg)

            else:
                cinfo('        {} is in {} and in {}'.format(pkg, src, pocket), 'red')

        # If we are missing a signing consumer ensure the signing provider is included
        # as we are unable to build the latter without the former.
        if pair_signing:
            for pkg in retval:
                signing_for = s.signing_package_for(pkg)
                if signing_for is not None and signing_for not in retval:
                    cdebug("{} not in delta, added for ppa".format(signing_for))
                    retval.append(signing_for)

        cinfo("from {} to {} delta {}".format(src, dst, retval))

        cleave(s.__class__.__name__ + '.delta_src_dst(...)={}'.format(retval))
        return retval

    # delta_in_pocket
    #
    def delta_in_pocket(s, delta, pocket):
        '''
        Are all of the packages in delta in pocket.
        '''
        center(s.__class__.__name__ + '.delta_in_pocket({}, {})'.format(delta, pocket))

        retval = True
        for pkg in delta:
            pkg_in = s.__pkg_in(pkg, pocket)
            if not pkg_in:
                cinfo('        {} is not in {}'.format(pkg, pocket), 'red')
                retval = False
                break

        cleave(s.__class__.__name__ + '.delta_in_pocket(...)={}'.format(retval))
        return retval

    # delta_built_pocket
    #
    def delta_built_pocket(s, delta, pocket):
        '''
        Are all of the packages in delta built in pocket.
        '''
        center(s.__class__.__name__ + '.delta_built_pocket({}, {})'.format(delta, pocket))

        retval = True
        for pkg in delta:
            pkg_in = s.__pkg_built(pkg, pocket)
            if not pkg_in:
                cinfo('        {} is not built in {}'.format(pkg, pocket), 'red')
                retval = False
                break

        cleave(s.__class__.__name__ + '.delta_built_pocket(...)={}'.format(retval))
        return retval

    # delta_record
    def delta_record(s, which, pocket_src, pocket_dest):
        delta = s.delta_src_dst(pocket_src, pocket_dest, pair_signing=pocket_src == "ppa")
        s.bug.bprops.setdefault('delta', {})[which] = delta

    # all_built_and_in_pocket
    #
    def all_built_and_in_pocket(s, pocket):
        '''
        All dependent packages are fully built and in the pocket 'pocket'.
        '''
        center(s.__class__.__name__ + '.all_built_and_in_pocket')
        retval = True

        for pkg in s.dependent_packages_for_pocket(pocket):
            pkg_built = s.__pkg_built(pkg, pocket)
            if not pkg_built:
                cinfo('        {} is either not fully built yet or not in {}.'.format(pkg, pocket), 'red')
                retval = False
                break

        cleave(s.__class__.__name__ + '.all_built_and_in_pocket ({})'.format(retval))
        return retval

    # all_built_and_in_pocket_or_after
    #
    def all_built_and_in_pocket_or_after(s, pocket):
        '''
        All dependent packages are fully built and in the pocket 'pocket'.
        '''
        center(s.__class__.__name__ + '.all_built_and_in_pocket_or_after')
        retval = True

        for pkg in s.dependent_packages_for_pocket(pocket):
            if not s.built_and_in_pocket_or_after(pkg, pocket):
                cinfo('        {} is either not fully built yet or not in {} or after.'.format(pkg, pocket), 'red')
                retval = False
                break

        cleave(s.__class__.__name__ + '.all_built_and_in_pocket_or_after ({})'.format(retval))
        return retval

    # all_built_and_in_pocket_or_pocket
    #
    def all_built_in_src_dst(s, src, dst):
        '''
        All dependent packages are fully built and in src or dst.
        '''
        center(s.__class__.__name__ + '.all_built_in_src_dst')
        retval = True

        for pkg in s.dependent_packages_for_pocket(dst):
            pkg_built_src = s.__pkg_built(pkg, src)
            pkg_built_dst = s.__pkg_built(pkg, dst)
            if not pkg_built_src and not pkg_built_dst:
                cinfo('        {} is either not fully built yet or not in {} or {}.'.format(pkg, src, dst), 'red')
                retval = False
                break

        cleave(s.__class__.__name__ + '.all_built_in_src_dst ({})'.format(retval))
        return retval

    @centerleave
    def any_superseded_in_pocket(self, pocket):
        '''
        An dependent packages have Superseded binaries in pocket 'pocket'.
        '''
        for pkg in self.dependent_packages_for_pocket(pocket):
            pocket_route_entry = self.__pkg_pocket_route_entry(pkg, pocket)
            if pocket_route_entry is None:
                cdebug("{} is missing".format(pkg))
            elif pocket_route_entry.status == "SUPERSEDED":
                return True
        return False

    # all_built_in_src_dst_detail
    #
    @centerleaveargs
    def all_built_in_src_dst_detail(self, src, dst):
        '''
        Why dependent packages are not fully built and in src or dst.
        '''
        detail = []
        for pkg in self.dependent_packages_for_pocket(dst):
            package_version = self.package_version_exact(pkg)
            if package_version is None:
                return None
            pocket_route_entry = self.builds[pkg][src].version_match(exact=package_version, limit_stream=self.bug.built_in)
            if pocket_route_entry is None:
                pocket_route_entry = self.builds[pkg][dst].version_match(exact=package_version, limit_stream=self.bug.built_in)
            if pocket_route_entry is None:
                detail.append("{} is missing".format(pkg))
            else:
                detail += pocket_route_entry.status_detail
        return detail

    # built_in_src_dst_delta
    #
    def built_in_src_dst_delta(s, src, dst):
        '''
        List of dependent packages in src which are not in dst.
        '''
        center(s.__class__.__name__ + '.built_in_src_dst_delta')
        retval = []

        for pkg in s.dependent_packages_for_pocket(dst):
            pkg_built_src = s.__pkg_built(pkg, src)
            pkg_built_dst = s.built_and_in_pocket_or_after(pkg, dst)
            if pkg_built_src and not pkg_built_dst:
                cinfo('        {} is in {} and not yet in {} or later.'.format(pkg, src, dst), 'red')
                retval.append(pkg)

        cleave(s.__class__.__name__ + '.built_in_src_dst_delta ({})'.format(retval))
        return retval

    # all_built_and_in_pocket_for
    #
    def all_built_and_in_pocket_for_old(s, pocket, period):
        '''
        Check if we are fully built in a specific pocket and have been there
        for at least period time.
        '''
        center(s.__class__.__name__ + '.all_built_and_in_pocket_for({}, {})'.format(pocket, period))
        retval = False
        if s.all_built_and_in_pocket_or_after(pocket):

            # Find the most recent date of either the publish date/time or the
            # date/time of the last build of any arch of any of the dependent
            # package.
            #
            date_available = None
            bi = s.legacy_info
            for d in sorted(bi):
                if bi[d][pocket]['published'] is None:
                    continue
                if bi[d][pocket]['most_recent_build'] is None:
                    continue

                if bi[d][pocket]['published'] > bi[d][pocket]['most_recent_build']:
                    if date_available is None or bi[d][pocket]['published'] > date_available:
                        date_available = bi[d][pocket]['published']
                else:
                    if date_available is None or bi[d][pocket]['most_recent_build'] > date_available:
                        date_available = bi[d][pocket]['most_recent_build']

            now = datetime.now(timezone.utc)
            if date_available is None:
                date_available = now
            date_available = date_available.replace(tzinfo=timezone.utc)
            comp_date = date_available + period
            if comp_date <= now:
                retval = True
            else:
                cinfo('It has been less than {} since the last package was either published or built in {}'.format(period, pocket))
                cinfo('    target: %s' % comp_date)
                cinfo('       now: %s' % now)

                # Record when it makes sense to check again.
                s.bug.refresh_at(comp_date, 'package publication to {} for {}'.format(pocket, period))

        return retval

    @centerleaveargs
    def all_built_and_in_pocket_for_new(s, pocket, period):
        retval = False
        if s.all_built_and_in_pocket_or_after(pocket):
            # Find the most recent date of either the published date/time or the
            # date/time of the last build on any arch for any package.
            date_available = None
            for pkg in s.dependent_packages_for_pocket(pocket):
                build_route_entry = s.__pkg_pocket_route_entry(pkg, pocket)
                if build_route_entry is None:
                    continue
                if build_route_entry.published is not None:
                    if date_available is None or build_route_entry.published > date_available:
                        date_available = build_route_entry.published
                if build_route_entry.latest_build is not None:
                    if date_available is None or build_route_entry.latest_build > date_available:
                        date_available = build_route_entry.latest_build

            now = datetime.now(timezone.utc)
            if date_available is None:
                date_available = now
            date_available = date_available.replace(tzinfo=timezone.utc)
            comp_date = date_available + period
            if comp_date <= now:
                retval = True
            else:
                cinfo('It has been less than {} since the last package was either published or built in {}'.format(period, pocket))
                cinfo('    target: %s' % comp_date)
                cinfo('       now: %s' % now)

                # Record when it makes sense to check again.
                ##s.bug.refresh_at(comp_date, 'package publication to {} for {}'.format(pocket, period))

        return retval

    def all_built_and_in_pocket_for(s, pocket, period):
        old = s.all_built_and_in_pocket_for_old(pocket, period)
        new = s.all_built_and_in_pocket_for_new(pocket, period)
        cinfo("PRv5: all_built_and_in_pocket_for({}, {}) = {} -> {}".format(pocket, period, old, new))
        return old

    # attempt_retry_logless
    #
    def attempt_retry_logless(s, pkg):
        retried = False
        for maint in s.bug.maintenance:
            if maint['type'] == 'deb-build' and maint['detail']['type'] == pkg:
                # If we have a maintenance record and it is in 'Failed to build'
                # and we have no log then this is a clear retry candidate.
                if (maint is not None and
                        maint['detail']['state'] == 'Failed to build' and
                        maint['detail']['log'] is None):
                    cinfo("RETRY: {} (logless failure)".format(maint['detail']['lp-api']))
                    if s.attempt_retry(pkg):
                        retried = True
        return retried

    # attempt_retry
    #
    def attempt_retry(s, pkg):
        retried = False
        for record in s.bug.maintenance:
            if record['type'] == 'deb-build' and record['detail']['type'] == pkg:
                cinfo("RETRY: {}".format(record['detail']['lp-api']))
                lp_build = s.lp.load(record['detail']['lp-api'])
                if lp_build is None:
                    cinfo("RETRY: {} build not found".format(
                        record['detail']['lp-api']))
                elif not lp_build.can_be_retried:
                    cinfo("RETRY: {} not retryable (state={})".format(
                        record['detail']['lp-api'], lp_build.buildstate))
                    # If this is not retryable but is in progress now,
                    # so just behave as if we retried it.
                    if lp_build.buildstate in (
                        "Needs building",
                        "Currently building",
                        "Gathering build output",
                        "Uploading build",
                    ):
                        retried = True
                else:
                    try:
                        lp_build.retry()
                        retried = True
                        cinfo("RETRY: {} retry successful".format(
                            record['detail']['lp-api']))
                    except Unauthorized as e:
                        cinfo("RETRY: {} retry unsuccessful -- marked manual-retry".format(
                            record['detail']['lp-api']))
                        record['detail']['manual-retry'] = True
        return retried

    # all_failures_in_pocket
    #
    def all_failures_in_pocket(s, pocket, ignore_all_missing=False):
        packages = s.dependent_packages_for_pocket(pocket)
        return s.delta_failures_in_pocket(packages, pocket, ignore_all_missing)

    def __prereq_completed(self, prereq, pocket):
        pocket_route = self.__pkg_pocket_route_entry(prereq, pocket)
        if pocket_route is None:
            return None
        published = pocket_route.published
        built = pocket_route.latest_build
        if published is None:
            return built
        if built is None:
            return published
        if built > published:
            return built
        return published

    # __pkg_state
    #
    def __pkg_state(self, pkg, pocket):
        package_version = self.package_version_exact(pkg)
        if package_version is None:
            return None
        pocket_route_entry = self.builds[pkg][pocket].version_match(exact=package_version, limit_stream=self.bug.built_in)
        if pocket_route_entry is None:
            return None
        return pocket_route_entry.status

    # delta_failures_in_pocket
    #
    def delta_failures_in_pocket(s, delta, pocket, ignore_all_missing=False):
        failures = {}
        missing = 0
        sources = 0
        for pkg in delta:
            sources += 1
            status = s.__pkg_state(pkg, pocket)
            if status in (None, ''):
                failures.setdefault('missing', []).append(pkg)
                missing += 1
            elif status == 'BUILDING':
                failures.setdefault('building', []).append(pkg)
            elif status in ('DEPWAIT', 'FAILEDTOBUILD'):
                real_status = 'depwait' if status == 'DEPWAIT' else 'failed'
                wait_status = 'depwait' if status == 'DEPWAIT' else 'failwait'

                # Check if we failed without a log, if so, hit retry regardless
                # or any prereq existance.
                if status == 'FAILEDTOBUILD':
                    # If we successfully retried it then we should report it as
                    # building.
                    if s.attempt_retry_logless(pkg):
                        failures.setdefault('building', []).append(pkg)
                        continue

                # Look up the dependancy chain looking for something which
                # can be retried.
                active_prereq = pkg
                while True:
                    previous_prereq = active_prereq
                    active_prereq = s.prereq_package_for(active_prereq)
                    if active_prereq is None:
                        break
                    active_prereq_state = s.__pkg_state(active_prereq, pocket)
                    if active_prereq_state not in ('DEPWAIT', 'FAILEDTOBUILD'):
                       break

                # If there is nothing above us doing anything.  Then our status
                # is real.
                if active_prereq is None:
                    failures.setdefault(real_status, []).append(pkg)
                    continue

                # If the active prereq is incomplete then we should continue
                # waiting for it.
                if active_prereq_state != 'FULLYBUILT':
                    failures.setdefault(wait_status, []).append(pkg)
                    continue

                # Work out if the previous_prereq is retryable.
                previous_prereq_completed = s.__prereq_completed(previous_prereq, pocket)
                active_prereq_completed = s.__prereq_completed(active_prereq, pocket)
                cinfo("completions {} => {} {} -> {} {}".format(pkg, previous_prereq_completed, previous_prereq, active_prereq, active_prereq_completed))
                previous_prereq_retry = (
                        previous_prereq_completed is not None and
                        active_prereq_completed is not None and
                        previous_prereq_completed - timedelta(hours=2) <= active_prereq_completed)

                # If the previous_prereq is actually us and can be retried
                # actually attempt it.
                if previous_prereq_retry and previous_prereq == pkg:
                    # If the retry fails this requirs a manual retry,
                    # mark us and annotate the maintenance record.
                    if not s.attempt_retry(pkg):
                        failures.setdefault('retry-needed', []).append(pkg)

                    # If it works it should end up in Needs Building state
                    # which implies we should report it as :building.
                    else:
                        failures.setdefault('building', []).append(pkg)

                    # Otherwise we made progress, so no mark is needed.
                    continue

                # If the previous_prereq can be retried, assume it will
                # elsewhere in the pass.  Mark ourselves as waiting.
                if previous_prereq_retry:
                    failures.setdefault(wait_status, []).append(pkg)

                # Otherwise we are genuinely broken.
                else:
                    failures.setdefault(real_status, []).append(pkg)

            elif status == 'PENDING':
                failures.setdefault('pending', []).append(pkg)
            elif status == 'QUEUED':
                failures.setdefault('queued', []).append(pkg)
            elif status == 'SUPERSEDED':
                failures.setdefault('superseded', []).append(pkg)

        if ignore_all_missing and sources == missing:
            failures = None

        return failures

    # failures_to_text
    #
    def failures_to_text(self, summary):
        type_state = {}
        for state, members in summary.items():
            state_text = {
                    'missing': 'M',
                    'queued': 'Q',
                    'pending': 'P',
                    'building': 'B',
                    'depwait': 'D',
                    'retry-needed': 'R',
                    'failwait': 'D*',
                    'failed': 'F',
                    'superseded': 'S',
                }.get(state, state)
            for member in members:
                type_state[member] = state_text
        bits = []
        #for state, members in sorted(summary.items()):
        #    members = sorted(members, key=self.prereq_key)
        #    bits.append(','.join(members) + ':' + state)
        for member in sorted(type_state, key=self.prereq_key):
            bits.append("{}:{}".format(member, type_state[member]))
        cdebug("failures_to_text: {} -> {}".format(summary, bits))
        return ' '.join(bits)

    # creator
    #
    @centerleaveargs
    def creator(self, pkg, pocket=None):
        if pocket is None:
            pockets = self.__pockets_uploaded
        else:
            pockets = [pocket]
        for pocket in pockets:
            pocket_route = self.__pkg_pocket_route_entry(pkg, pocket)
            if pocket_route is not None:
                return pocket_route.creator
        return None

    # signer
    #
    @centerleaveargs
    def signer(self, pkg, pocket=None):
        if pocket is None:
            pockets = self.__pockets_uploaded
        else:
            pockets = [pocket]
        for pocket in pockets:
            pocket_route = self.__pkg_pocket_route_entry(pkg, pocket)
            if pocket_route is not None:
                return pocket_route.signer
        return None

    def changes_data(self, url):
        """
        Return the changes file contents located at ``url``.

        :param url:
            the URL from which we should fetch the changes file
        :return:
            list of changes file lines
            ``None`` no changes file was found at ``url``
        :raises:
            ``WorkflowCrankError`` on librarian errors
        """
        try:
            url = url.replace('https://launchpad.net/', 'https://api.launchpad.net/devel/')
            changes = self.lp._browser.get(url)
            return changes.decode('utf-8').rstrip().split('\n')
        except NotFound:
            cdebug("changes_data: NotFound")
            pass
        except Unauthorized:
            cdebug("changes_data: Unauthorized")
            pass
        except ServerError:
            raise WorkflowCrankError("launchpad librarian unavailable")
        except HTTPError as e:
            if e.args[0] != 403:
                raise WorkflowCrankError("launchpad librarian unavailable ({})".format(e.args[0]))
        return None

    # bugs
    #
    def bugs_old(self):
        center(self.__class__.__name__ + '.bugs')

        # If we have no version, we can have no build, if we have no build we 
        # do not know what bugs we have.
        if self.version is None:
            return None

        # Find an upload record for the main package.
        changes_url = None
        bugs = None
        pkg = 'main'
        for pocket in self.__pockets_uploaded:
            package_version = self.package_version_exact(pkg)
            if package_version is None:
                continue
            build_route = self.builds.get(pkg, {}).get(pocket)
            if build_route is None:
                continue
            build_route_entry = build_route.version_match(exact=package_version, limit_stream=self.bug.built_in)
            if build_route_entry is None:
                continue
            changes_url = build_route_entry.changes_url
            if changes_url is None:
                continue

            cdebug("BUGS: CHANGES: url={}".format(changes_url))
            changes_data = self.changes_data(changes_url)
            if changes_data is None:
                continue

            for line in changes_data:
                if line.startswith('Launchpad-Bugs-Fixed:'):
                    bugs = line.split(' ')[1:]
            break

        cleave(self.__class__.__name__ + '.bugs {}'.format(bugs))
        return bugs

    @centerleaveargs
    def bugs_new(self):
        # If we have no version, we can have no build, if we have no build we 
        # do not know what bugs we have.
        if self.version is None:
            return None

        # Find an upload record for the main package.
        changes_url = None
        bugs = None
        pkg = 'main'
        for pocket in self.__pockets_uploaded:
            package_version = self.package_version_exact(pkg)
            if package_version is None:
                continue
            build_route = self.builds.get(pkg, {}).get(pocket)
            if build_route is None:
                continue
            build_route_entry = build_route.version_match(exact=package_version, limit_stream=self.bug.built_in)
            if build_route_entry is None:
                continue
            changes_url = build_route_entry.changes_url
            if changes_url is None:
                continue

            cdebug("BUGS: CHANGES: url={}".format(changes_url))
            changes_data = self.changes_data(changes_url)
            if changes_data is None:
                continue

            updates_version = None
            updates_route = self.builds.get(pkg, {}).get("Updates")
            if updates_route is not None:
                updates_route_entry = updates_route.version_match(limit_stream=self.bug.built_in)
                if updates_route_entry is not None:
                    updates_version = updates_route_entry.version

            #cinfo("APW: bugs_since build={} updates={}".format(build_route_entry.version, updates_version))

            version_re = re.compile(r"\(([^\)]+)\)")
            bug_re = re.compile(r"LP: *#([0-9]+)")
            in_changes = False
            bugs = []
            bugs_version = None
            bugs_fallback = []
            version = None
            for line in changes_data:
                if line.startswith('Launchpad-Bugs-Fixed:'):
                    bugs_fallback = line.split(' ')[1:]
                if len(line) > 0 and line[0] != " ":
                    in_changes = False
                if line.startswith("Changes:"):
                    in_changes = True
                if in_changes:
                    if len(line) > 1 and line[1] not in (" ", "."):
                        match = version_re.search(line)
                        #cinfo("BUGS: match={}".format(match))
                        #if match:
                        #    cinfo("BUGS: match={} group(1)={} version={}".format(match, match.group(1), updates_version))
                        if match and match.group(1) == updates_version:
                            bugs_version = list(bugs)
                    for match in bug_re.finditer(line):
                        bugs.append(match.group(1))
            cinfo("BUGS: bugs_version={}".format(bugs_version))
            return bugs_version if bugs_version is not None else bugs_fallback
        return None

    @property
    def bugs(self):
        old = self.bugs_old()
        new = self.bugs_new()
        cinfo("BUGSv1: bugs = {} -> {}".format(old, new))

        return new

    # prerequisite_packages
    #
    @centerleave
    def prerequisite_packages(self):
        """
        Return a list of failed prerequisite debian packages.

        :returns:
            list of errors for any known prerequisite package which is not
            in the -updates pocket, an empty list indicates success
        """
        prereq_re = re.compile(r"^ *(\S+) +\(= +(\S+)\) *$")

        # If we have no version, we can have no build, if we have no build we 
        # do not know what bugs we have.
        if self.version is None:
            return None

        # Find an upload record for the lrm package.
        pkg = 'lrm'
        prereqs = []
        for pocket in self.__pockets_uploaded:
            package_version = self.package_version_exact(pkg)
            if package_version is None:
                continue
            build_route = self.builds.get(pkg, {}).get(pocket)
            if build_route is None:
                continue
            build_route_entry = build_route.version_match(exact=package_version, limit_stream=self.bug.built_in)
            if build_route_entry is None:
                continue
            changes_url = build_route_entry.changes_url
            if changes_url is None:
                continue

            cdebug("PREREQ-PKGS: CHANGES: url={}".format(changes_url))
            changes_data = self.changes_data(changes_url)
            if changes_data is None:
                continue

            #cdebug("PREREQ-PKGS: CHANGES: data={}".format(changes_data))
            prereq_data = None
            for line in changes_data:
                if line.startswith("Ubuntu-Nvidia-Dependencies:"):
                    prereq_data = ""
                    continue
                if prereq_data is None:
                    continue
                if line[0] != " ":
                    break
                prereq_data = prereq_data + line.rstrip()
            cdebug("PREREQ-PKGS: CHANGES: prereq={}".format(prereq_data))
            if prereq_data is not None:
                for prereq in prereq_data.split(","):
                    match = prereq_re.match(prereq)
                    if not match:
                        continue
                    prereqs.append((match.group(1), match.group(2)))
            break

        if self.bug.is_development_series:
            pockets = ['Release']
        else:
            pockets = ['Updates', 'Release']
        failures = []
        for package, version in prereqs:
            for pocket in pockets:
                route = self._routing.get(pocket)
                if route is None:
                    cinfo("{}/{} package has no {} route data".format(package, version, pocket))
                    continue
                build_route = PackageBuildRoute(self.distro_series, "adhoc", pocket, self._routing[pocket], package, bug=self.bug)
                if build_route is None:
                    cinfo("{}/{} package has no {} route".format(package, version, pocket))
                    continue
                #build_route_entry = build_route.version_match(exact=version, limit_stream=self.bug.built_in)
                build_route_entry = build_route.version_match() # ANY
                cinfo("{}/{} package found version={}".format(package, build_route_entry, build_route_entry.version if build_route_entry is not None else None))
                if (
                    build_route_entry is not None
                    and build_route_entry.version is not None
                    and package.startswith("nvidia-graphics-drivers-")
                ):
                    version_prefix = version.split("-")[0]
                    build_prefix = build_route_entry.version.split("-")[0]
                    if version_prefix != build_prefix:
                        failures.append("{}/{} version ABI missmatch".format(package, version, pocket))
                        cinfo("{}/{} package ABI missmatch in {} route {}".format(package, version, pocket, build_route_entry.version))
                        break

                elif (
                    build_route_entry is not None
                    and build_route_entry.version is not None
                    and build_route_entry.version != version
                ):
                    failures.append("{}/{} version missmatch".format(package, version, pocket))
                    cinfo("{}/{} package missmatch in {} route {}".format(package, version, pocket, build_route_entry.version))
                    break
                else:
                    cinfo("{}/{} package not found in {} route".format(package, version, pocket))
                    continue
                cinfo("{}/{} package found as expected".format(package, version))
                break
            else:
                failures.append("{}/{} missing".format(package, version))

        return failures

    # packages_released
    #
    @property
    def packages_released(s):
        '''
        '''
        retval = True

        if s.bug.is_development_series:
            pocket = 'Release'
        else:
            pocket = 'Updates'

        for pkg in s.dependent_packages_for_pocket(pocket):
            if not s.__pkg_built(pkg, pocket):
                cinfo('            %s has not been released.' % (pkg), 'yellow')
                retval = False
                break

        return retval

    # packages_released_to_security
    #
    @property
    def packages_released_to_security(s):
        '''
        '''
        retval = True

        pocket = 'Security'

        for pkg in s.dependent_packages_for_pocket(pocket):
            if not s.__pkg_built(pkg, pocket):
                cinfo('            %s has not been released.' % (pkg), 'yellow')
                retval = False
                break

        return retval

    # pocket_route
    #
    def pocket_route(self, pocket):
        retval = None
        for pkg in self.dependent_packages():
            build_route_entry = self.__pkg_pocket_route_entry(pkg, pocket)
            if build_route_entry is None:
                continue
            retval = (build_route_entry.archive, build_route_entry.pocket)
            cinfo('            pocket {} packages found in {}'.format(pocket, retval), 'yellow')
            break
        return retval

    # pocket_routing
    #
    def pocket_routing_old(s, pocket):
        '''
        '''
        retval = None

        bi = s.legacy_info
        for pkg in bi:
            if pocket not in bi[pkg]:
                continue
            retval = bi[pkg][pocket].routing
            cinfo('            pocket {} packages found in {}'.format(pocket, retval), 'yellow')
            break

        return retval
    def pocket_routing_new(self, pocket):
        retval = None
        for pkg in self.dependent_packages():
            build_route = self.builds.get(pkg, {}).get(pocket)
            if build_route is None:
                continue
            retval = build_route.routing
            cinfo('            pocket {} packages found in {}'.format(pocket, retval), 'yellow')
            break
        return retval
    def pocket_routing(self, pocket):
        old = self.pocket_routing_old(pocket)
        new = self.pocket_routing_new(pocket)
        cinfo("PRv5b: pocket_routing {} = {} -> {}".format(pocket, old, new))
        return old

    # pocket_clear
    #
    def pocket_clear_old(s, pocket, pockets_after):
        '''
        Check that the proposed pocket is either empty or contains the same version
        as found in -updates/-release.
        '''
        retval = True

        # Release/Updates maps based on development series.
        pockets_srch = []
        for pocket_next in pockets_after:
            if pocket_next == 'Release/Updates':
                pocket_next = 'Release' if s.bug.is_development_series else 'Updates'
            pockets_srch.append(pocket_next)

        bi = s.legacy_info
        pkg_outstanding = set(bi.keys())
        for pkg in bi:
            if pocket not in bi[pkg]:
                continue
            found = False
            if bi[pkg][pocket]['version'] is None:
                found = True
            ancillary_for = s.ancillary_package_for(pkg)
            if ancillary_for is not None:
                pkg_af = ancillary_for
            else:
                pkg_af = pkg
            # If the version is our version then ultimatly we won't copy this item, all is well.
            if bi[pkg][pocket]['version'] == s.bug.bprops.get('versions', {}).get(pkg_af):
                cinfo('            {} has {} pending in {} -- my version so ignored.'.format(pkg, bi[pkg][pocket]['version'], pocket), 'yellow')
                found = True
            # If the versions is a version we have replaced within the life of this tracker, all is well.
            if not found and bi[pkg][pocket]['version'] in s.bug.bprops.get('versions-replace', {}).get(pkg_af, []):
                cinfo('            {} has {} pending in {} -- an old version of mine so ignored.'.format(pkg, bi[pkg][pocket]['version'], pocket), 'yellow')
                found = True
            # If the version is in a later pocket then all is well.
            for pocket_next in pockets_srch:
                if found:
                    break
                if pocket_next not in bi[pkg]:
                    continue
                try:
                    if version_compare(bi[pkg][pocket]['version'], bi[pkg][pocket_next]['version']) <= 0:
                        cinfo('            {} has {} pending in {} -- matches later pocket so ignored.'.format(pkg, bi[pkg][pocket]['version'], pocket), 'yellow')
                        found = True
                except ValueError:
                    pass
                if pkg not in s.dependent_packages_for_pocket(pocket_next):
                    found = True
                cinfo("APW: {} <= {} = {}".format(bi[pkg][pocket]['version'], bi[pkg][pocket_next]['version'], version_compare(bi[pkg][pocket]['version'], bi[pkg][pocket_next]['version'])))
            if found:
                pkg_outstanding.discard(pkg)

        # We are ready to go but proposed is not clear.  Consider any
        # bug we are marked as replacing.
        s.bug.dup_replaces()

        # If proposed is not clear, consider if it is full due to a bug
        # which has been duplicated against me.
        if len(pkg_outstanding):
            cinfo("APW: packages {} unaccounted for".format(pkg_outstanding))
            duplicates = s.bug.workflow_duplicates
            for dup_wb in duplicates:
                # Stop scanning out duplicates if we manage to account for everything.
                if len(pkg_outstanding) == 0:
                    break
                for pkg in list(pkg_outstanding):
                    found = False
                    if bi[pkg][pocket]['version'] is None:
                        found = True
                    ancillary_for = s.ancillary_package_for(pkg)
                    if ancillary_for is not None:
                        pkg_af = ancillary_for
                    else:
                        pkg_af = pkg
                    # If the version is our version then ultimatly we won't copy this item, all is well.
                    if bi[pkg][pocket]['version'] == dup_wb.bprops.get('versions', {}).get(pkg_af):
                        found = True
                    # If the versions is a version we have replaced within the life of this tracker, all is well.
                    if bi[pkg][pocket]['version'] in dup_wb.bprops.get('versions-replace', {}).get(pkg_af, []):
                        found = True
                    # If we have found it then all is good for this package.
                    if found:
                        cinfo('            {} has {} pending in {} -- belongs to duplicate so ignored.'.format(pkg, bi[pkg][pocket]['version'], pocket, ), 'yellow')
                        pkg_outstanding.discard(pkg)

        outstanding = {}
        for pkg in pkg_outstanding:
            cinfo('            {} has {} pending in {} -- unaccounted for so blocking.'.format(pkg, bi[pkg][pocket]['version'], pocket), 'yellow')
            retval = False
            outstanding[pkg] = [bi[pkg][pocket]['version']]

        if len(outstanding):
            s.bug.reasons['packages-unaccounted'] = 'Stalled -s ' + yaml.dump(outstanding, default_flow_style=True, width=10000).strip()

        return retval

    def pocket_clear_new(s, pocket, pockets_after, dry_run=False):
        '''
        Check that the proposed pocket is either empty or contains the same version
        as found in -updates/-release.
        '''
        retval = True

        # Release/Updates maps based on development series.
        pockets_srch = []
        for pocket_next in pockets_after:
            if pocket_next == 'Release/Updates':
                pocket_next = 'Release' if s.bug.is_development_series else 'Updates'
            pockets_srch.append(pocket_next)

        pkg_all = s.dependent_packages_for_pocket(pocket)
        pkg_outstanding = set(pkg_all)
        for pkg in pkg_all:
            build_route_entry = s.__pkg_pocket_route_entry(pkg, pocket)
            if build_route_entry is None:
                continue
            if build_route_entry.version is None:
                found = True
            ancillary_for = s.ancillary_package_for(pkg)
            if ancillary_for is not None:
                pkg_af = ancillary_for
            else:
                pkg_af = pkg
            # If the version is our version then ultimatly we won't copy this item, all is well.
            if build_route_entry.version == s.bug.bprops.get('versions', {}).get(pkg_af):
                cinfo('            {} has {} pending in {} -- my version so ignored.'.format(pkg, build_route_entry.version, pocket), 'yellow')
                found = True
            # If the versions is a version we have replaced within the life of this tracker, all is well.
            if not found and pocket_route_entry.version in s.bug.bprops.get('versions-replace', {}).get(pkg_af, []):
                cinfo('            {} has {} pending in {} -- an old version of mine so ignored.'.format(pkg, build_route_entry.version, pocket), 'yellow')
                found = True
            # If the version is in a later pocket then all is well.
            for pocket_next in pockets_srch:
                if found:
                    break
                next_route_entry = s.__pkg_pocket_route_entry(pkg, pocket_next, exact_match=False)
                if next_route_entry is None:
                    continue
                try:
                    if version_compare(build_route_entry.version, next_route_entry.version) <= 0:
                        cinfo('            {} has {} pending in {} -- matches later pocket so ignored.'.format(pkg, build_route_entry.version, pocket), 'yellow')
                        found = True
                except ValueError:
                    pass
                if pkg not in s.dependent_packages_for_pocket(pocket_next):
                    found = True
                cinfo("APW: {} <= {} = {}".format(build_route_entry.version, next_route_entry.version, version_compare(build_route_entry.version, next_route_entry.version)))
            if found:
                pkg_outstanding.discard(pkg)

        # We are ready to go but proposed is not clear.  Consider any
        # bug we are marked as replacing.
        if not dry_run:
            s.bug.dup_replaces()

        # If proposed is not clear, consider if it is full due to a bug
        # which has been duplicated against me.
        if len(pkg_outstanding):
            cinfo("APW: packages {} unaccounted for".format(pkg_outstanding))
            duplicates = s.bug.workflow_duplicates
            for dup_wb in duplicates:
                # Stop scanning out duplicates if we manage to account for everything.
                if len(pkg_outstanding) == 0:
                    break
                for pkg in list(pkg_outstanding):
                    found = False
                    build_route_entry = s.__pkg_pocket_route_entry(pkg, pocket)
                    if build_route_entry is None:
                        continue
                    if build_route_entry.version is None:
                        found = True
                    ancillary_for = s.ancillary_package_for(pkg)
                    if ancillary_for is not None:
                        pkg_af = ancillary_for
                    else:
                        pkg_af = pkg
                    # If the version is our version then ultimatly we won't copy this item, all is well.
                    if build_route_entry.version == dup_wb.bprops.get('versions', {}).get(pkg_af):
                        found = True
                    # If the versions is a version we have replaced within the life of this tracker, all is well.
                    if build_route_entry.version in dup_wb.bprops.get('versions-replace', {}).get(pkg_af, []):
                        found = True
                    # If we have found it then all is good for this package.
                    if found:
                        cinfo('            {} has {} pending in {} -- belongs to duplicate so ignored.'.format(pkg, build_route_entry.version, pocket, ), 'yellow')
                        pkg_outstanding.discard(pkg)

        outstanding = {}
        for pkg in pkg_outstanding:
            build_route_entry = s.__pkg_pocket_route_entry(pkg, pocket)
            if build_route_entry is None:
                continue
            cinfo('            {} has {} pending in {} -- unaccounted for so blocking.'.format(pkg, build_route_entry.version, pocket), 'yellow')
            retval = False
            outstanding[pkg] = [build_route_entry.version]

        if not dry_run and len(outstanding):
            s.bug.reasons['packages-unaccounted'] = 'Stalled -s ' + yaml.dump(outstanding, default_flow_style=True, width=10000).strip()

        return retval

    def pocket_clear(s, pocket, pockets_after):
        old = s.pocket_clear_old(pocket, pockets_after)
        new = s.pocket_clear_new(pocket, pockets_after, dry_run=True)
        cinfo("PRv5: pocket_clear({}, {}) = {} -> {}".format(pocket, pockets_after, old, new))
        return old

    # uploaded
    #
    def uploaded(s, pkg):
        '''
        '''
        center(s.__class__.__name__ + '.uploaded')
        retval = False

        for pocket in s.__pockets_uploaded:
            cdebug("checking for {} in {}".format(pkg, pocket))
            if s.__pkg_in(pkg, pocket):
                retval = True
                break

        cleave(s.__class__.__name__ + '.uploaded (%s)' % (retval))
        return retval

    # signed
    #
    def signed(s, pkg):
        '''
        '''
        center(s.__class__.__name__ + '.signed')
        retval = False

        for pocket in s.__pockets_signed:
            cdebug("checking for {} in {}".format(pkg, pocket))
            if s.__pkg_in(pkg, pocket):
                retval = True
                break

        cleave(s.__class__.__name__ + '.signed (%s)' % (retval))
        return retval

    # ready_to_prepare
    #
    def ready_to_prepare(s):
        master = s.bug.master_bug
        if master is None:
            return True

        if s.bug.swm_config.need_master_in_proposed:
            if master.tasks_by_name['promote-to-proposed'].status != 'Fix Released':
                return False

        # If our master is marked to block derivatives block on it.
        if 'kernel-block-derivatives' in master.tags and 'kernel-unblock-derivatives' not in master.tags:
            wait_for = []
            s.bug.interlocks['holding-derivative'] = s.bug.name

        # If our master package is a leader (no master of its own) then we want
        # to wait for it to be successfully built (Fix Released).
        elif not master.is_derivative_package and 'kernel-unblock-derivatives' not in master.tags:
            wait_for = ['Fix Released']

        # Otherwise wait for it to be tagged and uploaded (Fix Committed or later).
        else:
            wait_for = ['Fix Committed', 'Fix Released']

        for task_name in ('prepare-package', 'prepare-package-lrm'):
            task_status = master.task_status(task_name)
            if task_status != 'Invalid':
                break

        if task_status in wait_for:
            return True

        return False

    # ready_for_testing
    #
    @property
    def ready_for_testing(s):
        '''
        In order to determine if we're ready for testing the packages need to be
        fully built and published to -proposed. We build in a delay after these
        two conditions are met so that the packages are available in the archive
        to the lab machines that will be installing them.
        '''
        center(s.__class__.__name__ + '.ready_for_testing')
        # We only have mirrors on the primary archive, so if we are not routing
        # to the primary archive -proposed pocket we do not need a mirroring
        # delay.
        routing = s.routing('Proposed')
        archive = None
        if s.bug.built_in is not None and s.bug.built_in <= len(routing):
            (archive, pocket) = routing[s.bug.built_in - 1]
        if archive is not None and archive.reference == 'ubuntu':
            delay = timedelta(hours=1)
        else:
            delay = timedelta(hours=0)
        retval = s.all_built_and_in_pocket_for('Proposed', delay)
        cinfo('        Ready for testing: %s' % (retval), 'yellow')
        cleave(s.__class__.__name__ + '.ready_for_testing (%s)' % (retval))
        return retval

    # ready_for_testing_as_proposed
    #
    @property
    def ready_for_testing_as_proposed(s):
        '''
        If we have an as-proposed route check if the packages are fully published
        there and return that as current status.  If we do not have an as-proposed
        route fallback to the status in the primary proposed route.
        '''
        center(s.__class__.__name__ + '.ready_for_testing_as_proposed')
        ptap_status = s.bug.task_status(':promote-to-as-proposed')
        if ptap_status == 'Fix Released':
            retval = True

        elif ptap_status != 'Invalid':
            retval = False

        else:
            retval = s.ready_for_testing

        cinfo('        Ready for testing (as-proposed): %s' % (retval), 'yellow')
        cleave(s.__class__.__name__ + '.ready_for_testing_as_proposed (%s)' % (retval))
        return retval

    # ready_for_security
    #
    @property
    def ready_for_security(s):
        '''
        When routinely releasing to -security we will floor our infrastructure
        if the packages have not had sufficient time to mirror out to
        -updates first.  Make them wait in -updates for 20 hours.
        '''
        center(s.__class__.__name__ + '.ready_for_security')
        retval = s.all_built_and_in_pocket('Security')
        if not retval:
            retval = s.all_built_and_in_pocket_for('Updates', timedelta(hours=2))
        cinfo('        Ready for security: %s' % (retval), 'yellow')
        cleave(s.__class__.__name__ + '.ready_for_security (%s)' % (retval))
        return retval

    # Expand a cycle-spin combo so that it is comparible as text.  0 extend
    # the spin number to three digits: 2021.06.31-1 -> 2021.05.31-001.
    # Format: YYYY.MM.DD-SSS.
    def cycle_key(self, cycle):
        if cycle != '-':
            cycle_bits = cycle.split('-')
            try:
                cycle_spin = int(cycle_bits[-1])
            except ValueError:
                cycle_spin = 0
            cycle_bits[-1] = '{:03}'.format(cycle_spin)
            cycle = '-'.join(cycle_bits)
        return cycle

    # older_tracker_in_ppa
    #
    @property
    def _older_tracker_in_ppa(s):
        # The target trackers are returned in cycle order.
        target_trackers = s.bug.target_trackers
        #cinfo("older_tracker_in_ppa: {}".format(target_trackers))

        my_cycle_key = s.cycle_key(s.bug.sru_spin_name)
        my_id = str(s.bug.lpbug.id)
        for tracker_nr, tracker_data in target_trackers:
            # If we find ourselves then we have considered everything "older".
            if tracker_nr == my_id:
                return None

            # If we find we have an older cycle than the current entry we are older
            # than it.  This only can occur when we are new and have not yet saved
            # a single status.
            if my_cycle_key < tracker_data.get('cycle', '-'):
                return None

            # Consider if this is a blocker if it promote-to-proposed is not
            # Fix Released.
            cinfo("    considering {}".format(tracker_nr))
            ptp_status = tracker_data.get('task', {}).get('promote-to-proposed', {}).get('status', 'Invalid')
            stream = tracker_data.get('built', {}).get('route-entry')
            if stream is not None and stream != s.bug.built_in:
                cinfo("    not in stream {}".format(tracker_nr))

            elif ptp_status not in ('Invalid', 'Fix Released'):
                cinfo("      promote-to-proposed {} considered blocking".format(ptp_status))
                return tracker_nr

        return None

    # older_tracker_in_ppa
    #
    @property
    def older_tracker_in_ppa(s):
        retval = s._older_tracker_in_ppa
        newval = s.older_tracker_in_pocket("build")
        cinfo("OTv1: older_tracker_in_proposed = {} -> {}".format(retval, newval))
        return retval

    def _older_tracker_in_proposed(s, limit_stream):
        # The target trackers are returned in cycle order.
        target_trackers = s.bug.target_trackers
        #cinfo("older_tracker_in_ppa: {}".format(target_trackers))

        for tracker_nr, tracker_data in target_trackers:
            # If we find ourselves then we have considered everything "older".
            if tracker_nr == str(s.bug.lpbug.id):
                return None
            # Consider if this is a blocker if it promote-to-proposed is
            # Fix Released and promote-to-updates/release is not Fix Released.
            cinfo("    considering {}".format(tracker_nr))
            ptp_status = tracker_data.get('task', {}).get('promote-to-proposed', {}).get('status', 'Invalid')
            ptu_status = tracker_data.get('task', {}).get('promote-to-updates', {}).get('status', 'Invalid')
            if ptu_status == 'Invalid':
                ptu_status = tracker_data.get('task', {}).get('promote-to-release', {}).get('status', 'Invalid')
            stream = tracker_data.get('built', {}).get('route-entry')
            if stream is not None and limit_stream is not None and stream != limit_stream:
                cinfo("    not in stream {}".format(tracker_nr))
            elif ptp_status == 'Fix Released' and ptu_status not in ('Invalid', 'Fix Released'):
                cinfo("      promote-to-proposed {} plus promote-to-{{updates,release}} {} considered blocking".format(ptp_status, ptu_status))
                return tracker_nr

        return None

    # older_tracker_in_proposed
    #
    @property
    def older_tracker_in_proposed(s):
        retval = s._older_tracker_in_proposed(s.bug.built_in)
        newval = s.older_tracker_in_pocket("Proposed")
        cinfo("OTv1: older_tracker_in_proposed = {} -> {}".format(retval, newval))
        return retval

    # older_tracker_in_proposed_any
    #
    @property
    def older_tracker_in_proposed_any(s):
        retval = s._older_tracker_in_proposed(None)
        newval = s.older_tracker_in_pocket("Updates")
        cinfo("OTv1: older_tracker_in_proposed_any = {} -> {}".format(retval, newval))
        return retval

    # older_tracker_in_pocket
    #
    def older_tracker_in_pocket(s, pocket):
        blocker = s.occupancy_reference(pocket)

        cinfo("    analysing pocket {} blocker {}".format(pocket, blocker))

        target_trackers = s.bug.target_trackers
        #cinfo("older_tracker_in_ppa: {}".format(target_trackers))

        for tracker_nr, tracker_data in target_trackers:
            # If we find ourselves then we have considered everything "older".
            if tracker_nr == str(s.bug.lpbug.id):
                return None

            occupancy = tracker_data.get('occupancy')
            cinfo("    considering {} occupancy {}".format(tracker_nr, occupancy))
            if occupancy is None:
                cinfo("    no occupancy information, considered blocking")
                return tracker_nr
            if blocker in occupancy:
                cinfo("    overlapping occupancy, considered blocking")
                return tracker_nr

        return None

    # older_tracker_unprepared
    #
    @property
    def older_tracker_unprepared(s):
        # The target trackers are returned in cycle order.
        target_trackers = s.bug.target_trackers
        #cinfo("older_tracker_in_ppa: {}".format(target_trackers))

        my_cycle_key = s.cycle_key(s.bug.sru_spin_name)
        my_id = str(s.bug.lpbug.id)
        for tracker_nr, tracker_data in target_trackers:
            # If we find ourselves then we have considered everything "older".
            if tracker_nr == my_id:
                return None

            # If we find we have an older cycle than the current entry we are older
            # than it.  This only can occur when we are new and have not yet saved
            # a single status.
            if my_cycle_key < tracker_data.get('cycle', '-'):
                return None

            cinfo("    considering {}".format(tracker_nr))

            # Consider if this is a blocker if :prepare-packages is not at least Fix Committed
            # indicating everything is uploaded.
            pp_status = tracker_data.get('task', {}).get(':prepare-packages', {}).get('status', 'Invalid')
            if pp_status not in ('Invalid', 'Fix Committed', 'Fix Released'):
                cinfo("      :prepare-packages {} considered blocking".format(pp_status))
                return tracker_nr

            # Consider prepare-package a blocker if it is not Fix Released indicating we
            # have abis available.
            pp_status = tracker_data.get('task', {}).get('prepare-package', {}).get('status', 'Invalid')
            if pp_status not in ('Invalid', 'Fix Released'):
                cinfo("      prepare-package {} considered blocking".format(pp_status))
                return tracker_nr

        return None

    # occupancy_reference
    def occupancy_reference(s, pocket):
        routing = s.routing(pocket)
        if routing is None:
            cinfo("APW: occupancy_reference pocket={} no routing".format(pocket))
            return "error:NO-ROUTE " + pocket
        # XXX: we directly understand streaming here...
        if pocket in ("build", "proposed"):
            which = s.bug.built_in
            if which is None:
                which = 1
            else:
                which = int(which)
        else:
            which = 1
        if len(routing) < which:
            cinfo("APW: occupancy_reference pocket={} stream={} out of range".format(pocket, which))
            return "error:NO-STREAM " + pocket
        archive, pocket = routing[which - 1]
        if archive is None:
            cinfo("APW: occupancy_reference pocket={} no archive".format(pocket))
            return "error:NO-ARCHIVE " + pocket
        reference = archive.reference
        if pocket != "Release":
            reference += " " + pocket
        return reference

    # occupancy
    #
    @property
    def occupancy(s):
        occupancy = set()
        ptp_status = s.bug.task_status('promote-to-proposed')
        ptu_status = s.bug.task_status('promote-to-updates')
        if ptu_status == 'Invalid':
            ptu_status = s.bug.task_status('promote-to-release')
        pts_status = s.bug.task_status('promote-to-security')

        if pts_status not in ("Invalid", "Fix Released"):
            occupancy.add(s.occupancy_reference("Security"))
            occupancy.add(s.occupancy_reference("Updates"))
        if ptu_status not in ("Invalid", "Fix Released"):
            occupancy.add(s.occupancy_reference("Updates"))
            occupancy.add(s.occupancy_reference("Proposed"))
        if ptp_status not in ('Invalid', 'Fix Released'):
            occupancy.add(s.occupancy_reference("Proposed"))
            occupancy.add(s.occupancy_reference("build"))
        cinfo("APW: occupancy ptp={} ptu={} occupancy={}".format(ptp_status, ptu_status, occupancy))

        return occupancy

    def check_component_in_pocket(s, tstamp_prop, pocket):
        """
        Check if packages for the given tracking bug were properly copied
        to the right component in the given pocket.
        """
        center(s.__class__.__name__ + '.check_component_in_pocket')
        cdebug('tstamp_prop: ' + tstamp_prop)
        cdebug('     pocket: %s' % pocket)

        # Check if this is a route with components enabled.
        routing = s.bug.debs.routing(pocket)
        if routing is None:
            cleave(s.__class__.__name__ + '.check_component_in_pocket (True) -- no route')
            return (True, [])
        if routing[0][0].reference.startswith('~'):
            cleave(s.__class__.__name__ + '.check_component_in_pocket (True) -- ppa route')
            return (True, [])

        # If the packages are not all built and in -proposed then just bail out of
        # here.
        #
        if not s.bug.debs.all_built_and_in_pocket_or_after(pocket):
            cleave(s.__class__.__name__ + '.check_component_in_pocket (False)')
            return (None, [])

        check_component = CheckComponent(s)

        primary_src_component = None
        mis_lst = []
        # Run the packages list for this source, do main first as we need to
        # check components against that.
        for pkg_type in sorted(s.dependent_packages_for_pocket(pocket), key=lambda a: (a != 'main', a)):
            pkg = s.pkgs[pkg_type]
            if pkg_type == 'main':
                check_ver = s.version
            else:
                check_ver = None

            ps = check_component.get_published_sources(s.series, pkg, check_ver, pocket)
            if not ps:
                continue

            # We are going to use the primary package source component as
            # our guide.  If we do not have that, then we cannot check.
            if pkg_type == 'main':
                primary_src_component = ps[0].component_name

            # Packages are versioned in a number of ways, try these in 'longest'
            # match order.
            src_ver = ps[0].source_package_version
            match = False
            # <version>+N                      -- signed/lrm respins
            if src_ver.startswith(s.version + '+'):
                cdebug("version is full +N")
                match = True
            # <version>                        -- signed/lrm
            elif src_ver == s.version:
                cdebug("version is exact")
                match = True
            # <base version>.<abi>.<upload>    -- meta/ports-meta
            elif src_ver.startswith(s.kernel + '.' + s.abi + '.'):
                cdebug("version is base.abi.upload")
                match = True
            # <base version>-<abi>.<upload>    -- lbm
            # qualify with package type as this one is abigious against older
            # versions.  We will not use this form for new types.
            elif (pkg_type == 'lbm' and
                    src_ver.startswith(s.kernel + '-' + s.abi + '.')):
                cdebug("version is base-abi.upload (for lbm)")
                match = True

            # If we have a match:
            if match:
                if pkg_type == 'lrm' or s.ancillary_package_for(pkg_type) == 'lrm':
                    if primary_src_component == 'main':
                        which_component = 'restricted'
                    else:
                        which_component = 'multiverse'
                else:
                    which_component = primary_src_component
                mis_lst.extend(check_component.mismatches_list(s.series,
                               pkg, ps[0].source_package_version,
                               pocket, ps, which_component))

        if mis_lst:
            cdebug('mis_lst is set')
            cinfo('        packages ended up in the wrong pocket')
            cdebug('check_component_in_pocket leave (False)')
            return (False, mis_lst)

        cleave(s.__class__.__name__ + '.check_component_in_pocket (True)')
        return (True, None)

    # send_testing_message
    #
    def send_testing_message(s, op="sru", ppa=False, flavour="generic", meta=None):
        cdebug("send_testing_message: op={} ppa={} flavour={} meta={}".format(op, ppa, flavour, meta))

        who = {
            2: "s2",
            3: "s3",
        }.get(s.bug.built_in, "kernel")

        # Send a message to the message queue. This will kick off testing of
        # the kernel packages in the -proposed pocket.
        #
        msg = {
            "key"            : "kernel.publish.proposed.%s" % s.series,
            "op"             : op,
            "who"            : [who],
            "bug-id"         : str(s.bug.lpbug.id),
            "pocket"         : "proposed",
            "date"           : str(datetime.utcnow()),
            "series-name"    : s.series,
            "kernel-version" : s.version,
            "package"        : s.name,
            "flavour"        : flavour,
        }
        if meta is not None:
            msg['meta-pkg'] = meta

        # Construct the appropriate testing meta package.
        # XXX: note this is currently limited to those packages which are
        #      converted to have the new interfaces.
        #if s.bug.swm_config.hack_kernel_testing:
        #    msg['meta-pkg'] = 'kernel-testing--{}--full--{}'.format(s.name, flavour)

        # Add the kernel-sru-cycle identifier to the message
        #
        msg['sru-cycle'] = s.bug.sru_spin_name

        if ppa:
            routing = s.pocket_route('build')
        else:
            # If we have an as-proposed route we will get here when that publishes
            # and we should be preferring it for testing as there is no cache on the
            # front of it and so package publication is deterministic.
            routing = s.pocket_route('as-proposed')
            if routing is None:
                routing = s.pocket_route('Proposed')
        if routing is None:
            raise PackageError("package NOT present in the requested location ppa={} op={}".format(ppa, op))
        (archive, pocket) = routing
        if archive.reference != 'ubuntu':
            msg['pocket'] = 'ppa'
            # XXX: need to find out what this used for, if it is exclusively
            #      used to look things up using lp.archive.getByReference()
            #      then this ~ handling is not required.
            # XXX: it appears this is used to do an apt-add-repository which
            #      would need a ppa: prefix, though it will add one if missing
            #      and apt-add-repository does handle a ~ prefix as expected
            #      so it is highly likely this is not needed.
            msg['ppa']    = archive.reference.replace('~', 'ppa:')
            msg['key']    = 'kernel.published.ppa.%s' % s.series

            # If we have additioanl testing PPAs for this source add them to the ppa
            # specifier.  Convert the specifier from a simple string to a list of
            # PPAs.
            add_ppas = s.bug.swm_config.testing_ppas
            if ppa and add_ppas is not None:
                msg['ppa'] = [msg['ppa']] + add_ppas

        if s.bug._dryrun or s.bug._no_announcements:
            cinfo('    dryrun - Sending msgq announcement', 'red')
            for i, v in msg.items():
                cinfo('        [' + str(i) + '] = ' + str(v), 'red')
        else:
            #if s.bug.local_msgqueue_port:
            #    mq = MsgQueue(address='localhost', port=s.bug.local_msgqueue_port)
            #else:

            mq = MsgQueueCkct()
            mq.publish(msg['key'], msg)

        return msg

    # send_boot_testing_requests
    #
    def send_boot_testing_requests(s):
        s.send_testing_requests(op="boot", ppa=True)

    # send_proposed_testing_requests
    #
    def send_proposed_testing_requests(s):
        s.send_testing_requests(op="sru", ppa=False)

    # test_flavour_meta
    #
    def test_flavour_meta(s):
        if s.source is None:
            return []

        # If we have no testable flavours fall back to legacy mode.
        testables = s.source.testable_flavours
        cdebug("test_flavour_meta: testables={}".format(testables))
        if len(testables) == 0:
            return []

        # If any of the testables have a meta_pkg specified then
        # emit testing for those combinations.
        # NOTE: entries supporting kernel-series will have synthetic
        # meta_pkg entries of the right form.
        result = []
        for flavour in testables:
            if flavour.meta_pkg is not None:
                result.append((flavour.name, flavour.meta_pkg))
        if len(result):
            return result

        # Otherwise if we have no meta-pkg definitions, use the flavour
        # and first variant.
        variants = s.source.variants
        if variants is None or len(variants) == 0:
            variants = ['']
        if variants[0] == '--':
            variants[0] = ''
        for flavour in testables:
            result.append((flavour.name, 'linux-' + flavour.name + variants[0]))

        return result

    # test_flavours
    #
    def test_flavours(s):
        if s.bug.swm_config is not None and s.bug.swm_config.hack_kernel_testing:
            return sorted([x.name for x in s.source.testable_flavours])

        generic = (s.name is None or
                   s.name == 'linux' or
                   s.name.startswith('linux-hwe') or
                   s.name.startswith('linux-lts-'))
        if generic:
            flavours = [ 'generic', 'lowlatency' ]
        else:
            flavours = [ s.name.replace('linux-', '') ]

        return flavours

    # send_testing_requests
    #
    def send_testing_requests(s, op="sru", ppa=False):
        cdebug("send_testing_requests: op={} ppa={}".format(op, ppa))
        for flavour_meta in s.test_flavour_meta():
            s.send_testing_request(op=op, ppa=ppa, flavour=flavour_meta[0], meta=flavour_meta[1])

    # send_testing_request
    #
    def send_testing_request(s, op="sru", ppa=False, flavour="generic", meta=None):
        cdebug("send_testing_request: op={} ppa={} flavour={} meta={}".format(op, ppa, flavour, meta))
        msg = s.send_testing_message(op, ppa, flavour, meta)

        where = " uploaded" if not ppa else " available in ppa"
        subject = "[" + s.series + "] " + s.name + " " + flavour + " " + s.version + where
        s.bug.announce('swm-testing-started', subject=subject, body=json.dumps(msg, sort_keys=True, indent=4))
        #s.bug.send_email(subject, json.dumps(msg, sort_keys=True, indent=4), 'brad.figg@canonical.com,po-hsu.lin@canonical.com,sean.feole@canonical.com')

    # meta_check
    #
    def meta_check_old(self):
        cinfo("meta_check: meta is ready...")
        bi = self.legacy_info

        pocket_data = bi["meta"].get("build")
        if pocket_data is None:
            return

        meta_version = pocket_data.version
        signing_present = "signed" in bi

        src = pocket_data.source
        cinfo("meta_check: source={}\n".format(pocket_data.source))
        if src is None:
            return

        bins = src.getPublishedBinaries(active_binaries_only=False)
        bins_image = []
        for binary in bins:
            binary_name = binary.binary_package_name
            if "-image-" in binary_name:
                bins_image.append(binary)
        #cinfo("meta_check: bins_image={}".format(bins_image))
        bins_image_names = set([binary.binary_package_name for binary in bins_image])

        variant_change = False
        version_change = False

        previously_published = False
        for pocket_data in (bi["meta"].get("Updates"), bi["meta"].get("Release")):
            if pocket_data is None:
                continue
            if pocket_data.route is None:
                continue
            lp_archive, pocket = pocket_data.route
            if lp_archive is None:
                continue

            #if pocket_data.version is None:
            #    continue
            if pocket_data.version == meta_version:
                previously_published = True
                continue

            # See if we have different names in this pocket.
            src = pocket_data.source
            cinfo("meta_check: previous src={}\n".format(pocket_data.source))
            if src is not None:
                previously_published = True
                bins = src.getPublishedBinaries(active_binaries_only=False)
                bins_image_prev = []
                for binary in bins:
                    binary_name = binary.binary_package_name
                    if "-image-" in binary_name:
                        bins_image_prev.append(binary)
                    #cinfo("meta_check: bins_image_prev={}".format(bins_image))

                bins_image_prev_names = set([binary.binary_package_name for binary in bins_image_prev])
                if bins_image_prev_names != bins_image_names:
                    cinfo("meta_check: names are different variant change prev={} curr={}".format(bins_image_prev_names, bins_image_names))
                    variant_change = True

            # See if we can see different versions of this package in the released
            # pocket.
            some = False
            for binary in bins_image:
                pubs = lp_archive.getPublishedBinaries(
                    order_by_date=True,
                    exact_match=True,
                    distro_arch_series=binary.distro_arch_series,
                    pocket=pocket,
                    status='Published',
                    binary_name=binary.binary_package_name,
                )
                for pub in pubs:
                    prev_version = pub.binary_package_version
                    if prev_version == meta_version:
                        continue
                    some = True

                    if meta_version.split('.')[0:2] != prev_version.split('.')[0:2]:
                        cinfo("meta_check: major versions are different prev={} curr={}".format(prev_version.split('.')[0:2], meta_version.split('.')[0:2]))
                        version_change = True
            if some:
                break

        signing_signoff = signing_present and (not previously_published or version_change)
        kernel_signoff = version_change or variant_change

        if kernel_signoff and "kernel-signoff" not in self.bug.tasks_by_name:
            cinfo("meta_check: kernel-signoff required")
            self.bug.add_task("kernel-signoff")
        if signing_signoff and "signing-signoff" not in self.bug.tasks_by_name:
            cinfo("meta_check: signing-signoff required")
            self.bug.add_task("signing-signoff")

        messages = []
        if signing_signoff and not previously_published:
            messages.append("New kernel with signed kernels; signing-review required.")
        elif signing_signoff:
            messages.append("Major kernel version bump with signed kernels; signing-review required.")
        if variant_change:
            messages.append("linux-image name changes detected, review variant/flavour changes; kernel-signoff required.")
        if version_change:
            messages.append("linux-image major version change detected, upgrade testing required; kernel-signoff required.")
        if len(messages) > 0:
            self.bug.add_comment("Kernel requires additional signoff", "\n".join(messages))

    def meta_check_new(self, dry_run=False):
        cinfo("meta_check: meta is ready...")
        build_route_entry = self.__pkg_pocket_route_entry("meta", "build")
        if build_route_entry is None:
            return

        # XXX: the presupposes the only risky signed package is "signed"
        signed_route_entry = self.__pkg_pocket_route_entry("signed", "build")
        signing_present = signed_route_entry is not None

        meta_version = build_route_entry.version
        src = build_route_entry.source
        cinfo("meta_check: source={}\n".format(src))
        if src is None:
            return

        bins = src.getPublishedBinaries(active_binaries_only=False)
        bins_image = []
        for binary in bins:
            binary_name = binary.binary_package_name
            if "-image-" in binary_name:
                bins_image.append(binary)
        #cinfo("meta_check: bins_image={}".format(bins_image))
        bins_image_names = set([binary.binary_package_name for binary in bins_image])

        updates_route_entry = self.__pkg_pocket_route_entry("meta", "Updates")
        release_route_entry = self.__pkg_pocket_route_entry("meta", "Release")
        variant_change = False
        version_change = False
        previously_published = False
        for route_entry in (updates_route_entry, release_route_entry):
            if route_entry is None:
                continue
            if route_entry.route is None:
                continue
            lp_archive, pocket = route_entry.route
            if lp_archive is None:
                continue

            #if pocket_data.version is None:
            #    continue
            if route_entry.version == meta_version:
                previously_published = True
                continue

            # See if we have different names in this pocket.
            src = route_entry.source
            cinfo("meta_check: previous src={}\n".format(src))
            if src is not None:
                previously_published = True
                bins = src.getPublishedBinaries(active_binaries_only=False)
                bins_image_prev = []
                for binary in bins:
                    binary_name = binary.binary_package_name
                    if "-image-" in binary_name:
                        bins_image_prev.append(binary)
                    #cinfo("meta_check: bins_image_prev={}".format(bins_image))

                bins_image_prev_names = set([binary.binary_package_name for binary in bins_image_prev])
                if bins_image_prev_names != bins_image_names:
                    cinfo("meta_check: names are different variant change prev={} curr={}".format(bins_image_prev_names, bins_image_names))
                    variant_change = True

            # See if we can see different versions of this package in the released
            # pocket.
            some = False
            for binary in bins_image:
                pubs = lp_archive.getPublishedBinaries(
                    order_by_date=True,
                    exact_match=True,
                    distro_arch_series=binary.distro_arch_series,
                    pocket=pocket,
                    status='Published',
                    binary_name=binary.binary_package_name,
                )
                for pub in pubs:
                    prev_version = pub.binary_package_version
                    if prev_version == meta_version:
                        continue
                    some = True

                    if meta_version.split('.')[0:2] != prev_version.split('.')[0:2]:
                        cinfo("meta_check: major versions are different prev={} curr={}".format(prev_version.split('.')[0:2], meta_version.split('.')[0:2]))
                        version_change = True
            if some:
                break

        signing_signoff = signing_present and (not previously_published or version_change)
        kernel_signoff = version_change or variant_change

        if kernel_signoff and "kernel-signoff" not in self.bug.tasks_by_name:
            cinfo("meta_check: kernel-signoff required")
            if not dry_run:
                self.bug.add_task("kernel-signoff")
        if signing_signoff and "signing-signoff" not in self.bug.tasks_by_name:
            cinfo("meta_check: signing-signoff required")
            if not dry_run:
                self.bug.add_task("signing-signoff")

        messages = []
        if signing_signoff and not previously_published:
            messages.append("New kernel with signed kernels; signing-review required.")
        elif signing_signoff:
            messages.append("Major kernel version bump with signed kernels; signing-review required.")
        if variant_change:
            messages.append("linux-image name changes detected, review variant/flavour changes; kernel-signoff required.")
        if version_change:
            messages.append("linux-image major version change detected, upgrade testing required; kernel-signoff required.")
        if len(messages) > 0:
            if not dry_run:
                self.bug.add_comment("Kernel requires additional signoff", "\n".join(messages))

    def meta_check(self):
        old = self.meta_check_old()
        new = self.meta_check_new(dry_run=True)
        cinfo("PRv5: meta_check() = {} -> {}".format(old, new))
        return old
