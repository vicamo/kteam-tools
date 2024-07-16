
from wfl.log                                    import center, cleave, cdebug, cwarn, cinfo
from .base                                      import TaskHandler

class AbiTesting(TaskHandler):
    '''
    A Task Handler for the abi-testing task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super().__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['Opinion']       = s._status_check
        s.jumper['Fix Committed'] = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            if s.bug.task_status("prepare-package") != "Fix Released":
                break

            s.task.status = "Confirmed"
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')
        retval = False

        present = s.bug.task_status("prepare-package") == "Fix Released"

        # If we have no routing for Proposed then there is nothing to test.
        if s.bug.debs.routing('Proposed') is None:
            cinfo("abi-testing invalid with no Proposed route")
            s.task.status = 'Invalid'
            retval = True

        elif not present:
            if s.task.status not in ('Incomplete', 'Fix Released', "Won't Fix", 'Opinion'):
                cinfo('Kernel no longer present in build moving Aborted (Opinion)', 'yellow')
                s.task.status = 'Opinion'
                retval = True

        elif present and s.task.status == 'Opinion':
            s.task.status = 'New'
            retval = True

        elif 'abi-testing-failed' in s.bug.tags:
            cdebug('ABI Testing tagged as FAIL', 'yellow')
            if s.task.status != 'Confirmed' and s.task.status != 'Incomplete':
                msgbody = 'The bug was tagged as abi-testing-failed\n'
                s.task.status = 'Incomplete'
                retval = True

        elif 'abi-testing-passed' in s.bug.tags:
            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -s testing FAILED'
        else:
            s.task.reason = 'Ongoing -s testing in progress'

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
