
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
        s.jumper['Fix Released']  = s._fix_released
        s.jumper['Invalid']       = s._invalid

        cleave(s.__class__.__name__ + '.__init__')

    # _ready_for_updates
    #
    def _ready_for_updates(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_updates')
        retval = False

        while True:

            # Special case for Vivid kernel packages which should never go to -updates or -security.
            # We are past support and only do this to support the Plano project.
            # Azure kernel is also being promoted temporarily only to -proposed.
            #
            if s.bug.series == "vivid" or s.bug.pkg_name == "linux-azure":
                s.task.status = 'Invalid'
                retval = True
                break

            if s.bug.is_derivative_package:
                if not s.master_bug_ready():
                    break

            if not s._security_signoff_verified():
                break

            if not s._testing_completed():
                break

            if s._kernel_block():
                cinfo('            A kernel-block tag exists on this tracking bug', 'yellow')
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

        while True:

            # Check if packages were copied to the right pocket->component
            #
            if s._block_proposed():
                s._remove_block_proposed()
                cinfo('            Removing block-proposed tag on this tracking bug', 'yellow')

            if not s.bug.packages_released:
                cinfo('            packages have not been released', 'yellow')
                break

            cinfo('    All components are now in -updates', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            s.bug.phase = 'Promoted to updates'
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

        while True:
            if not s.bug.packages_released:
                cinfo('            packages have not been released, but the task is set to "Fix Released"', 'yellow')
                break

            if s.bug.sru_workflow_project:
                if s.bug.tasks_by_name['security-signoff'] == "Fix Released":
                    if not s.bug.packages_released_to_security:
                        cinfo('            the packages have not been released to the security pocket', 'yellow')
                        break

            if not s._testing_completed():
                break

            # Since this is the one place where the master, project task is set Fix Released it needs to
            # do more than just look at the promote-to-updates. It needs to also look at promote-to-security.
            #
            promote_to_security = s.bug.tasks_by_name['promote-to-security']
            if promote_to_security.status not in ['Invalid', 'Fix Released']:
                break

            s.bug.tasks_by_name[s.bug.workflow_project].status = 'Fix Released'
            s.bug.phase = 'Released'
            msgbody = 'The package has been published and the bug is being set to Fix Released\n'
            s.bug.add_comment('Package Released!', msgbody)
            break

        cleave(s.__class__.__name__ + '._fix_released (%s)' % retval)
        return retval

    # _invalid
    #
    def _invalid(s):
        """
        """
        center(s.__class__.__name__ + '._invalid')
        retval = False

        while True:
            if s.bug.packages_released:
                cinfo('            packages have been released, but the task is set to "Invalid"', 'yellow')
                break

            if s.bug.sru_workflow_project:
                if s.bug.tasks_by_name['security-signoff'] == "Fix Released":
                    if not s.bug.packages_released_to_security:
                        cinfo('            the packages have not been released to the security pocket', 'yellow')
                        break

            if not s._testing_completed():
                break

            # Since this is the one place where the master, project task is set Fix Released it needs to
            # do more than just look at the promote-to-updates. It needs to also look at promote-to-security.
            #
            promote_to_security = s.bug.tasks_by_name['promote-to-security']
            if promote_to_security.status not in ['Invalid', 'Fix Released']:
                break

            s.bug.tasks_by_name[s.bug.workflow_project].status = 'Fix Released'
            msgbody = 'All tasks have been completed and the bug is being set to Fix Released\n'
            s.bug.add_comment('Workflow done!', msgbody)
            break

        cleave(s.__class__.__name__ + '._invalid (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
