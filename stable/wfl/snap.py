#!/usr/bin/env python

try:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, urljoin
    from urllib.error import URLError, HTTPError
except ImportError:
    from urllib2 import urlopen, urlencode, Request, URLError, HTTPError

import json
from .errors import ShankError

from ktl.kernel_series                          import KernelSeries

from wfl.git_tag                                import GitTagsSnap
from wfl.log                                    import center, cleave, cinfo, cerror, cdebug

from .secrets                                   import Secrets


# SnapError
#
class SnapError(ShankError):
    pass


# SnapStoreError
#
class SnapStoreError(ShankError):
    """
    Thrown when something goes wrong with the snap store (e.g. snap not found).
    """
    pass


# SnapStore
#
class SnapStore:
    """
    A helper class to handle Snapcraft store operations.
    """
    base_url = "https://api.snapcraft.io/v2/snaps/info/"
    common_headers = {'Snap-Device-Series': '16'}
    # curl -H 'Snap-Device-Series: 16' 'https://api.snapcraft.io/v2/snaps/info/pc-kernel?fields=channel-map,architecture,channel,revision,version'

    # __init__
    #
    def __init__(s, snap):
        """
        :param bug: WorkflowBug object
        """
        s.snap = snap
        s._versions = None  # dictionary with {(<arch>,<channel>): {<version>,<revision>}}
        s.secrets = Secrets().get('snaps')

    # channel_map
    #
    def channel_map(s):
        """
        Query the snap store URL to get the information about the kernel snap
        publishing.

        :return: publishing array
        """
        cdebug("    snap.name={}".format(s.snap.name))
        cdebug("    snap.publish_to={}".format(s.snap.publish_to))

        result = {}
        try:
            headers = s.common_headers

            params = urlencode({'fields': 'revision,version'})
            store_id = s.secrets.get(s.snap.name, {}).get('store-id')
            if store_id is not None:
                cdebug('SnapStore: {} using snap specific store-id')
                headers['Snap-Device-Store'] = store_id
            url = "{}?{}".format(urljoin(s.base_url, s.snap.name), params)
            req = Request(url, headers=headers)
            with urlopen(req) as resp:
                response = json.loads(resp.read().decode('utf-8'))
                cdebug(response)
                for channel_rec in response['channel-map']:
                    channel = (channel_rec['channel']['architecture'],
                        channel_rec['channel']['track'] + '/' +
                        channel_rec['channel']['risk'])
                    entry = {}
                    entry['version'] = channel_rec['version']
                    entry['revision'] = channel_rec['revision']
                    entry['released-at'] = channel_rec['channel']['released-at']
                    result[channel] = entry

        except HTTPError as e:
            # Error 404 is returned if the snap has never been published
            # to the given channel.
            store_err = False
            if hasattr(e, 'code') and e.code == 404:
                ret_body = e.read().decode()
                store_err_str = 'has no published revisions in the given context'
                if store_err_str in ret_body:
                    store_err = True
            if not store_err:
                raise SnapStoreError('failed to retrieve store URL (%s)' % str(e))
        except (URLError, KeyError) as e:
            raise SnapStoreError('failed to retrieve store URL (%s: %s)' %
                                 (type(e), str(e)))
        return result

    # channel_version
    #
    def channel_version(s, arch, channel):
        key = (arch, channel)
        if s._versions is None:
            s._versions = s.channel_map()
        return s._versions.get(key, {}).get('version', None)

    # channel_revision
    #
    def channel_revision(s, arch, channel):
        key = (arch, channel)
        if s._versions is None:
            s._versions[key] = s.channel_map()
        return s._versions.get(key, {}).get('revision', None)


