from datetime                                   import datetime, timedelta, timezone

from wfl.bug                                    import WorkflowBugTaskError
from wfl.git_tag                                import GitTagsSnap, GitTagError
from wfl.log                                    import center, cleave, cinfo, cerror, cdebug, centerleave
from wfl.snap                                   import SnapStoreError
from wfl.test_observer                          import TestObserverResults, TestObserverError
from wfl.errors                                 import WorkflowCrankError
from .base                                      import TaskHandler


class KernelSnapBase(TaskHandler):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(KernelSnapBase, s).__init__(lp, task, bug)

        # For a legacy combo variant the debs from which we will make a snap
        # are associated with this bug.  For a snap variant they come from
        # our parent tracker.  Add a direct pointer to whichever bug that is.
        if s._bug.variant == 'snap-debs':
            master_bug = bug.master_bug
            while master_bug is not None and master_bug.variant == "snap-debs":
                master_bug = master_bug.master_bug
            s.debs_bug = master_bug
            if master_bug != bug.master_bug:
                cinfo("cascaded snap-debs tracker parent={} debs_tracker={}".format(
                    bug.master_bug, master_bug))
        else:
            s.debs_bug = bug

        cleave(s.__class__.__name__ + '.__init__')

    def do_verify_release(s, risk):
        center(s.__class__.__name__ + '.do_verify_release')
        retval = False

        snap_build = "edge" if risk == "edge" else "beta"

        try:
            if s.is_v2:
                request = s.bug.group_get("snap-prepare", snap_build)
                good, partial, reasons = s.bug.snap.is_in_risk_request(risk, request)
            else:
                good, partial, reasons = s.bug.snap.is_in_tracks(risk)
            # Everything is fully published into all expected tracks.
            if good is True:
                if s.task.status != 'Fix Released':
                    s.task.status = 'Fix Released'
                    s.task.timestamp('finished')
                    retval = True
            else:
                # Something is published into some of the tracks at least.
                if partial is True:
                    if s.task.status != 'Fix Committed':
                        s.task.status = 'Fix Committed'
                        retval = True
                else:
                    if s.task.status == 'Fix Released':
                        s.task.status = 'New'
                        retval = True
                issue = 'snap {} not in expected channel(s): {}'.format(s.bug.snap.name, ' '.join(reasons))
                s.task.reason = 'Pending -s {}'.format(issue)
                cinfo('    {}'.format(issue), 'yellow')
                s.bug.monitor_add({
                    'type': 'snap-publishing',
                    #'snap': s.bug.snap.name,
                    'last-published': s.bug.snap.last_published})
        except SnapStoreError as e:
            cerror('    failed to query snap store (%s)' % str(e))
            s.task.reason = 'Stalled -- snap store query failed ({})'.format(str(e))

        cleave(s.__class__.__name__ + '.do_verify_release')
        return retval

    def oldest_tracker(s):
        # The target trackers are returned in cycle order.
        target_trackers = s.bug.target_trackers
        cinfo(s.bug.target_trackers)
        for tracker_nr, tracker_data in target_trackers:
            cinfo("APW: {} {}".format(tracker_nr, tracker_data.get("cycle", "??")))
            if tracker_nr == str(s.bug.lpbug.id):
                break
            stream = tracker_data.get('built', {}).get('route-entry')
            if stream is not None and stream != s.bug.built_in:
                continue
            return tracker_nr, "LP: #{} {}".format(tracker_nr, tracker_data.get("cycle", "unknown"))
        return None, None

    @property
    def is_v2(self):
        return self.bug.snap is not None and self.bug.snap.is_v2

    @property
    def is_v2v(self):
        return self.bug.snap is not None and self.bug.snap.is_v2v


