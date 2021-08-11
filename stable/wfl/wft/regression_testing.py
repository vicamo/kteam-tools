
from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler

class RegressionTesting(TaskHandler):
    '''
    A Task Handler for the regression-testing task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(RegressionTesting, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['Fix Committed'] = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            # If we have no routing for Proposed then there is nothing to test.
            if s.bug.debs.routing('Proposed') is None:
                cinfo("regression-testing invalid with no Proposed route")
                s.task.status = 'Invalid'
                retval = True
                break

            if not s.bug.debs.ready_for_testing_as_proposed:
                break

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')
        retval = False

        present = s.bug.debs.all_built_and_in_pocket('Proposed')
        if not present:
            if s.task.status not in ('Incomplete', 'Fix Released', "Won't Fix"):
                cinfo('Kernels no longer present in Proposed moving Incomplete', 'yellow')
                s.task.status = 'Incomplete'
                retval = True

        # If we have managed to spam the bugs then verification is now in-progress.
        elif 'proposed-testing-requested' in s.bug.bprops and s.task.status == 'Confirmed':
            s.task.status = 'In Progress'
            retval = True

        elif 'qa-testing-failed' in s.bug.tags or 'regression-testing-failed' in s.bug.tags:
            cdebug('Regression Testing tagged as FAIL', 'yellow')
            if s.task.status != 'Confirmed' and s.task.status != 'Incomplete':
                msgbody = 'The bug was tagged as qa-testing-failed\n'
                s.bug.add_comment('Regression Testing FAILURE', msgbody)
                s.task.status = 'Incomplete'
                retval = True

        elif 'qa-testing-passed' in s.bug.tags or 'regression-testing-passed' in s.bug.tags:
            cdebug('Regression Testing tagged as PASSED', 'yellow')
            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -- testing FAILED'
        else:
            s.task.reason = 'Ongoing -- testing in progress'

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
