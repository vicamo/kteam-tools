
from wfl.log                                    import center, cleave, cinfo
from .base                                      import TaskHandler

class PromoteToProposed(TaskHandler):
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

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        if s.bug.all_dependent_packages_fully_built:
            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True

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
                break

            # If we've already been through here and already sent out the announcement
            # don't go through it again.
            #
            if 'proposed-announcement-sent' not in s.bug.bprops:
                s.bug.send_upload_announcement('proposed')
                s.bug.bprops['proposed-announcement-sent'] = True

            cinfo('    All components are now in -proposed', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            s.bug.phase = 'Promoted to proposed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
