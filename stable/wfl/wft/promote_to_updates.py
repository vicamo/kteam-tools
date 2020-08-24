
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
            if not s.bug.debs.all_in_pocket('Proposed'):
                break

            # Note this will set appropriate reasons.
            prerequisites = s._prerequisites_released()

            # If testing is not complete, we are not ready to release.
            if not s._testing_completed():
                break

            if not prerequisites:
                s.task.reason = 'Pending -- prerequisites not ready'
                break

            if s._kernel_block():
                s.task.reason = 'Stalled -- kernel-block/kernel-block-proposed tag present'
                break

            if s._in_blackout():
                s.task.reason = 'Holding -- package in development blackout'
                break

            if not s._all_signoffs_verified():
                # Note this will set an appropriate reason.
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

            pull_back = False
            if s.bug.is_derivative_package:
                if not s.master_bug_ready():
                    cinfo('            Master bug no longer ready pulling back from Confirmed', 'yellow')
                    pull_back = True

            if s._kernel_block():
                cinfo('            A kernel-block/kernel-block-proposed on this tracking bug pulling back from Confirmed', 'yellow')
                pull_back = True

            if s._in_blackout():
                cinfo('            Package now in development blackout pulling back from Confirmed', 'yellow')
                pull_back = True

            if not s._cycle_ready():
                cinfo('            Cycle no longer ready for release pulling back from Confirmed', 'yellow')
                pull_back = True

            if pull_back:
                s.task.status = 'New'
                retval = True

            break

        while not retval:
            # Check if packages were copied to the right pocket->component
            #
            if s._block_proposed():
                s._remove_block_proposed()
                cinfo('            Removing block-proposed tag on this tracking bug', 'yellow')

            if not s.bug.debs.packages_released:
                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -- ready to copy'
                else:
                    s.task.reason = 'Ongoing -- packages not yet published'
                break

            cinfo('    All components are now in -updates', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python