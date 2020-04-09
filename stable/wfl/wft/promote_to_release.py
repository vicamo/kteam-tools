
from wfl.log                            import center, cleave, cinfo
from .promoter                          import Promoter

class PromoteToRelease(Promoter):
    '''
    A Task Handler for the promote-to-release task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToRelease, s).__init__(lp, task, bug)

        s.jumper['New']           = s._ready_for_release
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion

        cleave(s.__class__.__name__ + '.__init__')

    # _ready_for_release
    #
    def _ready_for_release(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_release')
        retval = False

        while True:
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

            if not s._all_signoffs_verified():
                # Note this will set an appropriate reason.
                break

            if s.bug.is_derivative_package:
                if not s.master_bug_ready():
                    s.task.reason = 'Holding -- master bug not ready for release'
                    break

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._ready_for_release (%s)' % retval)
        return retval

    # _verify_promotion
    #
    def _verify_promotion(s):
        """
        """
        center(s.__class__.__name__ + '._verify_promotion')
        retval = False

        while True:

            if s._block_proposed():
                s._remove_block_proposed()
                cinfo('            Removing block-proposed tag on this tracking bug', 'yellow')

            # Check if packages were copied to the right pocket->component
            #
            if not s.bug.debs.packages_released:
                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -- ready to copy'
                elif s.task.status == 'Incomplete':
                    s.task.reason = 'Stalled -- copy FAILED'
                elif s.task.status == 'Fix Committed':
                    s.task.reason = 'Ongoing -- packages not yet published'
                else:
                    s.task.reason = 'Ongoing -- copy in progress'
                break

            cinfo('    All components are now in -release', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
