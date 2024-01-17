#!/usr/bin/env python

try:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, urljoin
    from urllib.error import URLError, HTTPError
except ImportError:
    from urllib2 import urlopen, urlencode, Request, URLError, HTTPError

import os
import json
from .errors import ShankError
from datetime import datetime
import subprocess

from lazr.restfulclient.errors import NotFound


from wfl.git_tag                                import GitTagsSnap
from wfl.log                                    import center, cleave, cinfo, cerror, cdebug, centerleave

from .context                                   import ctx
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
        s._channel_map = None  # dictionary with {(<arch>,<channel>): {<version>,<revision>}}
        s._revision_map = None  # dictionary with {<revision}: {<version>,<revision>}}
        s.secrets = Secrets(os.path.expanduser("~/.swm-secrets.yaml")).get('snaps')

    # channel_map_lookup
    #
    def channel_map_lookup(s):
        """
        Probe the snap publishing records in the store.

        :return: publishing array
        """
        cdebug("    snap.name={}".format(s.snap.name))
        cdebug("    snap.publish_to={}".format(s.snap.publish_to))

        channels = {}
        revisions = {}
        for arch, tracks in s.snap.publish_to.items():
            actions = []
            for track in tracks:
                # XXX: we should be a little more dynamic with streams perhaps.
                for risk in [
                    "edge", "edge/stream2",
                    "beta", "beta/stream2",
                    "candidate", "candidate/stream2",
                    "stable"
                ]:
                    channel = "{}/{}".format(track, risk)
                    actions.append({
                        "action": "download",
                        "instance-key": channel,
                        "name": s.snap.name,
                        "channel": channel,
                    })
            data = {
                "context": [],
                "actions": actions,
                "fields": ["name","revision","type","version"],
            }
            try:
                headers = s.common_headers
                store_id = s.secrets.get(s.snap.name, {}).get("store-id")
                if store_id is not None:
                    cdebug("SnapStore: {} using snap specific store-id")
                    headers["Snap-Device-Store"] = store_id
                headers["Snap-Device-Architecture"] = arch
                headers["Content-Type"] = 'application/json'

                url = "https://api.snapcraft.io/v2/snaps/refresh"
                req = Request(url, headers=headers, method="POST", data=bytes(json.dumps(data), "ascii"))
                with urlopen(req) as resp:
                    raw_data = resp.read().decode('utf-8')
                    cdebug("SNAP JSON: {}".format(raw_data))
                    response = json.loads(raw_data)
                    cdebug(response)
                    for result in response["results"]:
                        if "error" in result:
                            cdebug("SNAP RESULT: arch={} channel={} error.code={}".format(arch, result["instance-key"], result["error"]["code"]))
                            continue
                        # XXX: should be checking for individual channel errors.
                        cdebug("SNAP RESULT: channel={} version={} revision={} released-at={}".format(result["instance-key"], result["snap"]["version"], result["snap"]["revision"], result["released-at"]))
                        entry = {}
                        entry['version'] = result["snap"]["version"]
                        entry['revision'] = result["snap"]["revision"]
                        entry['released-at'] = result["released-at"]
                        channels[(arch, result["instance-key"])] = entry
                        revisions[entry["revision"]] = entry

            except HTTPError as e:
                # Error 404 is returned if the snap has never been published
                # to the given channel.
                store_err = False
                ret_body = e.read().decode()
                cdebug("SNAP ERROR: ret_body={}".format(ret_body))
                if hasattr(e, 'code') and e.code == 404:
                    ret_data = json.loads(ret_body)
                    cinfo("SNAP 404: {}".format(ret_data))
                    for error in ret_data.get('error-list', []):
                        cinfo("SNAP ERROR: code={} message={}".format(error['code'], error['message']))
                        if error['code'] == 'resource-not-found':
                            store_err = True
                    # XXX: convert to something sane in the above loop.
                    store_err_str = 'has no published revisions in the given context'
                    if store_err_str in ret_body:
                        store_err = True
                if not store_err:
                    raise SnapStoreError('failed to retrieve store URL (%s)' % str(e))
            except (URLError, KeyError) as e:
                raise SnapStoreError('failed to retrieve store URL (%s: %s)' %
                                     (type(e), str(e)))
        return channels, revisions

    def channel_map(s):
        if s._channel_map is None:
            s._channel_map, s._revision_map = s.channel_map_lookup()
        return s._channel_map

    def revision_map(s):
        if s._revision_map is None:
            s._channel_map, s._revision_map = s.channel_map_lookup()
        return s._revision_map

    # channel_version
    #
    def channel_version(s, arch, channel):
        key = (arch, channel)
        return s.channel_map().get(key, {}).get('version', None)

    # channel_revision
    #
    def channel_revision(s, arch, channel):
        key = (arch, channel)
        return s.channel_map().get(key, {}).get('revision', None)

    # revision_version
    #
    def revision_version(s, revision):
        return s.revision_map().get(revision, {}).get("version", None)

    def _last_published(self, data):
        last_published = None
        publish_to = self.snap.publish_to
        promote_to = self.snap.promote_to
        if publish_to is not None and promote_to is not None:
            for arch, tracks in publish_to.items():
                for track in tracks:
                    for risk in promote_to:
                        channel = "{}/{}".format(track, risk)
                        #print("?", self.snap.name, arch, channel)
                        key = (arch, channel)
                        if key not in data:
                            continue

                        # Convert the iso8601 format timestring into one
                        # which strptime actually can parse.
                        released_at = data[key]['released-at']
                        released_at = released_at[:-3] + released_at[-2:]
                        #print("D?", released_at)

                        date_published = datetime.strptime(released_at,
                            "%Y-%m-%dT%H:%M:%S.%f%z")
                        cinfo("SNAP-RELEASED-AT {} -> {} > {}".format(data[key]['released-at'], date_published, last_published))
                        if last_published is None or date_published > last_published:
                            last_published = date_published

        return last_published

    @property
    def last_published(self):
        return self._last_published(self.channel_map())