class SnapPrepareV1(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super().__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_prepared
        s.jumper['Triaged']       = s._verify_prepared
        s.jumper['In Progress']   = s._verify_prepared
        s.jumper['Fix Committed'] = s._verify_prepared

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    def evaluate_status(s, state):
        # We ARE aware of invalid bugs.
        return s.jumper[state]()

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # The snap should be released to edge and beta channels after
        # the package hits -proposed.
        while not retval:
            if s.debs_bug is not None:
                if s.debs_bug.task_status('promote-to-proposed') != 'Fix Released':
                    cinfo('    task promote-to-proposed is not \'Fix Released\'', 'yellow')
                    s.task.reason = 'Holding -b Not ready to be cranked'
                    break

                if s.debs_bug.task_status('promote-signing-to-proposed') not in ('Fix Released', 'Invalid'):
                    cinfo('    task promote-signing-to-proposed is not \'Fix Released\' or \'Invalid\'', 'yellow')
                    s.task.reason = 'Holding -b Not ready to be cranked'
                    break

            # Attempt to apply replaces as we are ready to promote.
            s.bug.dup_replaces()

            # Check if this is the oldest tracker for this target.
            older, reason = s.oldest_tracker()
            if older is not None:
                cinfo('    snap has an older active tracker', 'yellow')
                s.task.reason = 'Stalled -- tracker for earlier spin still active, ' + reason
                s.bug.monitor_add({
                    "type": "tracker-modified",
                    "watch": str(older)})
                break

            # Are we blocked.
            block = s.bug.source_block_present()
            if block is not None:
                cinfo('    snap is in blocked via ' + block, 'yellow')
                s.task.reason = 'Stalled -- blocked via ' + block
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_prepared
    #
    def _verify_prepared(s):
        center(s.__class__.__name__ + '._verify_prepared')
        retval = False

        while not retval:
            if s.task.status not in ('Confirmed'):
                break

            pull_back = False
            older, reason = s.oldest_tracker()
            if older is not None:
                cinfo('            A previous cycle tracker is active pulling back from Confirmed', 'yellow')
                pull_back = True
            block = s.bug.source_block_present()
            if block is not None:
                cinfo('            Blocked via {} pulling back from Confirmed'.format(block), 'yellow')
                pull_back = True
            if s.debs_bug is not None:
                if s.debs_bug.task_status('promote-to-proposed') != 'Fix Released':
                    cinfo('    task promote-to-proposed is not \'Fix Released\' pulling back from Confirmed', 'yellow')
                    pull_back = True
                    break
                if s.debs_bug.task_status('promote-signing-to-proposed') not in ('Fix Released', 'Invalid'):
                    cinfo('    task promote-signing-to-proposed is not \'Fix Released\' or \'Invalid\' pulling back from Confirmed', 'yellow')
                    pull_back = True
                    break

            if pull_back:
                s.task.status = 'New'
                retval = True

            break

        while not retval:
            # Check the tags and tip are prepared and pushed.
            git_repo = s.bug.snap.git_repo
            try:
                version = git_repo.tip_version
            except GitTagError as e:
                raise WorkflowCrankError("unable to fetch tag information -- {}".format(e.args[0]))

            if version != s.bug.version and (version is None or (s.bug.version is not None and not version.startswith(s.bug.version + '.'))):
                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -b Snap ready to be cranked'
                else:
                    s.task.reason = 'Pending -- snap package tags missing'
                s.bug.refresh_at(datetime.now(timezone.utc) + timedelta(minutes=20),
                    '{} {} polling for tag'.format(
                    s.bug.snap.name, s.bug.version))
                break

            # We have a tag so we are at least Fix Committed.
            # NOTE: we do not break so we can upgrade to later states.
            if s.task.status not in ('Fix Committed', 'Fix Released'):
                s.task.status = 'Fix Committed'
                retval = True

            # Check for a snap build in this version.
            sha = git_repo.lookup_version(version)
            snap_status = s.bug.snap.snap_status(sha)
            if snap_status == 'SNAP-MISSING':
                pass

            elif snap_status != 'UPLOAD-COMPLETE':
                status_text = ' '.join([x.capitalize() for x in snap_status.split('-')])
                s.task.reason = 'Pending -- snap package build/upload not complete ({})'.format(status_text)
                s.bug.refresh_at(datetime.now(timezone.utc) + timedelta(minutes=20),
                    '{} {} polling for snap build/upload to complete'.format(
                    s.bug.snap.name, s.bug.version))
                break

            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True
            break

        cleave(s.__class__.__name__ + '._verify_prepared (%s)' % (retval))
        return retval


class SnapPrepareManual(KernelSnapBase):

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super().__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_prepared
        s.jumper['Triaged']       = s._verify_prepared
        s.jumper['In Progress']   = s._verify_prepared
        s.jumper['Fix Committed'] = s._verify_prepared
        s.jumper['Incomplete']    = s._verify_prepared

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    def evaluate_status(s, state):
        # We ARE aware of invalid bugs.
        return s.jumper[state]()

    # _verify_prepared
    #
    @centerleave
    def _verify_prepared(s):
        retval = False

        request = s.bug.group_get("snap-prepare", s.snap_build)
        if request is None:
            if s.is_v2v:
                if not s.bug.snap.update_version(s.snap_build, s.bug.version):
                    cinfo('    unable to set snap version', 'yellow')
                    s.task.reason = 'Stalled -- unable to set snap version'
                    return

            request = s.bug.snap.snap_request(s.snap_build)
            s.bug.group_set("snap-prepare", s.snap_build, request)

        while not retval:
            snap_status = s.bug.snap.snap_status_request(request)
            # XXX: why is this not an error?
            if snap_status == 'SNAP-MISSING':
                pass

            elif snap_status != 'UPLOAD-COMPLETE':
                status_text = ' '.join([x.capitalize() for x in snap_status.split('-')])
                s.task.reason = 'Pending -- snap package build/upload not complete ({})'.format(status_text)
                s.bug.refresh_at(datetime.now(timezone.utc) + timedelta(minutes=20),
                    '{} {} polling for snap build/upload to complete'.format(
                    s.bug.snap.name, s.bug.version))
                break

            validate_version = s.bug.version
            cinfo("validate_version={} v2={} v2v={}".format(validate_version, s.is_v2, s.is_v2v))
            validate = s.bug.snap.snap_validate_request(request, validate_version)
            if not validate:
                if validate is None:
                    s.task.reason = 'Stalled -- snap package no revision'
                else:
                    s.task.reason = 'Stalled -- snap package version missmatch'
                if s.task.status != 'Incomplete':
                    s.task.status = 'Incomplete'
                    retval = True
                break

            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True
            break

        return retval


class SnapPrepareUnsigned(SnapPrepareManual):

    snap_build = "edge"

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # This is only relevant to v2 snap recipes.
        if not s.is_v2:
            s.task.status = "Invalid"
            retval = True

        # The snap should be released to edge and beta channels after
        # the package hits -proposed.
        while not retval:
            if s.bug.master_bug is not None:
                if s.bug.master_bug.task_status("snap-release-to-" + s.snap_build) not in ("Fix Released", "Invalid"):
                    cinfo("    task snap-release-to-{} is not 'Fix Released'".format(s.snap_build), 'yellow')
                    s.task.reason = "Holding -b Automated crank waiting (source snap not in {})".format(s.snap_build)
                    break
            if s.debs_bug is not None:
                if s.debs_bug.task_status(':prepare-packages') != 'Fix Released':
                    cinfo('    task :prepare-packages is not \'Fix Released\'', 'yellow')
                    s.task.reason = 'Holding -b Automated crank waiting (packages not built)'
                    break

            # Check if this is the oldest tracker for this target.
            older, reason = s.oldest_tracker()
            if older is not None:
                cinfo('    snap has an older active tracker', 'yellow')
                s.task.reason = 'Stalled -- tracker for earlier spin still active, ' + reason
                s.bug.monitor_add({
                    "type": "tracker-modified",
                    "watch": str(older)})
                break

            # Are we blocked.
            block = s.bug.source_block_present()
            if block is not None:
                cinfo('    snap is in blocked via ' + block, 'yellow')
                s.task.reason = 'Stalled -- blocked via ' + block
                break

            s.task.status = 'In Progress'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval


class SnapPrepareSigned(SnapPrepareManual):

    snap_build = "beta"

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # This is only relevant to v2 snap recipes.
        if not s.is_v2:
            s.task.status = "Invalid"
            retval = True

        # The snap should be released to edge and beta channels after
        # the package hits -proposed.
        while not retval:
            edge_reason = " -b " in (s.bug.task_reason("snap-prepare") or '')
            if s.bug.master_bug is not None:
                if s.bug.master_bug.task_status("snap-release-to-" + s.snap_build) not in ("Fix Released", "Invalid"):
                    cinfo("    task snap-release-to-{} is not 'Fix Released'".format(s.snap_build), 'yellow')
                    if not edge_reason:
                        s.task.reason = "Holding -b Automated crank waiting (source snap not in {})".format(s.snap_build)
                    break
            if s.debs_bug is not None:
                if s.debs_bug.task_status('promote-to-proposed') != 'Fix Released':
                    cinfo('    task promote-to-proposed is not \'Fix Released\'', 'yellow')
                    if not edge_reason:
                        s.task.reason = 'Holding -b Automated crank waiting (packages not in proposed)'
                    break

                if s.debs_bug.task_status('promote-signing-to-proposed') not in ('Fix Released', 'Invalid'):
                    cinfo('    task promote-signing-to-proposed is not \'Fix Released\' or \'Invalid\'', 'yellow')
                    if not edge_reason:
                        s.task.reason = 'Holding -b Automated crank waiting (packages not in proposed)'
                    break

            # Attempt to apply replaces as we are ready to promote.
            s.bug.dup_replaces()

            # Check if this is the oldest tracker for this target.
            older, reason = s.oldest_tracker()
            if older is not None:
                cinfo('    snap has an older active tracker', 'yellow')
                s.task.reason = 'Stalled -- tracker for earlier spin still active, ' + reason
                s.bug.monitor_add({
                    "type": "tracker-modified",
                    "watch": str(older)})
                break

            # Are we blocked.
            block = s.bug.source_block_present()
            if block is not None:
                cinfo('    snap is in blocked via ' + block, 'yellow')
                s.task.reason = 'Stalled -- blocked via ' + block
                break

            # Boot testing will be performed against edge, wait for that to be
            # complete before allowing this to be prepared.
            # XXX: we also need to block promote-to-proposed.
            if s.bug.task_status('boot-testing') not in ['Fix Released', 'Invalid']:
                cinfo('    task boot-testing is neither \'Fix Released\' nor \'Invalid\'', 'yellow')
                break

            s.task.status = 'In Progress'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval


class SnapPrepare:

    def __new__(cls, lp, task, bug):
        if task.bug.snap and task.bug.snap.is_v2:
            return SnapPrepareUnsigned(lp, task, bug)
        return SnapPrepareV1(lp, task, bug)


class SnapReleaseToEdge(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapReleaseToEdge, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_release
        s.jumper['Triaged']       = s._verify_release
        s.jumper['In Progress']   = s._verify_release
        s.jumper['Fix Committed'] = s._verify_release
        s.jumper['Fix Released']  = s._verify_release

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            # Check if this snap is valid in this risk.
            if s.bug.snap.promote_to_risk('edge'):
                break

            cinfo('    snap not valid in beta risk', 'yellow')
            s.task.status = 'Invalid'
            retval = True
            break

        # The snap should be released to edge and beta channels after
        # the package hits -proposed.
        while not retval:
            if s.bug.task_status('snap-prepare') not in ('Fix Released', 'Invalid'):
                cinfo('    task snap-prepare is not \'Fix Released\'', 'yellow')
                break

            # Legacy handling of we have no snap-prepare task.
            elif s.bug.task_status('snap-prepare') == 'Invalid':
                if s.debs_bug.task_status('promote-to-proposed') != 'Fix Released':
                    cinfo('    task promote-to-proposed is not \'Fix Released\'', 'yellow')
                    s.task.reason = 'Holding -- waiting for debs to promote-to-proposed'
                    break

                if s.debs_bug.task_status('promote-signing-to-proposed') not in ('Fix Released', 'Invalid'):
                    cinfo('    task promote-signing-to-proposed is not \'Fix Released\' or \'Invalid\'', 'yellow')
                    s.task.reason = 'Holding -- waiting for debs to promote-signing-to-proposed'
                    break

                # Attempt to apply replaces as we are ready to promote.
                s.bug.dup_replaces()

                # Check if this is the oldest tracker for this target.
                older, reason = s.oldest_tracker()
                if older is not None:
                    cinfo('    snap has an older active tracker', 'yellow')
                    s.task.reason = 'Stalled -- tracker for earlier spin still active, ' + reason
                    s.bug.monitor_add({
                        "type": "tracker-modified",
                        "watch": str(older)})
                    break

            if s.bug.manual_block("snap-release-to-edge"):
                s.task.reason = "Stalled -- promotion manually blocked"
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_release
    #
    def _verify_release(s):
        center(s.__class__.__name__ + '._verify_release')
        retval = s.do_verify_release('edge')
        cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
        return retval


class SnapReleaseToBeta(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapReleaseToBeta, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_release
        s.jumper['Triaged']       = s._verify_release
        s.jumper['In Progress']   = s._verify_release
        s.jumper['Fix Committed'] = s._verify_release
        s.jumper['Fix Released']  = s._verify_release

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            # Check if this snap is valid in this risk.
            if s.bug.snap.promote_to_risk('beta'):
                break

            cinfo('    snap not valid in beta risk', 'yellow')
            s.task.status = 'Invalid'
            retval = True
            break

        # The snap should be released to edge and beta channels after
        # the package hits -proposed.
        while not retval:
            if s.is_v2:
                if s.bug.task_status('snap-prepare-signed') not in ('Fix Released', 'Invalid'):
                    cinfo('    task snap-prepare is not \'Fix Released\'', 'yellow')
                    break
            else:
                if s.bug.tasks_by_name['snap-release-to-edge'].status not in ('Fix Committed', 'Fix Released'):
                    cinfo('    task snap-release-to-edge is not \'Fix Released\'', 'yellow')
                    break

            if s.debs_bug is not None:
                if s.debs_bug.tasks_by_name['promote-to-proposed'].status != 'Fix Released':
                    cinfo('    task promote-to-proposed is not \'Fix Released\'', 'yellow')
                    s.task.reason = 'Holding -- waiting for debs to promote-to-proposed'
                    break

            # Check if this is the oldest tracker for this target.
            older, reason = s.oldest_tracker()
            if older is not None:
                cinfo('    snap has an older active tracker', 'yellow')
                s.task.reason = 'Stalled -- tracker for previous spin still active, ' + reason
                s.bug.monitor_add({
                    "type": "tracker-modified",
                    "watch": str(older)})
                break

            if s.bug.manual_block("snap-release-to-beta"):
                s.task.reason = "Stalled -- promotion manually blocked"
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_release
    #
    def _verify_release(s):
        center(s.__class__.__name__ + '._verify_release')
        retval = s.do_verify_release('beta')
        cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
        return retval


class SnapReleaseToCandidate(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapReleaseToCandidate, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_release
        s.jumper['Triaged']       = s._verify_release
        s.jumper['In Progress']   = s._verify_release
        s.jumper['Fix Committed'] = s._verify_release
        s.jumper['Fix Released']  = s._verify_release

        cleave(s.__class__.__name__ + '.__init__')

    def _ready_for_confirmed(s):
        if s.bug.tasks_by_name['snap-release-to-beta'].status != 'Fix Released':
            cinfo('    task snap-release-to-beta is not \'Fix Released\'', 'yellow')
            return False

        if (s.bug.tasks_by_name.get('snap-certification-testing', None) is not None
                and s.bug.tasks_by_name['snap-certification-testing'].status not in ['Fix Released', 'Invalid']):
            cinfo('    task snap-certification-testing is neither \'Fix Released\' nor \'Invalid\'', 'yellow')
            return False

        if s.bug.manual_block("snap-release-to-candidate"):
            s.task.reason = "Stalled -- promotion manually blocked"
            return False

        return True

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            # Check if this snap is valid in this risk.
            if s.bug.snap.promote_to_risk('candidate'):
                break

            cinfo('    snap not valid in candidate risk', 'yellow')
            s.task.status = 'Invalid'
            retval = True
            break

        # The snap is released to candidate channel after it's on beta channel
        # and passes HW certification tests (or the task is set to invalid).
        while not retval:
            if not s._ready_for_confirmed():
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_release
    #
    def _verify_release(s):
        center(s.__class__.__name__ + '._verify_release')
        retval = False

        if s.task.status == 'Confirmed' and not s._ready_for_confirmed():
            cinfo('    snap no-longer ready for Confirmed, pulling back to New')
            s.task.status = 'New'
            retval = True

        if not retval:
            retval = s.do_verify_release('candidate')

        cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
        return retval


class SnapReleaseToStable(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapReleaseToStable, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_release
        s.jumper['Triaged']       = s._verify_release
        s.jumper['In Progress']   = s._verify_release
        s.jumper['Fix Committed'] = s._verify_release
        s.jumper['Fix Released']  = s._verify_release

        cleave(s.__class__.__name__ + '.__init__')

    def _ready_for_confirmed(s):
        if s.bug.tasks_by_name['snap-release-to-candidate'].status != 'Fix Released':
            cinfo('    task snap-release-to-candidate is not \'Fix Released\'', 'yellow')
            return False

        if (s.bug.tasks_by_name.get('snap-qa-testing', None) is not None
                and s.bug.tasks_by_name['snap-qa-testing'].status not in ['Fix Released', 'Invalid']):
            cinfo('    task snap-qa-testing is neither \'Fix Released\' nor \'Invalid\'', 'yellow')
            return False

        if s.bug.task_status("stakeholder-signoff") not in ("Fix Released", "Invalid"):
            cinfo("    task stakeholder-signoff 'Fix Released' nor 'Invalid'", "yellow")
            s.task.reason = 'Holding -- waiting for signoffs: stakeholder-signoff'
            return False

        if s.debs_bug is not None:
            promote_to = 'promote-to-updates'
            if 'promote-to-release' in s.debs_bug.tasks_by_name:
                promote_to = 'promote-to-release'
            if s.debs_bug.tasks_by_name[promote_to].status in ['New', 'Incomplete']:
                cinfo('    task promote-to-updates/release is \'{}\''.format(s.debs_bug.tasks_by_name[promote_to].status), 'yellow')
                s.task.reason = 'Holding -- waiting for debs to {}'.format(promote_to)
                return False
            if (s.debs_bug.tasks_by_name[promote_to].status == 'Invalid' and
                    'promote-to-security' in s.bug.tasks_by_name and
                    s.bug.tasks_by_name['promote-to-security'].status not in ['Fix Released', 'Invalid']):
                cinfo('    task promote-to-updates/release is \'Invalid\' and promote-to-security is neither \'Fix Released\''
                      ' nor \'Invalid\'', 'yellow')
                s.task.reason = 'Holding -- waiting for debs to promote-to-security'
                return False

        if s.bug.manual_block("snap-release-to-stable"):
            s.task.reason = "Stalled -- promotion manually blocked"
            return False

        return True

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            # Check if this snap is valid in this risk.
            if s.bug.snap.promote_to_risk('stable'):
                break

            cinfo('    snap not valid in stable risk', 'yellow')
            s.task.status = 'Invalid'
            retval = True
            break

        # The snap is released to stable channel after it's on candidate channel,
        # passes QA tests (or the task is set to invalid) and the deb is promoted
        # to -updates or -security.
        while not retval:
            if not s._ready_for_confirmed():
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _verify_release
    #
    def _verify_release(s):
        center(s.__class__.__name__ + '._verify_release')
        retval = False

        if s.task.status == 'Confirmed' and not s._ready_for_confirmed():
            cinfo('    snap no-longer ready for Confirmed, pulling back to New')
            s.task.status = 'New'
            retval = True

        if not retval:
            retval = s.do_verify_release('stable')

        cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
        return retval


class SnapQaTesting(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapQaTesting, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['Fix Committed'] = s._status_check
        s.jumper['Fix Released']  = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # We only care about setting the task to 'Confirmed' when the
        # snap is published to the candidate channel.
        if s.bug.tasks_by_name['snap-release-to-candidate'].status == 'Fix Released':
            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True
        else:
            cinfo('    task snap-release-to-candidate is not \'Fix Released\'', 'yellow')

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')
        retval = False

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -s testing FAILED'
        else:
            s.task.reason = 'Ongoing -s testing in progress'

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval


class SnapCertificationTesting(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapCertificationTesting, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._status_check
        s.jumper['Triaged']       = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['Fix Committed'] = s._status_check
        s.jumper['Fix Released']  = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # We only care about setting the task to 'Confirmed' when the
        # snap is published to the beta channel.
        if s.bug.tasks_by_name['snap-release-to-beta'].status == 'Fix Released':
            if s.bug.built_in not in (None, 1):
                s.task.status = "Invalid"
            else:
                s.task.status = 'Confirmed'
                s.task.timestamp('started')
            retval = True

        else:
            cinfo('    task snap-release-to-beta is not \'Fix Released\'', 'yellow')

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')
        retval = False

        if s.bug.tasks_by_name['snap-release-to-beta'].status != 'Fix Released':
            if s.task.status not in ('Incomplete', 'Fix Released'):
                cinfo('    snap no longer present in beta moving Incomplete', 'yellow')
                s.task.status = 'Incomplete'
                retval = True

        elif 'certification-testing-failed' in s.bug.tags:
            cdebug('Certification Testing tagged as FAIL', 'yellow')
            if s.task.status != 'Confirmed' and s.task.status != 'Incomplete':
                msgbody = 'The bug was tagged as certification-testing-failed\n'
                s.bug.add_comment('Certification Testing FAILURE', msgbody)
                s.task.status = 'Incomplete'
                retval = True

        elif 'certification-testing-passed' in s.bug.tags:
            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        else:
            result = None
            try:
                observer = TestObserverResults()
                result = None
                existing = s.bug.group_get("test-observer", "edge")
                if existing is not None:
                    result = observer.lookup_result(existing)
                    cinfo("TO direct result={}".format(result))
                if result is None:
                    # test-observer reports the _current_ branch not the tested
                    # branch so we cannot use that as a selector.  Therefore we
                    # assume that in the common case that
                    # <snap>:<version>:<revisions> will be unique in space and
                    # time, where it is not we will have only one result and it
                    # is 99% likley the right one.
                    results = observer.lookup_results(
                        "snap",
                        name=s.bug.snap.name,
                        version=s.bug.version,
                    )
                    cinfo("TO snap results={}".format(results))
                    revisions = None
                    if s.is_v2:
                        request = s.bug.group_get("snap-prepare", "beta")
                        revisions = s.bug.snap.revisions_request(request)
                        cinfo("TO revisions={}".format(revisions))

                        for current in results:
                            superset = True
                            for arch, revision in (current.get(":revisions") or {}).items():
                                if revision != revisions.get(arch):
                                    superset = False
                            if superset:
                                cinfo("TO snap match result={}".format(current))
                                s.bug.group_set("test-observer", "beta", current.get("id"))
                                result = current
                                break
                    elif len(results) == 1:
                        result = results[0]
                        cinfo("TO snap first match result={}".format(result))
                        s.bug.group_set("test-observer", "beta", result.get("id"))
                if result is not None:
                    status = result.get("status", "UNKNOWN")
                    tstatus = {
                        "UNDECIDED": "Triaged",
                        "APPROVED": "Fix Released",
                    }.get(status, "Incomplete")
                    assignee = (result.get("assignee") or {}).get("launchpad_handle")
                    if status == "UNDECIDED" and assignee is not None:
                        tstatus = "In Progress"

                    # If we have a missmatch on the architectures then move to failure...
                    if revisions is not None and revisions != result.get(":revisions"):
                        cinfo("TO snap match missmatched architectures {} expected {}".format(result.get(":revisions"), revisions))
                        s.bug.reasons['test-observer'] = "Stalled -- Warning testing missing architectures"

                    # Assign the task if we have an owner and move it if the status has changed.
                    if s.task.assignee is None or s.task.assignee.name != assignee:
                        lp_assignee = s.lp.people[assignee] if assignee is not None else s.lp.people["canonical-hw-cert"]
                        s.task.assignee = lp_assignee
                    cinfo("TO snap match result-status={} task-status={}".format(status, tstatus))
                    if s.task.status != tstatus:
                        s.task.status = tstatus
                        retval = True
            except TestObserverError as e:
                s.bug.refresh_at(
                    datetime.now(timezone.utc) + timedelta(minutes=30),
                    "polling due to test-observer failure",
                )
                raise WorkflowBugTaskError(str(e))

            if result:
                s.bug.monitor_add({
                    "type": "test-observer",
                    "id": result.get("id"),
                    "status": result.get("status"),
                    "assignee": (result.get("assignee") or {}).get("launchpad_handle"),
                })
            else:
                s.bug.refresh_at(
                    datetime.now(timezone.utc) + timedelta(minutes=30),
                    "polling waiting for initial status",
                )

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -s testing FAILED'
        else:
            s.task.reason = 'Ongoing -s testing in progress'

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval


class SnapPublish(KernelSnapBase):
        '''
        '''

        # __init__
        #
        def __init__(s, lp, task, bug):
            center(s.__class__.__name__ + '.__init__')
            super(SnapPublish, s).__init__(lp, task, bug)

            s.jumper['New']           = s._new
            s.jumper['Confirmed']     = s._verify_release
            s.jumper['Triaged']       = s._verify_release
            s.jumper['In Progress']   = s._verify_release
            s.jumper['Fix Committed'] = s._verify_release

            cleave(s.__class__.__name__ + '.__init__')

        # _new
        #
        def _new(s):
            center(s.__class__.__name__ + '._new')
            retval = False

            # If the snap has update control set up, the original publisher of the snap
            # needs to validate the new snap after it hits the stable channel.
            if s.bug.tasks_by_name['snap-release-to-stable'].status == 'Fix Released':
                s.task.status = 'Confirmed'
                s.task.timestamp('started')
                retval = True
            else:
                cinfo('    task snap-release-to-stable is not \'Fix Released\'', 'yellow')

            cleave(s.__class__.__name__ + '._new (%s)' % (retval))
            return retval

        # _verify_release
        #
        def _verify_release(s):
            center(s.__class__.__name__ + '._verify_release')
            retval = False
            # TODO: check if the snap has been un-gated
            cleave(s.__class__.__name__ + '._verify_release (%s)' % (retval))
            return retval

# vi: set ts=4 sw=4 expandtab syntax=python
