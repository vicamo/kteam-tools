#!/usr/bin/python

# Copyright (C) 2009-2013  Canonical Ltd.
# Authors:
#   Andy Whitcroft <apw@canonical.com>
# Based on sru-report by:
#   Martin Pitt <martin.pitt@ubuntu.com>
#   Jean-Baptiste Lallement <jean-baptiste.lallement@canonical.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

from functools import cmp_to_key

import logging
import os

import apt_pkg
from launchpadlib.launchpad import Launchpad as _Launchpad

# Work around non-multiple-instance-safety of launchpadlib (bug #459418).
class Launchpad(_Launchpad):
    @classmethod
    def _get_paths(cls, service_root, launchpadlib_dir=None):
        service_root, launchpadlib_dir, cache_path, service_root_dir = (
            _Launchpad._get_paths(
                service_root, launchpadlib_dir=launchpadlib_dir))
        cache_path += "-sru-report"
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, 0o700)
        return service_root, launchpadlib_dir, cache_path, service_root_dir

class PackagePockets:
    def __init__(s, pv, series, sourcename):
        s.pv = pv
        s.series = series
        s.sourcename = sourcename

        s.pockets = None
        s.published = {}
        s.published_infer = {}

    def _cache_load(s):
        distro_series = s.pv.releases[s.series]

        logging.debug(
            'Fetching publishing history for %s/%s' %
            (distro_series.name, s.sourcename))
        pubs = s.pv.archive.getPublishedSources(source_name=s.sourcename,
                                           exact_match=True,
                                           distro_series=distro_series)

        # Take the latest pocket the package made it into as its 'pocket'.
        s.pockets = {}
        s.published = {}
        for pub in pubs:
            logging.debug("publication: %s %s %s" % (pub.source_package_version, pub.pocket, pub.status))
            version = pub.source_package_version
            pocket = pub.pocket

            # Record all pockets a version has been in.
            if version not in s.pockets:
                s.pockets[version] = []
            if pocket not in s.pockets[version]:
                s.pockets[version].append(pocket)

            # Record the Published version in a pocket.
            if pub.status == 'Published':
                s.published[pocket] = version

        s.published_infer = s.published

        if 'Release' not in s.published:
            for version in sorted(s.pockets.keys(), key=cmp_to_key(apt_pkg.version_compare)):
                if 'Updates' in s.pockets[version]:
                    s.published_infer['Release'] = version
                    break

    def _pockets(s):
        if not s.pockets:
            s._cache_load()

        return s.pockets


    def _pocket_lookup(s, pocket, infer_release):
        if infer_release and pocket in s.published_infer:
            return s.published_infer[pocket]
        elif pocket in s.published:
            return s.published[pocket]

        if pocket == 'Release' and infer_release:
            s._pockets()
            return s.published_infer[pocket]

        distro_series = s.pv.releases[s.series]

        logging.debug(
            'Fetching publishing record for %s/%s %s' %
            (distro_series.name, s.sourcename, pocket))
        pubs = s.pv.archive.getPublishedSources(source_name=s.sourcename,
                                                exact_match=True,
                                                distro_series=distro_series,
                                                pocket=pocket,
                                                status='Published')
        for pub in pubs:
            s.published[pocket] = pub.source_package_version
            s.published_infer[pocket] = pub.source_package_version

        if pocket not in s.published:
            s.published[pocket] = None
            s.published_infer[pocket] = None

        return s.published[pocket]


    def current_in_pocket(s, pocket, infer_release=False):
        '''Get the current version of this package published in the specified pocket'''
        pocket = pocket.capitalize()

        logging.debug('current_in_pocket: %s' % (pocket,))

        # If a package is introduced post release then there is no -release
        # version, the very first -updates version stands in for this version.
        return s._pocket_lookup(pocket, infer_release)


    def all_viable(s):
        pockets = s._pockets()

        result = []
        version = None
        for version in sorted(s.pockets.keys(), key=cmp_to_key(apt_pkg.version_compare)):
            #print(version, pockets[version])
            if pockets[version] != ['Proposed']:
                result.append(version)

        if version in s.pockets and pockets[version] == ['Proposed']:
            result.append(version)

        return result


class KernelVersions:
    def __init__(s, launchpad=None, ppa_owner=None, ppa_name=None, active_only=True):
        s.lp = None
        s.ubuntu = None
        s.archive = None
        s.releases = {}  # name -> distro_series
        s.broken_bugs = set()
        s.ignored_commenters = []

        s.lpinit(launchpad=launchpad, ppa_owner=ppa_owner, ppa_name=ppa_name, active_only=active_only)
        apt_pkg.init_system()


    def pocket_data(s, series, sourcename):
        return PackagePockets(s, series, sourcename)


    def current_in_pocket(s, pocket, series, sourcename, infer_release=False):
        '''Get the current version of this package published in the specified pocket'''
        pockets = s.pocket_data(series, sourcename)

        return pockets.current_in_pocket(pocket, infer_release)


    def all_viable(s, series, sourcename):
        '''Get all viable versions of this package published ever, only the last -proposed is considered'''
        pockets = s.pocket_data(series, sourcename)

        return pockets.all_viable()


    def ppa(s, ppa_owner, ppa_name):
        return KernelVersions(launchpad=s.lp, active_only=s.active_only, \
                              ppa_owner=ppa_owner, ppa_name=ppa_name)


    def lpinit(s, launchpad=None, ppa_owner=None, ppa_name=None, active_only=True):
        '''Init LP credentials, archive, distro list and sru-team members'''
        logging.debug("Initializing LP Credentials")
        if not launchpad:
            s.lp = Launchpad.login_anonymously('kernel-versions', 'production')
        else:
            s.lp = launchpad
            
        s.ubuntu = s.lp.distributions['ubuntu']
        if not ppa_owner:
            s.archive = s.ubuntu.getArchive(name='primary')
        else:
            s.archive = s.lp.people[ppa_owner].getPPAByName(name=ppa_name)

        s.active_only = active_only
        for series in s.ubuntu.series:
            if not active_only or series.active:
                s.releases[series.name] = series
        logging.debug('Active releases found: %s' % ' '.join(s.releases))

