
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
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Incomplete']    = s._verify_promotion
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
            # If we have no routing for release then we are invalid.
            if s.bug.debs.routing('Release') is None:
                cinfo("promote-to-release invalid with no Release route")
                s.task.status = 'Invalid'
                retval = True
                break

            # Confirm we think we are in proposed.
            if s.bug.task_status('promote-to-proposed') != 'Fix Released':
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

            # See if we are blocked by a derivative.
            blocks = s.bug.block_present('hold-promote-to-updates')
            if blocks is not None:
                cinfo("promote-to-release held {}".format(blocks))
                s.task.reason = blocks
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

            if s.bug.is_derivative_package:
                if not s.master_bug_ready():
                    s.task.reason = 'Holding -- master bug not ready for release'
                    break

            # Record what is missing as we move to Confirmed.
            s.bug.bprops.setdefault('delta', {})[s.task.name] = s.bug.debs.built_in_src_dst_delta('Proposed', 'Release')

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._ready_for_release (%s)' % retval)
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

            blocks = s.bug.block_present('hold-promote-to-updates')
            if blocks is not None:
                cinfo("promote-to-release held {}".format(blocks))
                cinfo('            A hold-promote-to-updates present ({}) on this tracking bug pulling back from Confirmed'.format(blocks), 'yellow')
                pull_back = True

            if s._kernel_block():
                cinfo('            A kernel-block/kernel-block-proposed on this tracking bug pulling back from Confirmed', 'yellow')
                pull_back = True

            if s._in_blackout():
                cinfo('            Package now in development blackout pulling back from Confirmed', 'yellow')
                pull_back = True

            if pull_back:
                s.task.status = 'New'
                retval = True

            break

        while not retval:
            # Check if packages were copied to the right pocket->component
            #
            if not s.bug.debs.packages_released:
                # Confirm the packages remain available to copy.
                if not s.bug.debs.all_built_and_in_pocket('Proposed'):
                    s.task.reason = 'Alert -- packages no longer available'
                    if s.task.status != 'Incomplete':
                        s.task.status = 'Incomplete'
                        retval = True
                    break

                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -- britney unblocked'
                else:
                    s.task.reason = 'Ongoing -- packages not yet published'
                break

            cinfo('    All components are now in -release', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
