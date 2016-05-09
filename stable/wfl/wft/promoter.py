
from wfl.log                                    import center, cleave, cinfo
from .base                                      import TaskHandler

class Promoter(TaskHandler):
    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(Promoter, s).__init__(lp, task, bug)
        cleave(s.__class__.__name__ + '.__init__')

    def _security_signoff_verified(s):
        '''
        Check if the security-signoff task has been set to 'Fix Released'. Development
        series tracking bugs do not have this task and should always return True.
        '''
        center(s.__class__.__name__ + '.security_signoff_verified')
        retval = False
        if s.bug.sru_workflow_project:
            if s.bug.tasks_by_name['security-signoff'].status not in ['Fix Released', 'Invalid']:
                retval = True
            else:
                cinfo('            security-signoff is neither "Fix Released" nor "Invalid" (%s)' % (s.bug.tasks_by_name['security-signoff'].status), 'yellow')
        else:
            retval = True
        cleave(s.__class__.__name__ + '.security_signoff_verified (%s)' % retval)
        return retval

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
                    cinfo('            %s is neither "Fix Released" nor "Invalid" (%s)' % (task, s.bug.tasks_by_name[task].status), 'yellow')
                    tested = False

            if not tested and 'testing-override' not in s.bug.tags:
                break

            retval = True
            break

        cleave(s.__class__.__name__ + '._testing_completed (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