# SnapDebs
#
class SnapDebs:
    """
    Class representing a snap of a kernel from debian packages.
    """
    def __init__(s, shankbug):
        s.bug = shankbug

        s.snap_info = None
        s._snap_store = None
        s._git_repo = False
        s.is_v2 = False
        s.is_v2v = False

        if s.bug.variant == 'snap-debs':
            # We take our version from the debs we are snapping up
            # so grab the version data from there and update the bug
            # title to match as needed.
            #if not s.bug.is_derivative_package:
            #    raise SnapError("snap-debs requires a parent tracker pointing at the deb builds to be snapped")

            # Default to our own version information.
            s.bug.version_from_title()

            # Handle version changes.
            parent_wb = s.bug.master_bug
            clamp = s.bug.clamp('parent')
            if parent_wb is not None and parent_wb.version != clamp:
                cinfo("parent tracker version has changed resetting snap versioning {} -> {}".format(clamp, parent_wb.version))
                s.bug.version = parent_wb.version
                s.bug.clamp_assign('parent', parent_wb.version)
            clamp = s.bug.clamp('self')
            if s.bug.version != clamp:
                cinfo("tracker version has changed resetting tracker {} -> {}".format(clamp, s.bug.version))
                s.bug.clamp_assign('self', s.bug.version)
                # XXX: likely we should be pulling tasks back here.
                for taskname, task in s.bug.tasks_by_name.items():
                    if taskname.startswith('snap-') and task.status != 'New':
                        cinfo("pulling {} to New".format(taskname))
                        task.status = 'New'

            # Expect this bug to have the data we need to identify the
            # snap.
            snap_name = s.bug.bprops.get('snap-name')
            if snap_name is None:
                raise SnapError("snap-name not provided")
            s.name = snap_name
            source = s.bug.source
            if source is not None:
                s.snap_info = source.lookup_snap(snap_name)
                if s.snap_info is None:
                    raise SnapError("{}: snap does not appear in kernel-series for that source".format(snap_name))

            s.bug.update_title(suffix='snap-debs snap:' + snap_name)

            # V2: attempt to locate the "edge" "stream=1" recipe.
            recipe_edge = s.lookup_recipe_v2("edge", stream=1, probe_2v=True)
            if recipe_edge is not None:
                s.is_v2 = True
                s.is_v2v = True
            else:
                recipe_edge = s.lookup_recipe_v2("edge", stream=1)
                if recipe_edge is not None:
                    s.is_v2 = True
            cdebug("SNAP is_v2={} is_v2v={}".format(s.is_v2, s.is_v2v))

            # Use our parents stream as soon as it comes ready.  Match our parent in
            # the normal form.
            if s.is_v2 and parent_wb is not None and parent_wb.built_in != s.bug.built_in:
                s.bug.built_in = parent_wb.built_in
                cinfo("APW: STREAM2 -- SNAP stream set to {}".format(s.bug.built_in))

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

            # Our name is our snap name.
            if s.snap_info is not None:
                s.name = s.snap_info.name

        else:
            s.name = s.bug.name

        # Pick up versions from our bug as needed.
        s.series = s.bug.series
        s.version = s.bug.version
        s.source = s.bug.source
        s.kernel = s.bug.kernel
        s.abi = s.bug.abi

    @property
    def snap_store(s):
        if s._snap_store is None:
            s._snap_store = SnapStore(s.snap_info)
        return s._snap_store

    @centerleave
    def recover_request_v2(self, handle):
        if handle is None:
            return None
        lp = ctx.lp
        recipe = lp.load(handle)
        return recipe

    def lookup_recipe_v2(self, risk, stream=None, probe_2v=None):
        if stream is None:
            stream = self.bug.built_in
        if probe_2v is None:
            probe_2v = self.is_v2v

        if stream is None:
            return None

        risk_clamp = "edge" if risk == "edge" else "beta"
        variant = "+2v" if probe_2v else "+2"
        # mantic--linux--pc-kernel--edge--1
        recipe_name = "{}--{}--{}--{}--{}{}".format(
            self.bug.series,
            self.bug.source.name,
            self.name,
            risk_clamp,
            stream,
            variant,
        )
        cdebug("lookup_recipe_manual({}) recipe_name={}".format(risk, recipe_name))

        # Lookup our team snap recipies.
        lp = ctx.lp
        # XXX: we should really move these to the right team instead.
        if self.bug.source.series.esm:
            owner = lp.people['canonical-kernel-esm']
        else:
            path = '~' + self.snap_info.repo.url.split('~')[1]
            lp_repo = lp.git_repositories.getByPath(path=path)
            if lp_repo is None:
                return None
            owner = lp_repo.owner
        cdebug("lookup_recipe_manual({}) owner={}".format(risk, owner))

        try:
            lp_snap = lp.snaps.getByName(owner=owner, name=recipe_name)
        except NotFound as e:
            lp_snap = None
        cdebug("lookup_recipe_manual({}) lp_snap={}".format(risk, lp_snap))

        return lp_snap

    @centerleave
    def snap_request(self, risk):
        recipe = self.lookup_recipe_v2(risk)
        cinfo("snap_request: lookup_recipe_v2({}) = {}".format(risk, recipe))
        if recipe is None:
            return False

        # Request a snap build and return the request.
        request = recipe.requestBuilds(
            archive=recipe.auto_build_archive,
            pocket=recipe.auto_build_pocket,
            channels=recipe.auto_build_channels,
        )
        cinfo("snap_request: recipe.requestBuilds(archive={}, pocket={}, channels={}) = {}".format(
            recipe.auto_build_archive,
            recipe.auto_build_pocket,
            recipe.auto_build_channels,
            request,
        ))
        if request is None:
            return None

        request = request.self_link.split("/devel/")[-1]
        return request

    @property
    def last_published(self):
        return self.snap_store.last_published

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
        lp = ctx.lp
        ks_snap = s.snap_info

        # Find the snap repository in launchpad.
        path = '~' + ks_snap.repo.url.split('~')[1]
        lp_repo = lp.git_repositories.getByPath(path=path)
        lp_ref = lp_repo.getRefByPath(path='refs/heads/' + ks_snap.repo.branch)
        cinfo("snap_status: ks_snap={} sha={} lp_repo={} lp_ref={}".format(ks_snap, sha, lp_repo, lp_ref))

        # Lookup our team snap recipies.
        if s.bug.source.series.esm:
            snap_team = 'canonical-kernel-esm'
        else:
            snap_team = 'canonical-kernel-snaps'
        cks = lp.people[snap_team]
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

        # Assume we are incomplete if there are any build-requests pending.
        if len(lp_snap.pending_build_requests) != 0:
            status.add('BUILD-PENDING')

        # Assume we are incomplete if there are any build pending without a
        # revision-id as we have no way to know which revision they will refer
        # supply for once built.
        for build in lp_snap.pending_builds:
            cinfo("snap build pending: {} {} {} {}".format(build, build.arch_tag, build.buildstate, build.revision_id))
            if build.revision_id is None:
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

            if build.buildstate == 'Successfully built':
                if build.store_upload_status == 'Unscheduled':
                    status.add('UPLOAD-DISABLED')

                elif build.store_upload_status == 'Pending':
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
                'BUILD-FAILED', 'UPLOAD-FAILED', 'UPLOAD-DISABLED',                  # Errors: earliest first
                'BUILD-PENDING', 'BUILD-DEPWAIT', 'BUILD-ONGOING', 'UPLOAD-PENDING', # Pending: earliest first
                'UPLOAD-COMPLETE', 'BUILD-COMPLETE',                                 # Finished: latest first
                'BUILD-MISSING'):
            if state in status:
                break

        # XXX: enable when snap builds are not scheduling.
        #if state == "BUILD-MISSING":
        #    s.bug.reasons['snap-start'] = "Stalled -s {}".format(lp_snap)

        cdebug("snap_status: build/upload stati {} {}".format(status, state))

        return state

    # snap_validate_request
    #
    @centerleave
    def snap_validate_request(self, request, version):
        request = self.recover_request_v2(request)

        # If the request is not yet complete return inconclusive result.
        if request is None:
            cinfo("snap_validate_request: no request")
            return None
        if request.status != "Completed":
            cinfo("snap_validate_request: request.status={}".format(request.status))
            return None

        publish_to = self.snap_info.publish_to
        good = True
        for build in request.builds:
            if build.arch_tag not in publish_to:
                self.bug.flag_assign("error-snap-extra-arch", True)
                continue
            rev = build.store_upload_revision
            if rev is None:
                cinfo("snap_validate_request: build={} no rev recorded".format(build))
                return None
            rev_version = self.snap_store.revision_version(rev)
            cinfo("snap_validate_request: arch={} version={} rev={} rev_version={}".format(build.arch_tag, version, rev, rev_version))
            if rev_version != version:
                good = False

        return good

    # snap_status_request
    #
    @centerleave
    def snap_status_request(s, request):
        request = s.recover_request_v2(request)

        # If the request is not yet implemented report it.
        if request is None:
            return "REQUEST-MISSING"
        if request.status != "Completed":
            return "REQUEST-" + request.status.upper()

        # Run the list of builds for this snap and see if we have one for the sha
        # we care about.  If so take the first build in each arch as the current
        # status.  Accumulate the build and upload stati into a single status
        # for this snap build and upload phase.
        status = set()
        status.add('BUILD-MISSING')

        for build in request.builds:
            cinfo("snap build complete: {} {} {} {}".format(build, build.arch_tag, build.buildstate, build.revision_id))

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

            if build.buildstate == 'Successfully built':
                if build.store_upload_status == 'Unscheduled':
                    status.add('UPLOAD-DISABLED')

                elif build.store_upload_status == 'Pending':
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
                'BUILD-FAILED', 'UPLOAD-FAILED', 'UPLOAD-DISABLED',                  # Errors: earliest first
                'BUILD-PENDING', 'BUILD-DEPWAIT', 'BUILD-ONGOING', 'UPLOAD-PENDING', # Pending: earliest first
                'UPLOAD-COMPLETE', 'BUILD-COMPLETE',                                 # Finished: latest first
                'BUILD-MISSING'):
            if state in status:
                break

        # XXX: enable when snap builds are not scheduling.
        #if state == "BUILD-MISSING":
        #    s.bug.reasons['snap-start'] = "Stalled -s {}".format(lp_snap)

        cdebug("snap_status_request: build/upload stati {} {}".format(status, state))

        return state

    @centerleave
    def is_in_risk_request(self, risk, request):
        request = self.recover_request_v2(request)
        risk_branch = risk
        if self.bug.built_in != 1 and risk != "stable":
            risk_branch += "/stream{}".format(self.bug.built_in)

        # Identify expected revisions.
        revisions = {}
        if request is not None:
            for build in request.builds:
                revisions[build.arch_tag] = build.store_upload_revision
                cinfo("is_in_risks_request: arch={} revision={}".format(build.arch_tag, build.store_upload_revision))

        # Scan and report on revision missmatches.
        good = True
        partial = False
        broken = []
        publish_to = self.snap_info.publish_to
        #promote_to = self.snap_info.promote_to
        for arch in sorted(publish_to):
            expected_revision = revisions.get(arch)
            cinfo("is_in_risks_request: arch={} expected_revision={}".format(arch, expected_revision))
            if expected_revision is None:
                good = False
            for track in publish_to[arch]:
                channel = "{}/{}".format(track, risk_branch)
                revision = self.snap_store.channel_revision(arch, channel)
                cinfo("is_in_risks_request: arch={} channel={} revision={}".format(arch, channel, revision))
                entry = "arch={}:channel={}".format(arch, channel)
                if expected_revision is not None:
                    entry += ":rev={}".format(expected_revision)
                if revision is not None and expected_revision != revision:
                    entry += ":badrev={}".format(revision)
                if expected_revision != revision:
                    good = False
                if revision is not None and expected_revision == revision:
                    partial = True
                broken.append(entry)

        return good, partial, broken

    @centerleave
    def revisions_request(self, request):
        request = self.recover_request_v2(request)

        # Identify expected revisions.
        revisions = {}
        if request is not None:
            for build in request.builds:
                revisions[build.arch_tag] = build.store_upload_revision
                cinfo("is_in_risks_request: arch={} revision={}".format(build.arch_tag, build.store_upload_revision))
        return revisions

    def update_version(self, risk, version):
        # Usage: $0 <tracker> <repo-url> <repo-branch> <build-branch> <version>

        cmd = [
            os.path.join(os.path.dirname(__file__), "..", "snap-set-version"),
            str(self.bug.lpbug.id),
            self.snap_info.repo.url,
            self.snap_info.repo.branch,
            risk,
            str(self.bug.built_in),
            version,
        ]
        cinfo("repo_update_version: cmd={}".format(cmd))
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in proc.stdout.split(b"\n"):
            cinfo("repo_update_version: {}".format(line))

        return proc.returncode == 0
