
from wfl.log                                    import center, cleave, cinfo
from .base                                      import TaskHandler

class PromoteToRelease(TaskHandler):
    '''
    A Task Handler for the promote-to-release task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToRelease, s).__init__(lp, task, bug)

        s.jumper['New']          = s._ready_for_release
        s.jumper['Fix Released'] = s._fix_released

        cleave(s.__class__.__name__ + '.__init__')

    # _ready_for_release
    #
    def _ready_for_release(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_release')
        retval = False # For the stub

        while True:
            if s.bug.tasks_by_name['security-signoff'].status not in ['Fix Released', 'Invalid']:
                cinfo('            security-signoff is not "Fix Released" (%s)' % (s.bug.tasks_by_name['security-signoff'].status), 'yellow')
                break

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
                    tested = False

            if tested or 'testing-override' in s.bug.tags:
                s.task.status = 'Confirmed'
                retval = True
            break

        cleave(s.__class__.__name__ + '._ready_for_release (%s)' % retval)
        return retval

    # _fix_released
    #
    def _fix_released(s):
        """
        """
        center(s.__class__.__name__ + '._fix_released')
        retval = False # For the stub

        if s.bug.packages_released and s.task.status != 'Fix Released':
            s.bug.tasks_by_name[s.bug.workflow_project].status = 'Fix Released'
            s.bug.phase = 'Released'
            msgbody = 'The package has been published and the bug is being set to Fix Released\n'
            s.bug.add_comment('Package Released!', msgbody)
            retval = True

        cleave(s.__class__.__name__ + '._fix_released (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