# SnapDebs
#
class SnapDebs:
    """
    Class representing a snap of a kernel from debian packages.
    """
    def __init__(s, shankbug, ks=None):
        s.bug = shankbug

        s.snap_info = None
        s._snap_store = None
        s._git_repo = False

        s.kernel_series = KernelSeries() if ks is None else ks

        if s.bug.variant == 'snap-debs':
            # We take our version from the debs we are snapping up
            # so grab the version data from there and update the bug
            # title to match as needed.
            if not s.bug.is_derivative_package:
                raise SnapError("snap-debs requires a master bug pointing at the deb builds to be snapped")
            s.bug.version_from_master()

            # Expect this bug to have the data we need to identify the
            # snap.
            snap_name = s.bug.bprops.get('snap-name')
            if snap_name is None:
                raise SnapError("snap-name not provided")
            source = s.bug.source
            if source is not None:
                s.snap_info = source.lookup_snap(snap_name)
                if s.snap_info is None:
                    raise SnapError("{}: snap does not appear in kernel-series for that source".format(snap_name))

            s.bug.update_title(suffix='snap-debs snap:' + snap_name)

        elif s.bug.variant == 'combo':
            # For a combo bug take versioning from our title.
            s.bug.version_from_title()

            # Lookup the primary snap and use that.
            source = s.bug.source
            if source is not None:
                snaps = source.snaps
                for snap in snaps:
                    if snap.primary:
                        s.snap_info = snap
                        break

        # Pick up versions from our bug as needed.
        s.series = s.bug.series
        s.name = s.bug.name
        s.version = s.bug.version
        s.source = s.bug.source
        s.kernel = s.bug.kernel
        s.abi = s.bug.abi

        # Our name is our snap name.
        if s.snap_info is not None:
            s.name = s.snap_info.name

    @property
    def snap_store(s):
        if s._snap_store is None:
            s._snap_store = SnapStore(s.snap_info)
        return s._snap_store

    def is_in_tracks(s, risk):
        center(s.__class__.__name__ + '.is_in_tracks')
        missing = []

        partial = False
        publish_to = s.snap_info.publish_to
        if publish_to is not None:
            for arch in sorted(publish_to):
                # Find the highest revision in the highest risk.  This is will
                # then be used to validate the publications in the appropriate
                # channels.
                expected_revision = None
                for search_risk in ('edge', 'beta', 'candidate'):
                    for track in publish_to[arch]:
                        channel = "{}/{}".format(track, search_risk)
                        version = s.snap_store.channel_version(arch, channel)
                        if s.bug.version == version:
                            revision = s.snap_store.channel_revision(arch, channel)
                            if expected_revision is None or revision > expected_revision:
                                expected_revision = revision
                            break
                    if expected_revision is not None:
                        break

                missing_arch = []
                missing_entry = None
                for track in publish_to[arch]:
                    channel = "{}/{}".format(track, risk)
                    version = s.snap_store.channel_version(arch, channel)
                    revision = s.snap_store.channel_revision(arch, channel)
                    cdebug("track-version: arch={} channel={}  version={} revision={} ?? bug.version={} expected_revision={}".format(arch, channel, version, revision, s.bug.version, expected_revision))
                    if expected_revision is None or expected_revision != revision:
                        entry = "arch={}:channel={}".format(arch, channel)
                        if expected_revision is not None:
                            entry += ':rev={}'.format(expected_revision)
                        if s.bug.version == version and revision is not None:
                            entry += ':badrev={}'.format(revision)
                        missing_arch.append(entry)
                    elif revision != None:
                        partial = True
                missing += missing_arch
        else:
            missing.append("UNKNOWN")

        retval = len(missing) == 0

        cleave(s.__class__.__name__ + '.is_in_tracks')
        return retval, partial, missing

    def channel_revisions_consistent(s, before_risk=None):
        center(s.__class__.__name__ + '.channel_revisions_consistent')
        broken = []

        publish_to = s.snap_info.publish_to
        promote_to = s.snap_info.promote_to
        if publish_to is not None and promote_to is not None:
            for arch in sorted(publish_to):
                # Find the highest revision in the highest risk.  This is will
                # then be used to validate the publications in the appropriate
                # channels.
                expected_revision = None
                for search_risk in ('edge', 'beta', 'candidate'):
                    for track in publish_to[arch]:
                        channel = "{}/{}".format(track, search_risk)
                        version = s.snap_store.channel_version(arch, channel)
                        if s.bug.version == version:
                            revision = s.snap_store.channel_revision(arch, channel)
                            if expected_revision is None or revision > expected_revision:
                                expected_revision = revision
                            break
                    if expected_revision is not None:
                        break

                if expected_revision is not None:
                    for track in publish_to[arch]:
                        track_versions = ()
                        for risk in s.snap_info.promote_to:
                            # Only check to the risk level requested.
                            if risk == before_risk:
                                break
                            task = "snap-release-to-{}".format(risk)
                            if (task not in s.bug.tasks_by_name or
                                    s.bug.tasks_by_name[task].status != 'New'):
                                continue
                            channel = "{}/{}".format(track, risk)
                            revision = s.snap_store.channel_revision(arch, channel)
                            if revision is not None and expected_revision != revision:
                                broken.append("arch={}:channel={}:rev={}:badrev={}".format(arch, channel, expected_revision, revision))

        retval = len(broken) == 0

        cleave(s.__class__.__name__ + '.channel_revisions_consistent')
        return retval, broken

    def promote_to_risk(s, risk):
        return s.snap_info.promote_to_risk(risk)

    @property
    def git_repo(s):
        if s._git_repo is False:
            ks_snap = s.snap_info
            s._git_repo = GitTagsSnap(ks_snap)
        return s._git_repo

    # snap_status
    #
    def snap_status(s, sha):
        lp = s.bug.lp.launchpad
        ks_snap = s.snap_info

        # Find the snap repository in launchpad.
        path = '~' + ks_snap.repo.url.split('~')[1]
        lp_repo = lp.git_repositories.getByPath(path=path)
        lp_ref = lp_repo.getRefByPath(path='refs/heads/' + ks_snap.repo.branch)
        cinfo("snap_status: ks_snap={} sha={} lp_repo={} lp_ref={}".format(ks_snap, sha, lp_repo, lp_ref))

        # Lookup our team snap recipies.
        cks = lp.people['canonical-kernel-snaps']
        for lp_snap in lp.snaps.findByOwner(owner=cks):
            if lp_snap.git_ref == lp_ref:
                cdebug("snap_status: snap found {}".format(lp_snap))
                break
        else:
            return 'SNAP-MISSING'

        # Run the list of builds for this snap and see if we have one for the sha
        # we care about.  If so take the first build in each arch as the current
        # status.  Accumulate the build and upload stati into a single status
        # for this snap build and upload phase.
        status = set()
        status.add('BUILD-MISSING')
        arches_seen = {}

        # Assume we are incomplete if there are any build pending as we have no way
        # to know which revision they will refer supply for once built.
        for build in lp_snap.pending_builds:
            cinfo("snap build pending: {} {} {} {}".format(build, build.arch_tag, build.buildstate, build.revision_id))
            arch_tag = build.arch_tag
            arches_seen[arch_tag] = True

            status.add('BUILD-PENDING')

        for build in lp_snap.builds:
            cinfo("snap build complete: {} {} {} {}".format(build, build.arch_tag, build.buildstate, build.revision_id))
            # If we haven't seen the revision we want skip.
            if build.revision_id != sha:
                # Before our sha, continue scanning.
                if len(arches_seen) == 0:
                    continue
                # Leaving our revision, stop scanning.
                break

            # Take only the latest status for an architecture.
            arch_tag = build.arch_tag
            if arch_tag in arches_seen:
                continue
            arches_seen[arch_tag] = True
            #print(build, arch_tag, build.revision_id, build.buildstate, build.store_upload_status)

            if build.buildstate in (
                    'Needs building',
                    'Currently building',
                    'Uploading build'):
                status.add('BUILD-ONGOING')

            elif build.buildstate == 'Dependency wait':
                status.add('BUILD-DEPWAIT')

            elif build.buildstate == 'Successfully built':
                status.add('BUILD-COMPLETE')

            else:
                status.add('BUILD-FAILED')
                # Anything else is a failure, currently:
                #  Failed to build
                #  Dependency wait
                #  Chroot problem
                #  Build for superseded Source
                #  Failed to upload
                #  Cancelling build
                #  Cancelled build

            if build.store_upload_status in (
                    'Pending',
                    'Unscheduled'):
                status.add('UPLOAD-PENDING')

            elif build.store_upload_status == 'Uploaded':
                status.add('UPLOAD-COMPLETE')

            else:
                status.add('UPLOAD-FAILED')
                # Anything else is a failure, currently:
                #  Failed to upload
                #  Failed to release to channels

        # Find the 'worst' state and report that for everything.
        for state in (
                'BUILD-FAILED', 'UPLOAD-FAILED',                                     # Errors: earliest first
                'BUILD-PENDING', 'BUILD-DEPWAIT', 'BUILD-ONGOING', 'UPLOAD-PENDING', # Pending: earliest first
                'UPLOAD-COMPLETE', 'BUILD-COMPLETE',                                 # Finished: latest first
                'BUILD-MISSING'):
            if state in status:
                break

        cdebug("snap_status: build/upload stati {} {}".format(status, state))

        return state

