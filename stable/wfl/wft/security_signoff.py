
from wfl.log                                    import center, cleave, cinfo
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

        s.jumper['New']            = s._new
        s.jumper['Confirmed']      = s._confirmed
        s.jumper['In Progress']    = s._confirmed
        s.jumper['Fix Committed']  = s._confirmed

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while True:
            # If we have no routing for security then we are invalid.
            if s.bug.debs.routing('Security') is None:
                s.task.status = 'Invalid'
                retval = True
                break

            if not s.bug.debs.ready_for_testing:
                # It doesn't matter if this is a derivative package or not, if the
                # package isn't ready for testing (promoted to -proposed) then it
                # can't be set to 'Confirmed'.
                break

            if s.bug.is_derivative_package:
                master = s.bug.master_bug
                try:
                    if s.task.status != master.tasks_by_name['security-signoff'].status:
                        if 'New' != master.tasks_by_name['verification-testing'].status:
                            s.task.status = master.tasks_by_name['security-signoff'].status
                            retval = True
                            break
                    break
                except KeyError:
                    cinfo('    master bug does not contain either security-signoff or verification-testing tasks', 'yellow')

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

        s.task.reason = 'Pending -- waiting for signoff'

        if s.bug.is_derivative_package:
            master = s.bug.master_bug
            try:
                if s.task.status != master.tasks_by_name['security-signoff'].status:
                    if 'New' != master.tasks_by_name['verification-testing'].status:
                        s.task.status = master.tasks_by_name['security-signoff'].status
                        retval = True
            except KeyError:
                cinfo('    master bug does not contain either security-signoff or verification-testing tasks', 'yellow')

        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
