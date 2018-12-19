
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
        s.jumper['Fix Released']  = s._fix_released

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
            if not s.bug.all_in_pocket('Proposed'):
                break

            if not s._prerequisites_released():
                # Note this will set an appropriate reason.
                break

            # If testing is not complete, we are not ready to release.
            if not s._testing_completed():
                break

            if s.bug.is_derivative_package:
                if not s.master_bug_ready():
                    s.task.reason = 'Holding -- master bug not ready for release'
                    break

            if not s._security_signoff_verified():
                s.task.reason = 'Holding -- security signoff not verified'
                break

            if s._kernel_block():
                s.task.reason = 'Holding -- kernel-block/kernel-block-proposed tag present'
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
            if not s.bug.packages_released:
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
            s.bug.phase = 'Promoted to release'
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion (%s)' % retval)
        return retval

    # _fix_released
    #
    def _fix_released(s):
        """
        """
        center(s.__class__.__name__ + '._fix_released')
        retval = False

        if s.bug.packages_released and s.bug.tasks_by_name[s.bug.workflow_project].status != 'Fix Released':
            s.bug.tasks_by_name[s.bug.workflow_project].status = 'Fix Released'
            s.bug.phase = 'Released'
            msgbody = 'The package has been published and the bug is being set to Fix Released\n'
            s.bug.add_comment('Package Released!', msgbody)
            retval = True 
        cleave(s.__class__.__name__ + '._fix_released (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
