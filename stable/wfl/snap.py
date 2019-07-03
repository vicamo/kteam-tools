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

from wfl.log                                    import center, cleave, cinfo, cerror, cdebug


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

    # _channel_map
    #
    def _channel_map(s):
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
            params = urlencode({'fields': 'channel-map,architecture,channel,revision,version'})
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
            s._versions = s._channel_map()
        return s._versions.get(key, {}).get('version', None)

    # channel_revision
    #
    def channel_revision(s, arch, channel):
        key = (arch, channel)
        if s._versions is None:
            s._versions[key] = s._channel_map()
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

        s.kernel_series = KernelSeries() if ks is None else ks

        if s.bug.variant == 'snap-debs':
            # We take our version from the debs we are snapping up
            # so grab the version data from there and update the bug
            # title to match as needed.
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

        publish_to = s.snap_info.publish_to
        if publish_to is not None:
            retval = True
            for arch in sorted(publish_to):
                missing_arch = []
                missing_entry = None
                for track in publish_to[arch]:
                    channel = "{}/{}".format(track, risk)
                    version = s.snap_store.channel_version(arch, channel)
                    cdebug("track-version: arch={} channel={}  version={} ?? bug.version={}".format(arch, channel, s.snap_store.channel_version(arch, channel), s.bug.version))
                    if s.bug.version != version:
                        missing_arch.append("arch={}:channel={}".format(arch, channel))
                # We have channels missing the expected version for this
                # architecture.  Search all of the risks in all of the expected
                # tracks for the version required (and associated revision).
                # This allows us to find an appropriate revision in a higher
                # risk category for this channel or in any other channela
                # primary edge channel; launchpad can only publish to a single
                # track when auto uploading so where there are more than one
                # we need to promote it sideways.
                if len(missing_arch) > 0:
                    revision = None
                    for search_risk in ('edge', 'beta', 'candidate'):
                        for track in publish_to[arch]:
                            channel = "{}/{}".format(track, search_risk)
                            version = s.snap_store.channel_version(arch, channel)
                            if s.bug.version == version:
                                revision = s.snap_store.channel_revision(arch, channel)
                                break
                        if revision is not None:
                            break

                    if revision is not None:
                        missing_arch = [ m + ':rev={}'.format(revision) for m in missing_arch]
                missing += missing_arch
        else:
            missing.append("UNKNOWN")

        retval = len(missing) == 0

        cleave(s.__class__.__name__ + '.is_in_tracks')
        return retval, missing

    def promote_to_risk(s, risk):
        return s.snap_info.promote_to_risk(risk)
