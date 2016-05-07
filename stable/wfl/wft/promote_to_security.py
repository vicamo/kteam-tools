
from wfl.log                                    import center, cleave, cinfo
from .base                                      import TaskHandler

class PromoteToSecurity(TaskHandler):
    '''
    A Task Handler for the promote-to-security task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToSecurity, s).__init__(lp, task, bug)

        s.jumper['New']           = s._ready_for_security
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion

        cleave(s.__class__.__name__ + '.__init__')

    # _ready_for_security
    #
    def _ready_for_security(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_security')
        retval = False # For the stub

        while True:
            if s.bug.tasks_by_name['security-signoff'].status != 'Fix Released':
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

        cleave(s.__class__.__name__ + '._ready_for_security (%s)' % retval)
        return retval

    # _verify_promotion
    #
    def _verify_promotion(s):
        center(s.__class__.__name__ + '._verify_promotion')
        retval = False

        while True:

            # Check if packages were copied to the right pocket->component
            #
            if not s.bug.packages_released_to_security:
                break

            cinfo('    All components are now in -proposed', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            s.bug.phase = 'Promoted to proposed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
