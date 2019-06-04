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

                # 1: Packaging
                if taskname.startswith('prepare-package'):
                    (task_section, task_text) = (1, 'Packaging')

                # 2: Promote to Proposed
                elif (taskname in ('promote-to-proposed',
                                   'promote-signing-to-proposed',
                                   'snap-release-to-edge',
                                   'snap-release-to-beta')
                    ):
                    (task_section, task_text) = (2, 'Promote to Proposed')

                # 3: Testing
                elif (taskname.endswith('-testing') or
                      taskname in ('snap-release-to-candidate')
                    ):
                    (task_section, task_text) = (3, 'Testing')

                # 4: Signoffs
                elif taskname.endswith('-signoff'):
                    (task_section, task_text) = (4, 'Signoff')

                # 5: Release
                elif taskname in ('promote-to-updates', 'promote-to-release',
                         'snap-release-to-stable'):
                    (task_section, task_text) = (5, 'Release')

                # 6: Security
                elif taskname in ('promote-to-security'):
                    (task_section, task_text) = (6, 'Security')

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

            if phase_text is not None:
                s.bug.phase = phase_text

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

            # All is completed so we can finally close out this workflow bug.
            s.task.status = 'Fix Released'
            msgbody = 'All tasks have been completed and the bug is being set to Fix Released\n'
            s.bug.add_comment('Workflow done!', msgbody)
            break

        cleave(s.__class__.__name__ + '._complete (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
