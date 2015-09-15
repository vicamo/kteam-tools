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

import apt_pkg
from .log                               import cdebug, center, cleave

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

        cdebug('Fetching publishing history for %s/%s' % (distro_series.name, s.sourcename))
        pubs = s.pv.archive.getPublishedSources(source_name=s.sourcename, exact_match=True, distro_series=distro_series)

        # Take the latest pocket the package made it into as its 'pocket'.
        s.pockets = {}
        s.published = {}
        for pub in pubs:
            cdebug("publication: %s %s %s" % (pub.source_package_version, pub.pocket, pub.status))
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
            return s.published_infer.get(pocket)

        distro_series = s.pv.releases[s.series]

        cdebug('Fetching publishing record for %s/%s %s' % (distro_series.name, s.sourcename, pocket))
        pubs = s.pv.archive.getPublishedSources(source_name=s.sourcename,
                                                exact_match=True,
                                                distro_series=distro_series,
                                                pocket=pocket,
                                                status='Published')
        for pub in pubs:
            s.published[pocket] = pub.source_package_version
            s.published_infer[pocket] = pub.source_package_version

        return s.published.get(pocket)

    def current_in_pocket(s, pocket, infer_release=False):
        '''Get the current version of this package published in the specified pocket'''
        pocket = pocket.capitalize()

        cdebug('current_in_pocket: %s' % (pocket,))

        # If a package is introduced post release then there is no -release
        # version, the very first -updates version stands in for this version.
        return s._pocket_lookup(pocket, infer_release)

    def all_viable(s, include_proposed=True):
        pockets = s._pockets()

        result = []
        version = None
        for version in sorted(s.pockets.keys(), key=cmp_to_key(apt_pkg.version_compare)):
            if pockets[version] != ['Proposed']:
                result.append(version)

        if include_proposed and version in s.pockets and pockets[version] == ['Proposed']:
            result.append(version)

        return result


class KernelVersions:
    def __init__(s, launchpad, ppa_owner=None, ppa_name=None, active_only=True):
        center(s.__class__.__name__ + '.__init__')
        s.lp = launchpad
        s.ubuntu = None
        s.archive = None
        s.releases = {}  # name -> distro_series
        s.broken_bugs = set()
        s.ignored_commenters = []

        s.lpinit(launchpad=launchpad, ppa_owner=ppa_owner, ppa_name=ppa_name, active_only=active_only)
        apt_pkg.init_system()
        cleave(s.__class__.__name__ + '.__init__')

    def pocket_data(s, series, sourcename):
        center(s.__class__.__name__ + '.pocket_data')

        retval = PackagePockets(s, series, sourcename)

        cleave(s.__class__.__name__ + '.pocket_data')
        return retval

    def current_in_pocket(s, pocket, series, sourcename, infer_release=False):
        '''
        Get the current version of this package published in the specified pocket
        '''
        center(s.__class__.__name__ + '.current_in_pocket')

        pockets = s.pocket_data(series, sourcename)
        retval = pockets.current_in_pocket(pocket, infer_release)

        cleave(s.__class__.__name__ + '.current_in_pocket')
        return retval

    def all_viable(s, series, sourcename):
        '''
        Get all viable versions of this package published ever, only the last -proposed is considered
        '''
        center(s.__class__.__name__ + '.all_viable')

        pockets = s.pocket_data(series, sourcename)
        retval = pockets.all_viable()

        cleave(s.__class__.__name__ + '.all_viable')
        return retval

    def ppa(s, ppa_owner, ppa_name):
        center(s.__class__.__name__ + '.ppa')

        retval = KernelVersions(launchpad=s.lp, active_only=s.active_only, ppa_owner=ppa_owner, ppa_name=ppa_name)

        cleave(s.__class__.__name__ + '.ppa')
        return retval

    def lpinit(s, launchpad=None, ppa_owner=None, ppa_name=None, active_only=True):
        '''
        Init LP credentials, archive, distro list and sru-team members
        '''
        center(s.__class__.__name__ + '.lpinit')

        s.ubuntu = s.lp.distributions['ubuntu']
        if not ppa_owner:
            s.archive = s.ubuntu.getArchive(name='primary')
        else:
            s.archive = s.lp.people[ppa_owner].getPPAByName(name=ppa_name)

        s.active_only = active_only
        for series in s.ubuntu.series:
            if not active_only or series.active:
                s.releases[series.name] = series
        cdebug('Active releases found: %s' % ' '.join(s.releases))

        cleave(s.__class__.__name__ + '.lpinit')
