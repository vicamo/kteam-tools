
from wfl.log                                    import center, cleave
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

        s.jumper['Fix Released'] = s._ready_for_updates

        cleave(s.__class__.__name__ + '.__init__')

    # _ready_for_updates
    #
    def _ready_for_updates(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_updates')
        retval = False # For the stub

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
            if s.bug.tasks_by_name[task].status != 'Fix Released':
                tested = False

        if tested or 'testing-override' in s.bug.tags:
            s.task.status = 'Confirmed'
            retval = True

        cleave(s.__class__.__name__ + '._ready_for_updates (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
