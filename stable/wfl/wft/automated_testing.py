
from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler
import requests

class AutomatedTesting(TaskHandler):
    '''
    A Task Handler for the automated-testing task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(AutomatedTesting, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['Fix Committed'] = s._status_check

        s.regressions_url = "http://people.canonical.com/~kernel/status/adt-matrix/overall.txt"

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            # If we have no routing for Proposed then there is nothing to test.
            if s.bug.debs.routing('Proposed') is None:
                cinfo("automated-testing invalid with no Proposed route")
                s.task.status = 'Invalid'
                retval = True
                break

            if s.bug.tasks_by_name['prepare-package'].status == 'Invalid':
                s.task.status = 'Invalid'
                retval = True
                break

            if not s.bug.debs.ready_for_testing:
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

        # Start by retrieving regression data
        try:
            request = requests.get(s.regressions_url)
            data = request.text.split('\n')

            # Check main package
            state = s.check_testing_regression(s.bug.name, s.bug.version, data)
            if s.test_is_regression(state):
                if s.task.status != 'Incomplete':
                    s.task.status = 'Incomplete'
                    retval = True
            elif s.test_is_pass(state):
                if s.task.status != 'Fix Released':
                    s.task.status = 'Fix Released'
                    retval = True
            elif state is None:
                if s.task.status != 'Confirmed':
                    s.task.status = 'Confirmed'
                    retval = True
            else:
                if s.task.status != 'In Progress':
                    s.task.status = 'In Progress'
                    retval = True

            if s.task.status == 'Fix Released':
                pass
            elif s.task.status == 'Incomplete':
                s.task.reason = 'Stalled -- testing FAILED'
            else:
                s.task.reason = 'Ongoing -- testing in progress'

        except IOError:
            s.task.reason = 'Stalled -- testing results broken'
            cdebug('Failed to read from testing regressions data URL "%s"', s.regressions_url)

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval

    def test_is_regression(s, state):
        return state is not None and state.upper() in ['REGR', 'REGN']

    def test_is_pass(s, state):
        return state is not None and state.upper() in ['GOOD', 'FAIL', 'NEUTRAL']

    def check_testing_regression(s, package, version, test_data):
        for l in test_data:
            # Just in case we have a malformed line (e.g., when the file is being created)
            if (len(l.split()) > 3):
                # line format:
                # series package version state notes (optional)
                res = l.split()
                if res[0] == s.bug.series and res[1] == package and res[2] == version:
                    state = res[3]
                    cinfo('            State for %s %s in %s: %s' % (package, version, s.bug.series, state))

                    if s.test_is_regression(state):
                        if s.task.status != 'Incomplete':
                            msgbody = "Automated-Testing has regressed with version %s of package %s in %s\n" % (version, package, s.bug.series)
                            msgbody = "Here's the relevant information:\n\n\t%s\n\n" % l
                            msgbody += "Please verify test results in %s\n" % s.regressions_url
                            # s.bug.add_comment('Automated-Testing regression', msgbody)
                    return state
        cinfo('            Failed to get testing state for %s %s in %s' % (package, version, s.bug.series))
        return None

# vi: set ts=4 sw=4 expandtab syntax=python
