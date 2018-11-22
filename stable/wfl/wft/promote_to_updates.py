
from wfl.log                            import center, cleave, cinfo
from .promoter                          import Promoter

class PromoteToUpdates(Promoter):
    '''
    A Task Handler for the propose-to-proposed task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToUpdates, s).__init__(lp, task, bug)

        s.jumper['New']           = s._ready_for_updates
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion
        s.jumper['Fix Released']  = s._complete
        s.jumper['Invalid']       = s._complete

        cleave(s.__class__.__name__ + '.__init__')

    # _ready_for_updates
    #
    def _ready_for_updates(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_updates')
        retval = False

        while True:

            # The kernels below are in evaluation.  These only get as far
            # as -proposed and will not be promoted further:
            #
            if s.bug.is_proposed_only:
                s.task.status = 'Invalid'
                retval = True
                break

            # There is no point in considering prerequisites before we are
            # at least in proposed.
            if not s.bug.all_in_pocket('Proposed'):
                break

            if not s._prerequisites_released():
                # Note this will set an appropriate reason.
                break

            # If testing is not complete, we are not ready to release.
            if not s._testing_completed():
                break

            if s._kernel_block():
                s.task.reason = 'Holding -- kernel-block/kernel-block-proposed tag present'
                break

            if s._in_blackout():
                s.task.reason = 'Holding -- package in development blackout'
                break

            if not s._stakeholder_signoff_verified():
                s.task.reason = 'Holding -- stakeholder signoff not verified'
                break

            if not s._security_signoff_verified():
                s.task.reason = 'Holding -- security signoff not verified'
                break

            if not s._cycle_ready():
                s.task.reason = 'Holding -- cycle not ready to release'
                break

            if s.bug.is_derivative_package:
                if not s.master_bug_ready():
                    s.task.reason = 'Holding -- master bug not ready for release'
                    break

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._ready_for_updates (%s)' % retval)
        return retval

    # _verify_promotion
    #
    def _verify_promotion(s):
        center(s.__class__.__name__ + '._verify_promotion')
        retval = False

        while not retval:
            if s.task.status not in ('Confirmed'):
                break
            if not s._kernel_block() and not s._in_blackout() and s._cycle_ready():
                break

            if s._kernel_block():
                cinfo('            A kernel-block/kernel-block-proposed on this tracking bug pulling back from Confirmed', 'yellow')
            if s._in_blackout():
                cinfo('            Package now in development blackout pulling back from Confirmed', 'yellow')
            if not s._cycle_ready():
                cinfo('            Cycle no longer ready for release pulling back from Confirmed', 'yellow')

            s.task.status = 'New'

            retval = True
            break

        while not retval:
            # Check if packages were copied to the right pocket->component
            #
            if s._block_proposed():
                s._remove_block_proposed()
                cinfo('            Removing block-proposed tag on this tracking bug', 'yellow')

            if not s.bug.packages_released:
                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -- ready to copy'
                else:
                    s.task.reason = 'Ongoing -- packages not yet published'
                break

            cinfo('    All components are now in -updates', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            s.bug.phase = 'Promoted to updates'
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion (%s)' % retval)
        return retval

    # _complete
    #
    def _complete(s):
        """
        """
        center(s.__class__.__name__ + '._complete')
        retval = False

        while True:
            # Check that the promote-to-updates status matches -updates pocket.
            promote_to_updates = s.bug.tasks_by_name['promote-to-updates']
            #if promote_to_updates.status not in ['Invalid', 'Fix Released']:
            #    break
            if promote_to_updates.status == 'Invalid' and s.bug.packages_released:
                s.task.reason = 'Stalled -- packages have been released but the task set to Invalid'
                break
            elif promote_to_updates.status == 'Fix Released' and not s.bug.packages_released:
                s.task.reason = 'Stalled -- packages have been released but the task set to Fix Released'
                break

            # Since this is the one place where the master, project task is set Fix Released it needs to
            # do more than just look at the promote-to-updates. It needs to also look at promote-to-security,
            # confirm the testing is complete and that security signoff is completed.

            # Confirm we have completed all testing.
            if not s._testing_completed():
                s.task.reason = 'Stalled -- testing not yet complete'
                break

            # Confirm we have a valid security signoff.
            if not s._security_signoff_verified():
                s.task.reason = 'Stalled -- security signoff not verified'
                break

            if not s.bug.is_development_series:
                # Check that the promote-to-security status matches -security pocket.
                promote_to_security = s.bug.tasks_by_name['promote-to-security']
                if promote_to_security.status not in ['Invalid', 'Fix Released']:
                    s.task.reason = 'Stalled -- promote-to-security is neither "Fix Released" nor "Invalid" (%s)' % (s.bug.tasks_by_name['promote-to-security'].status)
                    break
                if promote_to_security.status == 'Invalid' and s.bug.packages_released_to_security:
                    s.task.reason = 'Stalled -- packages have been released to security, but the task is set to "Invalid"'
                    break
                elif promote_to_security.status == 'Fix Released' and not s.bug.packages_released_to_security:
                    s.task.reason = 'Stalled -- packages have not been released to security, but the task is set to "Fix Released"'
                    break

                # Check that the promote-to-security status matches that of the security-signoff.
                security_signoff = s.bug.tasks_by_name['security-signoff']
                if promote_to_security.status != security_signoff.status:
                    s.task.reason = 'Stalled -- package promote-to-security status (%s) does not match security-signoff status (%s)' % (promote_to_security.status, security_signoff.status)
                    break

                # Check that all snap tasks are either "Invalid" or "Fix Released"
                snap_done = True
                for taskname in s.bug.tasks_by_name:
                    if taskname.startswith('snap-') and s.bug.tasks_by_name[taskname].status not in ['Invalid', 'Fix Released']:
                        s.task.reason = 'Stalled -- %s is neither "Fix Released" nor "Invalid" (%s)' % (taskname, s.bug.tasks_by_name[taskname].status)
                        snap_done = False
                if not snap_done:
                    break

            # All is completed so we can finally close out this workflow bug.
            s.bug.tasks_by_name[s.bug.workflow_project].status = 'Fix Released'
            if promote_to_updates.status == 'Invalid':
                msgbody = 'All tasks have been completed and the bug is being set to Fix Released\n'
                s.bug.add_comment('Workflow done!', msgbody)
            else:
                s.bug.phase = 'Released'
                msgbody = 'The package has been published and the bug is being set to Fix Released\n'
                s.bug.add_comment('Package Released!', msgbody)
            break

        cleave(s.__class__.__name__ + '._complete (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
