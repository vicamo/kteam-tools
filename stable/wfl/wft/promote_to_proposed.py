
from wfl.log                            import center, cleave, cinfo
from ktl.ubuntu                         import Ubuntu
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
        s.jumper['Fix Committed'] = s._verify_promotion

        s.ubuntu = Ubuntu()

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while True:
            if not s.bug.all_dependent_packages_fully_built:
                break

            if 'boot-testing-requested' not in s.bug.bprops:
                s.bug.send_boot_testing_requests()
                s.bug.bprops['boot-testing-requested'] = True

            if s.bug.is_derivative_package:
                if not s.master_bug_ready_for_proposed():
                    break

            if (not s.bug.is_proposed_only and
                not s.bug.proposed_pocket_clear and
                not s._kernel_unblock_ppa()):
                cinfo('            Another kernel is currently pending in -proposed', 'yellow')
                break

            if s._kernel_block_ppa():
                cinfo('            A kernel-block-ppa tag exists on this tracking bug', 'yellow')
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

        while True:

            # Check if packages were copied to the right pocket->component
            #
            if not s.bug.check_component_in_pocket('kernel-stable-Promote-to-proposed-end', 'proposed'):
                cinfo('            packages are not in -proposed', 'yellow')
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
