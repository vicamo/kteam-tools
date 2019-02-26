
from wfl.log                            import center, cleave, cinfo
from .promoter                          import Promoter

class PromoteToSecurity(Promoter):
    '''
    A Task Handler for the promote-to-security task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToSecurity, s).__init__(lp, task, bug)

        s.jumper['New']           = s._ready_for_security
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion

        cleave(s.__class__.__name__ + '.__init__')

    # _ready_for_security
    #
    def _ready_for_security(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_security')
        retval = False # For the stub

        while True:

            # The kernels below are in evaluation.  These only get as far
            # as -proposed and will not be promoted further:
            #
            if s.bug.is_proposed_only:
                s.task.status = 'Invalid'
                s.bug.tasks_by_name['security-signoff'].status = 'Invalid'
                retval = True
                break

            # If the security-signoff task is 'Invalid' then this task should also
            # be 'Invalid'. This task will no longer be processed after that.
            #
            if not s.bug.is_development_series:
                if s.bug.tasks_by_name['security-signoff'].status == 'Invalid':
                    s.task.status = 'Invalid'
                    retval = True
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

        cleave(s.__class__.__name__ + '._ready_for_security (%s)' % retval)
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
            if s._block_proposed():
                s._remove_block_proposed()
                cinfo('            Removing block-proposed tag on this tracking bug', 'yellow')

            # Check if packages were copied to the right pocket->component
            #
            if not s.bug.packages_released_to_security:
                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -- ready to copy'
                else:
                    s.task.reason = 'Ongoing -- packages not yet published'
                break

            cinfo('    All components are now in -proposed', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
