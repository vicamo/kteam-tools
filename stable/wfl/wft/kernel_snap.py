from datetime                                   import datetime, timedelta, timezone

from wfl.git_tag                                import GitTagsSnap
from wfl.log                                    import center, cleave, cinfo, cerror, cdebug
from wfl.snap                                   import SnapStoreError
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
        # our master bug.  Add a direct pointer to whichever bug that is.
        s.debs_bug = bug
        if s._bug.variant == 'snap-debs':
            master_bug = bug.master_bug
            if master_bug is not None:
                s.debs_bug = master_bug

        cleave(s.__class__.__name__ + '.__init__')

    def do_verify_release(s, risk):
        center(s.__class__.__name__ + '.do_verify_release')
        retval = False

        try:
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
                s.task.reason = 'Pending -- {}'.format(issue)
                cinfo('    {}'.format(issue), 'yellow')
        except SnapStoreError as e:
            cerror('    failed to query snap store (%s)' % str(e))
            s.task.reason = 'Stalled -- snap store query failed ({})'.format(str(e))

        cleave(s.__class__.__name__ + '.do_verify_release')
        return retval

    @property
    def oldest_tracker(s):
        # The target trackers are returned in cycle order.
        target_trackers = s.bug.target_trackers
        cinfo(s.bug.target_trackers)
        for tracker_nr, tracker_data in target_trackers:
            if tracker_nr == str(s.bug.lpbug.id):
                return True
            return False


class SnapPrepare(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SnapPrepare, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_prepared
        s.jumper['Triaged']       = s._verify_prepared
        s.jumper['In Progress']   = s._verify_prepared
        s.jumper['Fix Committed'] = s._verify_prepared

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # The snap should be released to edge and beta channels after
        # the package hits -proposed.
        while not retval:
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
            if not s.oldest_tracker:
                cinfo('    snap has an older active tracker', 'yellow')
                s.task.reason = 'Stalled -- tracker for earlier spin still active'
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
            # Check the tags and tip are prepared and pushed.
            git_repo = s.bug.snap.git_repo
            version = git_repo.tip_version
            if version != s.bug.version:
                s.task.reason = 'Pending -- snap package tags missing'
                s.bug.refresh_at(datetime.now(timezone.utc) + timedelta(minutes=15),
                    '{} {} polling for tag'.format(
                    s.bug.snap.name, s.bug.version))

                break

            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True
            break

        cleave(s.__class__.__name__ + '._verify_prepared (%s)' % (retval))
        return retval


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
                if not s.oldest_tracker:
                    cinfo('    snap has an older active tracker', 'yellow')
                    s.task.reason = 'Stalled -- tracker for earlier spin still active'
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
            if s.bug.tasks_by_name['snap-release-to-edge'].status not in ('Fix Committed', 'Fix Released'):
                cinfo('    task snap-release-to-edge is not \'Fix Released\'', 'yellow')
                break

            if s.debs_bug.tasks_by_name['promote-to-proposed'].status != 'Fix Released':
                cinfo('    task promote-to-proposed is not \'Fix Released\'', 'yellow')
                s.task.reason = 'Holding -- waiting for debs to promote-to-proposed'
                break

            # Check if this is the oldest tracker for this target.
            if not s.oldest_tracker:
                cinfo('    snap has an older active tracker', 'yellow')
                s.task.reason = 'Stalled -- tracker for previous spin still active'
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
            if s.bug.tasks_by_name['snap-release-to-beta'].status != 'Fix Released':
                cinfo('    task snap-release-to-beta is not \'Fix Released\'', 'yellow')
                break

            if (s.bug.tasks_by_name.get('snap-certification-testing', None) is not None
                    and s.bug.tasks_by_name['snap-certification-testing'].status not in ['Fix Released', 'Invalid']):
                cinfo('    task snap-certification-testing is neither \'Fix Released\' nor \'Invalid\'', 'yellow')
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
            if s.bug.tasks_by_name['snap-release-to-candidate'].status != 'Fix Released':
                cinfo('    task snap-release-to-candidate is not \'Fix Released\'', 'yellow')
                break

            if (s.bug.tasks_by_name.get('snap-qa-testing', None) is not None
                    and s.bug.tasks_by_name['snap-qa-testing'].status not in ['Fix Released', 'Invalid']):
                cinfo('    task snap-qa-testing is neither \'Fix Released\' nor \'Invalid\'', 'yellow')
                break

            promote_to = 'promote-to-updates'
            if 'promote-to-release' in s.debs_bug.tasks_by_name:
                promote_to = 'promote-to-release'
            if s.debs_bug.tasks_by_name[promote_to].status in ['New', 'Incomplete']:
                cinfo('    task promote-to-updates/release is \'{}\''.format(s.debs_bug.tasks_by_name[promote_to].status), 'yellow')
                s.task.reason = 'Holding -- waiting for debs to {}'.format(promote_to)
                break

            if (s.debs_bug.tasks_by_name[promote_to].status == 'Invalid' and
                    'promote-to-security' in s.bug.tasks_by_name and
                    s.bug.tasks_by_name['promote-to-security'].status not in ['Fix Released', 'Invalid']):
                cinfo('    task promote-to-updates/release is \'Invalid\' and promote-to-security is neither \'Fix Released\''
                      ' nor \'Invalid\'', 'yellow')
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
            s.task.reason = 'Stalled -- testing FAILED'
        else:
            s.task.reason = 'Ongoing -- testing in progress'

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
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['Fix Committed'] = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        # We only care about setting the task to 'Confirmed' when the
        # snap is published to the beta channel.
        if s.bug.tasks_by_name['snap-release-to-beta'].status == 'Fix Released':
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

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -- testing FAILED'
        else:
            s.task.reason = 'Ongoing -- testing in progress'

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
