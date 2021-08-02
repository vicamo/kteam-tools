from datetime                           import datetime, timedelta, timezone

from wfl.log                            import center, cleave, cinfo

from .base                              import TaskHandler


class Workflow(TaskHandler):
    '''
    A Task Handler for the propose-to-proposed task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(Workflow, s).__init__(lp, task, bug)

        s.jumper['Confirmed']     = s._complete
        s.jumper['Triaged']       = s._complete
        s.jumper['In Progress']   = s._complete
        s.jumper['Fix Committed'] = s._complete

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    def evaluate_status(s, state):
        return s.jumper[state]()

    PHASE_MAX=10       # Maximum primary phases.
    PHASE_BETWEEN=2    # Maximum number of sub-phases 'between' phases.

    # _complete
    #
    def _complete(s):
        """
        """
        center(s.__class__.__name__ + '._complete')
        retval = False

        # Attempt to apply replaces where the target is inactive.
        s.bug.dup_replaces(inactive_only=True)

        # We will use nominal phases in 0..PHASE_MAX, and sub-phases
        # in the range PHASE_MAX..(PHASE_MAX * PHASE_BETWEEN).
        # Make sure we start higher than that.
        phase_section = s.PHASE_MAX + (s.PHASE_BETWEEN * s.PHASE_MAX) + 1
        phase_text = None
        while True:
            for (taskname, task) in s.bug.tasks_by_name.items():
                if task.status in [ 'Invalid', 'Opinion', 'Fix Released', ]:
                    continue

                (task_section, task_text) = (None, None)

                if s.bug.variant in ('debs', 'combo'):
                    # 1: Packaging
                    if taskname == ':prepare-packages':
                        if task.status == 'Fix Committed':
                            continue
                        (task_section, task_text) = (1, 'Packaging')

                    # 2: Promote to Proposed
                    elif (taskname in ('promote-to-proposed',
                           'promote-signing-to-proposed')):
                        (task_section, task_text) = (2, 'Promote to Proposed')

                    # 3: Testing
                    elif taskname.endswith('-testing'):
                        (task_section, task_text) = (3, 'Testing')

                    # 4: Signoffs
                    elif taskname.endswith('-signoff'):
                        (task_section, task_text) = (4, 'Signoff')

                    # 5: Release
                    elif taskname in ('promote-to-updates',
                            'promote-to-release'):
                        pocket = taskname.split('-')[-1].title()
                        (task_section, task_text) = (
                            5, 'Promote to {}'.format(pocket))

                    # 6: Security
                    elif taskname in ('promote-to-security'):
                        (task_section, task_text) = (6, 'Promote to Security')

                if s.bug.variant == 'snap-debs':
                    # SNAPS:
                    # 1: Promote to Edge
                    if taskname == 'snap-release-to-edge':
                        (task_section, task_text) = (1, 'Promote to Edge')

                    # 2: Promote to Beta
                    elif taskname == 'snap-release-to-beta':
                        (task_section, task_text) = (2, 'Promote to Beta')

                    # 3: Testing
                    elif taskname == 'snap-certification-testing':
                        (task_section, task_text) = (3, 'Certification Testing')

                    # 4: Promote to Candidate
                    elif taskname == 'snap-release-to-candidate':
                        (task_section, task_text) = (4, 'Promote to Candidate')

                    # 5: Testing (again)
                    elif taskname == 'snap-qa-testing':
                        (task_section, task_text) = (5, 'Q/A Testing')

                    # 4: Promote to Candidate
                    elif taskname == 'snap-release-to-stable':
                        (task_section, task_text) = (6, 'Promote to Stable')

                if task_section is None:
                    continue

                # We are looking for the first active phase, but it is possible
                # to be between phases.  Therefore unstarted sections are also
                # interesting.  Jack those so they are less interesting than
                # active tasks.  Jack New slightly more than Confirmed as we
                # care to see Ready in preference to Holding.
                if task.status == 'New':
                    (task_section, task_text) = (s.PHASE_MAX +
                        (task_section * s.PHASE_BETWEEN) + 1,
                        "Holding before " + task_text)
                elif task.status == 'Confirmed':
                    (task_section, task_text) = (s.PHASE_MAX +
                        (task_section * s.PHASE_BETWEEN) + 0,
                        "Ready for " + task_text)

                # Ratchet down to the earliest phase.
                if task_section < phase_section:
                    (phase_section, phase_text) = (task_section, task_text)

            # SAFETY CHECKS:
            #
            # Things which if found are worthy of reporting even if we are not yet trying
            # to close.
            #
            if s.bug.blockers.get('holding-derivative') is not None:
                s.bug.reasons['derivatives-held'] = 'Stalled -- derivative preparation block requested'

            if s.bug.snap:
                (consistent, reasons) = s.bug.snap.channel_revisions_consistent()
                if consistent is False:
                    s.bug.reasons['snap-publishing'] = "snap channel revisions inconsistent {}".format(",".join(reasons))

            if phase_text is not None:
                s.bug.phase = phase_text

            #
            # Calculate interlock blocks.
            #
            if s.bug.snap:
                # Report missing snaps in active states.
                for risk in ('edge', 'beta', 'candidate', 'stable'):
                    task = s.bug.tasks_by_name.get('snap-release-to-' + risk)
                    if task is not None and task.status not in ('New', 'Invalid', 'Fix Released'):
                        s.bug.interlocks['snap-not-in-' + risk] = 'Pending -- snap not yet in ' + risk

                # snap testing should block promote-to-updates.
                for task_name in ('snap-certification-testing', 'snap-qa-testing'):
                    task = s.bug.tasks_by_name.get(task_name)
                    if task is not None and task.status not in ('New', 'Invalid', 'Fix Released'):
                        s.bug.interlocks['hold-promote-to-updates'] = 'Pending -- {} is not complete'.format(task_name)
                        break

                # Block transition to updates if we are not at least in our latest risk
                # level up to and including candidate.
                for risk in ('candidate', 'beta', 'edge'):
                    task = s.bug.tasks_by_name.get('snap-release-to-' + risk)
                    if task is None:
                        continue
                    if task.status not in ('Invalid', 'Fix Released'):
                        s.bug.interlocks['hold-promote-to-updates'] = 'Pending -- snap not yet in ' + risk
                    if task.status != 'Invalid':
                        break

            #
            # Check interlock blocks.
            #
            if s.bug.debs:
                task = s.bug.tasks_by_name.get('promote-to-proposed')
                if task is not None and task.status == 'Fix Released':
                    blocks = s.bug.blockers.get('snap-not-in-beta')
                    if blocks is not None:
                        cinfo("snap-not-in-beta snap-lagging {}".format(blocks))
                        s.bug.reasons['snap-lagging'] = blocks
                for task_name in ('promote-to-updates', 'promote-to-release'):
                    task = s.bug.tasks_by_name.get(task_name)
                    if task is not None and task.status != 'New':
                        blocks = s.bug.block_present('hold-promote-to-updates')
                        if blocks is not None:
                            cinfo("snap-not-in-candidate snap-lagging {}".format(blocks))
                            s.bug.reasons['snap-lagging'] = blocks

                # Check for cascading blocks -- when we use a two phase snap build it should
                # block its parent too.
                # XXX: this is completely the wrong trigger flag.
                if s.bug.swm_config.need_master_in_proposed:
                    blocks = s.bug.block_present('hold-promote-to-updates')
                    if blocks:
                        s.bug.interlocks['hold-promote-to-updates'] = blocks + " (cascaded)"

            #
            # FINAL VALIDATION:
            #
            # In principle all of the tasks are now reporting complete, do final validation
            # of those tasks against each other and against the archive.
            #

            # Check that all tasks are either "Invalid" or "Fix Released"
            tasks_done = True
            for taskname in s.bug.tasks_by_name:
                if s.task == s.bug.tasks_by_name[taskname]:
                    continue
                if s.bug.tasks_by_name[taskname].status not in ['Invalid', 'Fix Released']:
                    tasks_done = False
            if tasks_done is False:
                break

            # Check that the promote-to-updates status matches -updates pocket.
            release_task = None
            if 'promote-to-updates' in s.bug.tasks_by_name:
                updates_task = 'promote-to-updates'
            if 'promote-to-release' in s.bug.tasks_by_name:
                updates_task = 'promote-to-release'
            if release_task is not None:
                promote_to_task = s.bug.tasks_by_name[updates_task]
                if promote_to_task.status == 'Invalid' and s.bug.debs.packages_released:
                    s.task.reason = 'Stalled -- packages have been released but the task set to Invalid'
                    break
                elif promote_to_task.status == 'Fix Released' and not s.bug.debs.packages_released:
                    s.task.reason = 'Stalled -- packages have been released but the task set to Fix Released'
                    break

            if s.bug.debs is not None and s.bug.debs.routing('Security') is not None and 'promote-to-security' in s.bug.tasks_by_name:
                # Check that the promote-to-security status matches -security pocket.
                promote_to_security = s.bug.tasks_by_name['promote-to-security']
                if promote_to_security.status not in ['Invalid', 'Fix Released']:
                    s.task.reason = 'Stalled -- promote-to-security is neither "Fix Released" nor "Invalid" (%s)' % (s.bug.tasks_by_name['promote-to-security'].status)
                    break
                if promote_to_security.status == 'Invalid' and s.bug.debs.packages_released_to_security:
                    s.task.reason = 'Stalled -- packages have been released to security, but the task is set to "Invalid"'
                    break
                elif promote_to_security.status == 'Fix Released' and not s.bug.debs.packages_released_to_security:
                    s.task.reason = 'Stalled -- packages have not been released to security, but the task is set to "Fix Released"'
                    break

                # Check that the promote-to-security status matches that of the security-signoff.
                security_signoff = s.bug.tasks_by_name['security-signoff']
                if promote_to_security.status != security_signoff.status:
                    s.task.reason = 'Stalled -- package promote-to-security status (%s) does not match security-signoff status (%s)' % (promote_to_security.status, security_signoff.status)
                    break

            # Everything looks ok now so move to phase Complete.
            s.bug.phase = 'Complete'

            # Hold this bug open for an hour so that any tooling needing to see
            # it will notice the final state.
            close_time = s.bug.phase_changed.replace(tzinfo=timezone.utc) + timedelta(hours=1)
            now = datetime.now(timezone.utc)
            if now <= close_time:
                s.bug.refresh_at(close_time, 'final close delay')
                cinfo("Complete but holding open until {} is {}".format(close_time, now))
                break

            # All is completed so we can finally close out this workflow bug.
            s.task.status = 'Fix Released'
            msgbody = 'All tasks have been completed and the bug is being set to Fix Released\n'
            s.bug.add_comment('Workflow done!', msgbody)
            s.bug.check_is_valid()
            break

        cleave(s.__class__.__name__ + '._complete (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
