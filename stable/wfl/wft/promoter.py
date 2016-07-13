
from wfl.log                                    import center, cleave, cinfo, cdebug
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
            if s.bug.sru_workflow_project:
                testing_tasks.append('certification-testing')
                testing_tasks.append('verification-testing')
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

    # master_bug_ready
    #
    def master_bug_ready(s):
        center(s.__class__.__name__ + '.master_bug_ready')
        retval = False

        required_sru_tasks = {
            'prepare-package'            : ['Fix Released'],
            'prepare-package-lbm'        : ['Fix Released', 'Invalid'],
            'prepare-package-meta'       : ['Fix Released', 'Invalid'],
            'prepare-package-ports-meta' : ['Fix Released', 'Invalid'],
            'prepare-package-signed'     : ['Fix Released'],
            'promote-to-proposed'        : ['Confirmed', 'Fix Released'],
            'promote-to-updates'         : ['Confirmed', 'Fix Released'],
            'promote-to-security'        : ['Confirmed', 'Fix Released', 'Invalid']
        }

        master = s.bug.master_bug

        if 'testing-override' not in master.tags:
            required_sru_tasks['automated-testing']     = ['Fix Released', 'Invalid']
            required_sru_tasks['regression-testing']    = ['Fix Released', 'Invalid']

            if master.sru_workflow_project:
                required_sru_tasks['certification-testing'] = ['Fix Released', 'Invalid']
                required_sru_tasks['verification-testing']  = ['Fix Released', 'Invalid']

        if s.bug.sru_workflow_project:
            tasks = required_sru_tasks

        retval = True
        for t in tasks:
            try:
                if master.tasks_by_name[t].status not in tasks[t]:
                    cinfo('master bug task %s is \'%s\' and not one of: %s' % (t, master.tasks_by_name[t].status, str(tasks[t])), 'yellow')
                    retval = False
                    break
            except KeyError:
                cdebug('master bug does not contian the %s task' % t)

        cleave(s.__class__.__name__ + '.master_bug_ready (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
