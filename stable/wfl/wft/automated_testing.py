
from wfl.log                                    import center, cleave, cdebug
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

        s.jumper['New']          = s._new
        s.jumper['Confirmed']    = s._confirmed
        s.jumper['Incomplete']   = s._confirmed

        s.regressions_url = "http://people.canonical.com/~kernel/status/adt-matrix/overall.txt"

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

    # _confirmed
    #
    def _confirmed(s):
        center(s.__class__.__name__ + '._confirmed')
        retval = False

        # Start by retrieving regression data
        try:
            request = requests.get(s.regressions_url)
            data = request.text.split('\n')

            # Check main package
            state = s.check_testing_regression(s.bug.pkg_name, s.bug.pkg_version, data)
            if s.test_is_pass(state):
                s.task.status = 'Fix Released'

                retval = True
        except IOError:
            cdebug('Failed to read from testing regressions data URL "%s"', s.regressions_url)

        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval

    def test_is_regression(s, state):
        return state is not None and state.upper() in ['REGR', 'REGN']

    def test_is_pass(s, state):
        return state is not None and state.upper() in ['GOOD', 'FAIL']

    def check_testing_regression(s, package, version, test_data):
        for l in test_data:
            # Just in case we have a malformed line (e.g., when the file is being created)
            if (len(l.split()) > 3):
                # line format:
                # series package version state notes (optional)
                res = l.split()
                if res[0] == s.bug.series and res[1] == package and res[2] == version:
                    state = res[3]
                    cdebug('            State for %s %s in %s: %s' % (package, version, s.bug.series, state))

                    if s.test_is_regression(state):
                        s.task.status = 'Incomplete'
                        msgbody = "Automated-Testing has regressed with version %s of package %s in %s\n" % (version, package, s.bug.series)
                        msgbody = "Here's the relevant information:\n\n\t%s\n\n" % l
                        msgbody += "Please verify test results in %s\n" % s.regressions_url
                        # s.bug.add_comment('Automated-Testing regression', msgbody)
                    return state
        cdebug('            Failed to get testing state for %s %s in %s' % (package, version, s.bug.series))
        return None

# vi: set ts=4 sw=4 expandtab syntax=python
