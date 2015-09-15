
from wfl.log                                    import center, cleave, cdebug, cwarn
from .base                                      import TaskHandler

class CertificationTesting(TaskHandler):
    '''
    A Task Handler for the certification-testing task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(CertificationTesting, s).__init__(lp, task, bug)

        s.jumper['New']          = s._new
        s.jumper['Confirmed']     = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Fix Committed'] = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        if s.bug.ready_for_testing:
            s.task.status = 'Confirmed'

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')
        retval = False

        if 'certification-testing-failed' in s.bug.tags:
            cdebug('Certification Testing tagged as FAIL', 'yellow')
            if s.task.status != 'Confirmed':
                msgbody = 'The bug was tagged as certification-testing-failed\n'
                s.bug.add_comment('Certification Testing FAILURE', msgbody)
                s.task.status = 'Incomplete'
                s.bug.phase = 'Testing Failed'

        elif 'certification-testing-passed' in s.bug.tags:
            cdebug('Certification Testing tagged as PASSED', 'yellow')
            s.task.status = 'Fix Released'
        else:
            cdebug('Certification Testing still running', 'yellow')
            pass

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
