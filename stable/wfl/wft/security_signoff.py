
from wfl.log                                    import center, cleave
from .base                                      import TaskHandler

class SecuritySignoff(TaskHandler):
    '''
    A Task Handler for the security-signoff task.

    new : When the task is 'new' we always check to see if the package is in the
          state to be tested. If it is in that state then the package is ready
          to be examined to see if it needs to be copied to the security pocket
          when it is also copied to the release pocket.

    invalid :
          When set to invalid, this task is _invalid_ and nothing should be done.

    confirmed :

    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SecuritySignoff, s).__init__(lp, task, bug)

        s.jumper['New']          = s._new
        s.jumper['Confirmed']    = s._confirmed

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while True:
            if not s.bug.ready_for_testing:
                # It doesn't matter if this is a derivative package or not, if the
                # package isn't ready for testing (promoted to -proposed) then it
                # can't be set to 'Confirmed'.
                #
                break

            if s.bug.is_derivative_package:
                master = s.bug.master_bug
                if s.task.status != master.tasks_by_name['security-signoff'].status:
                    s.task.status = master.tasks_by_name['security-signoff'].status
                    retval = True
                    break

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _confirmed
    #
    def _confirmed(s):
        center(s.__class__.__name__ + '._confirmed')
        retval = False

        if s.bug.is_derivative_package:
            master = s.bug.master_bug
            if s.task.status != master.tasks_by_name['security-signoff'].status:
                s.task.status = master.tasks_by_name['security-signoff'].status
                retval = True

        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
