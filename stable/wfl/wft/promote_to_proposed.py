
from wfl.log                            import center, cleave, cinfo
from .promoter                          import Promoter

class PromoteToProposed(Promoter):
    '''
    A Task Handler for the promote-to-proposed task.

    States:

        - New:
            As soon as all packages, main, meta, signed, etc. have been built
            move this to Confirmed so an AA can copy the packages to -proposed.

        - Confirmed / Triaged / In Progress / Fix Committed
            When we verify that all components have been copied to -proposed
            we send out our announcements and then can mark this task as
            Fix Released

        - Fix Released
            We don't process when in this state. We're done.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToProposed, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Incomplete']    = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            if not s.bug.all_in_pocket('Proposed'):
                break

            s.task.status = 'Fix Committed'
            s.task.timestamp('started')

            s._add_block_proposed()

            retval = True
            break

        while not retval:
            if not s.bug.all_dependent_packages_uploaded:
                break

            if not s.bug.all_dependent_packages_published_tag:
                s.task.reason = 'Source package tags missing'
                break

            if not s.bug.all_dependent_packages_fully_built:
                s.task.reason = 'Builds not complete'
                break

            if 'boot-testing-requested' not in s.bug.bprops:
                s.bug.send_boot_testing_requests()
                s.bug.bprops['boot-testing-requested'] = True

            if s.bug.is_derivative_package:
                if not s.master_bug_ready_for_proposed():
                    s.task.reason = 'Master bug not ready for proposed'
                    break

            if (not s.bug.proposed_pocket_clear and
                not s._kernel_unblock_ppa()):
                s.task.reason = 'Another kernel is currently pending in proposed'
                break

            if s._kernel_block_ppa():
                s.task.reason = 'Another kernel-block/kernel-block-ppa present'
                break
            if s._cycle_hold():
                s.task.reason = 'Cycle on hold'
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            s._add_block_proposed()

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _verify_promotion
    #
    def _verify_promotion(s):
        center(s.__class__.__name__ + '._verify_promotion')
        retval = False

        while not retval:
            if s.task.status not in ('Confirmed'):
                break
            if not s._kernel_block_ppa() and not s._cycle_hold():
                break

            if s._kernel_block_ppa():
                cinfo('            A kernel-block/kernel-block-ppa tag exists on this tracking bug pulling back from Confirmed', 'yellow')
            if s._cycle_hold():
                cinfo('            Cycle on hold pulling back from Confirmed', 'yellow')

            s.task.status = 'New'

            retval = True
            break

        while not retval:
            if s.task.status in ('Fix Committed', 'Incomplete'):
                break

            if not s.bug.all_in_pocket('Proposed'):
                break

            s.task.status = 'Fix Committed'

            retval = True
            break

        while True:
            # Confirm the packages remain available to copy.
            if not s.bug.all_dependent_packages_fully_built:
                s.task.reason = 'FAILED: Packages no longer available'
                if s.task.status != 'Incomplete':
                    s.task.status = 'Incomplete'
                    retval = True
                break

            # Check if the packages are published completely yet.
            if not s.bug.all_in_pocket('Proposed'):
                if s.task.status == 'Confirmed':
                    s.task.reason = 'Ready for review'
                elif s.task.status == 'Incomplete':
                    s.task.reason = 'Review FAILED'
                elif s.task.status == 'Fix Committed':
                    s.task.reason = 'Packages copies requested'
                else:
                    s.task.reason = 'Review in progress'
                break
            if not s.bug.all_built_and_in_proposed:
                s.task.reason = 'Packages copied but not yet published to -proposed'
                break
            if not s.bug.ready_for_testing:
                s.task.reason = 'Packages waiting in -proposed for mirror sync'
                break

            # Check if packages were copied to the right pocket->component
            #
            if not s.bug.check_component_in_pocket('kernel-stable-Promote-to-proposed-end', 'proposed'):
                s.task.reason = 'Packages are in the wrong component'
                break

            # If we've already been through here and already sent out the announcement
            # don't go through it again.
            #
            if 'proposed-announcement-sent' not in s.bug.bprops:
                s.bug.send_upload_announcement('proposed')
                s.bug.bprops['proposed-announcement-sent'] = True
                s.bug.send_proposed_testing_requests()
                s.bug.bprops['proposed-testing-requested'] = True

            cinfo('    All components are now in -proposed', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            s.bug.phase = 'Promoted to proposed'

            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
