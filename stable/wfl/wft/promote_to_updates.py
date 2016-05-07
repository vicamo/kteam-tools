
from wfl.log                                    import center, cleave, cinfo
from .base                                      import TaskHandler

class PromoteToUpdates(TaskHandler):
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

    # _testing_completed
    #
    def _testing_completed(s):
        """
        """
        center(s.__class__.__name__ + '._testing_completed')
        retval = False # For the stub

        while True:
            # If all testing tasks have been set to Fix Released we are ready
            # to release.
            #
            testing_tasks = [
                'automated-testing',
                'regression-testing',
            ]
            if s.bug.workflow_project == 'kernel_sru_workflow':
                testing_tasks.append('certification-testing')
            tested = True
            for task in testing_tasks:
                if s.bug.tasks_by_name[task].status not in ['Fix Released', 'Invalid']:
                    cinfo('            %s is neither "Fix Released" nor "Invalid" (%s)' % (task, s.bug.tasks_by_name['security-signoff'].status), 'yellow')
                    tested = False

            if not tested and 'testing-override' not in s.bug.tags:
                break

            retval = True
            break

        cleave(s.__class__.__name__ + '._testing_completed (%s)' % retval)
        return retval

    # _ready_for_updates
    #
    def _ready_for_updates(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_updates')
        retval = False # For the stub

        while True:
            if s.bug.tasks_by_name['security-signoff'].status not in ['Fix Released', 'Invalid']:
                cinfo('            security-signoff is neither "Fix Released" nor "Invalid" (%s)' % (s.bug.tasks_by_name['security-signoff'].status), 'yellow')
                break

            if not s._testing_completed():
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
            if not s.bug.packages_released:
                cinfo('            packages have not been released', 'yellow')
                break

            cinfo('    All components are now in -updates', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            s.bug.phase = 'Promoted to proposed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval

    # _fix_released
    #
    def _fix_released(s):
        """
        """
        center(s.__class__.__name__ + '._fix_released')
        retval = False # For the stub

        while True:
            if not s.bug.packages_released:
                cinfo('            packages have not been released, but the task is set to "Fix Released"', 'yellow')
                break

            if s.bug.tasks_by_name['security-signoff'] in ["Fix Released", "Invalid"]:
                cinfo('            security-signoff is neither "Fix Released" nor "Invalid"', 'yellow')
                break

            if s.bug.tasks_by_name['security-signoff'] == "Fix Released":
                if not s.bug.packages_released_to_security:
                    cinfo('            the packages have not been released to the security pocket', 'yellow')
                    break

            if not s._testing_completed():
                break

            s.bug.tasks_by_name[s.bug.workflow_project].status = 'Fix Released'
            s.bug.phase = 'Released'
            msgbody = 'The package has been published and the bug is being set to Fix Released\n'
            s.bug.add_comment('Package Released!', msgbody)
            retval = True
            break

        cleave(s.__class__.__name__ + '._fix_released (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
