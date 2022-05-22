import json
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from wfl.bug                                    import WorkflowBugTaskError
from wfl.errors                                 import ShankError
from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler


class RegressionTestingResultsError(ShankError):
    pass


class RegressionTestingResultsCycle:

    _url = "http://10.246.75.167/{cycle}/summarized-results.json"

    def __init__(self, cycle, url=None, data=None):
        if url is None:
            url = self._url
        url = url.format(cycle=cycle)

        cinfo("RTC creating url={}".format(url))

        self.cycle = cycle

        if data is None:
            try:
                response = urlopen(url, timeout=30)
                data = response.read()
            except HTTPError as e:
                if e.code != 404:
                    raise e
                data = None
            except URLError as e:
                data = RegressionTestingResultsError("summarized-results fetch failure -- " + str(e.reason))

        if isinstance(data, Exception):
            self.data = data

        elif data is not None:
            if not isinstance(data, str):
                data = data.decode('utf-8')
            self.data = json.loads(data)

        else:
            self.data = {}


    def lookup_result(self, series, source, version, op):
        if isinstance(self.data, Exception):
            raise self.data

        cycle_data = self.data.get(self.cycle)
        if cycle_data is None:
            return None

        op_data = cycle_data.get("ops", {}).get(op)
        if op_data is None:
            return None

        # Find the series by codename.
        all_series_data = op_data.get("series-names", {})
        for series_name, series_data in all_series_data.items():
            if series_data.get("series-codename") == series:
                break
        else:
            return None

        source_data = series_data.get("sources", {}).get(source)
        if source_data is None:
            return None

        version_data = source_data.get("versions", {}).get(version)
        if version_data is None:
            return None

        return version_data.get("summary", "UNKNOWN")


class RegressionTestingResults:

    _cycle_cache = {}

    @classmethod
    def lookup_result(cls, spin, series, source, version, op, url=None):
        (cycle, spin_num) = spin.rsplit('-', 1)
        if cycle not in cls._cycle_cache:
            cls._cycle_cache[cycle] = RegressionTestingResultsCycle(cycle, url)
        rtc = cls._cycle_cache[cycle]

        return rtc.lookup_result(series, source, version, op)


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
        s.jumper['Triaged']       = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['Opinion']       = s._status_check
        s.jumper['Fix Committed'] = s._status_check
        s.jumper['Fix Released']  = s._status_check

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

    def _status_check_payload(s):
        retval = False

        promote_status = s.bug.task_status('promote-to-updates')
        if promote_status == 'Invalid':
            promote_status = s.bug.task_status('promote-to-release')
        if promote_status == 'Fix Released':
            cinfo('kernels promoted successfully from Proposed', 'green')
            return retval

        present = s.bug.debs.all_built_and_in_pocket_or_after('Proposed')
        if not present:
            if s.task.status not in ('Incomplete', 'Fix Released', "Won't Fix", 'Opinion'):
                cinfo('Kernels no longer present in Proposed moving Aborted (Opinion)', 'yellow')
                s.task.status = 'Opinion'
                retval = True

        elif present and s.task.status == 'Opinion':
            s.task.status = 'New'
            retval = True

        elif 'qa-testing-failed' in s.bug.tags or 'regression-testing-failed' in s.bug.tags:
            cdebug('Regression Testing tagged as FAIL', 'yellow')
            if s.task.status not in ('Confirmed', 'Incomplete'):
                msgbody = 'The bug was tagged as regression-testing-failed\n'
                s.bug.add_comment('Regression Testing FAILURE', msgbody)
                s.task.status = 'Incomplete'
                retval = True

        elif 'qa-testing-passed' in s.bug.tags or 'regression-testing-passed' in s.bug.tags:
            cdebug('Regression Testing tagged as PASSED', 'yellow')
            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        # Otherwise use the testing status as posted by rt testing.
        else:
            try:
                result = RegressionTestingResults.lookup_result(s.bug.sru_cycle, s.bug.series, s.bug.name, s.bug.version, 'sru')
                task_status = {
                        None: 'Triaged',
                        'noprov': 'Incomplete',
                        'failed': 'Incomplete',
                        'passed': 'Fix Released',
                        'hinted': 'Fix Released',
                        'incomplete': 'In Progress',
                    }.get(result, 'In Progress')
                if s.task.status != task_status:
                    cinfo("RegressionTestingResults sru {} -> status {}".format(result, task_status))
                    s.task.status = task_status
                    retval = True
            except RegressionTestingResultsError as e:
                s.bug.monitor_add({
                    "type": "regression-testing",
                    "op": "sru",
                    "status": '--broken--'})
                raise WorkflowBugTaskError(str(e))
            s.bug.monitor_add({
                "type": "regression-testing",
                #"cycle": s.bug.sru_cycle,
                #"series": s.bug.series,
                #"source": s.bug.name,
                #"version": s.bug.version,
                "op": "sru",
                "status": result})

        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')

        retval = s._status_check_payload()

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -- testing FAILED'
        else:
            s.task.reason = 'Ongoing -- testing in progress'

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval


class BootTesting(TaskHandler):
    '''
    A Task Handler for the boot-testing task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(BootTesting, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._status_check
        s.jumper['Triaged']       = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper["Won't Fix"]     = s._status_check
        s.jumper['Fix Committed'] = s._status_check
        s.jumper['Fix Released']  = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            if s.bug.task_status(':prepare-packages') != 'Fix Released':
                break

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    def _status_check_payload(s):
        retval = False

        if s.bug.task_status('promote-to-proposed') == 'Fix Released':
            cinfo('kernels promoted successfully from the PPA', 'green')
            return retval

        present = s.bug.debs.all_built_and_in_pocket_or_after('ppa')
        if not present:
            if s.task.status not in ('Incomplete', 'Fix Released', "Won't Fix"):
                cinfo('Kernels no longer present in PPA moving Incomplete', 'yellow')
                s.task.status = "Opinion"
                retval = True

        elif present and s.task.status == "Opinion":
            s.task.status = 'New'
            retval = True

        elif 'boot-testing-failed' in s.bug.tags:
            cdebug('Boot Testing tagged as FAIL', 'yellow')
            if s.task.status != 'Incomplete':
                s.task.status = 'Incomplete'
                retval = True

        elif 'boot-testing-passed' in s.bug.tags:
            cdebug('Boot Testing tagged as PASSED', 'yellow')
            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        # Otherwise use the testing status as posted by rt testing.
        else:
            # If we are checking results and we have not requested boot testing
            # do that now.
            if 'boot-testing-requested' not in s.bug.bprops:
                s.bug.debs.send_boot_testing_requests()
                s.bug.bprops['boot-testing-requested'] = True

            try:
                result = RegressionTestingResults.lookup_result(s.bug.sru_cycle, s.bug.series, s.bug.name, s.bug.version, 'boot')
                task_status = {
                        None: 'Triaged',
                        'noprov': 'Incomplete',
                        'failed': 'Incomplete',
                        'passed': 'Fix Released',
                        'hinted': 'Fix Released',
                        'incomplete': 'In Progress',
                    }.get(result, 'In Progress')
                if s.task.status != task_status:
                    cinfo("RegressionTestingResults boot {} -> status {}".format(result, task_status))
                    s.task.status = task_status
                    retval = True
            except RegressionTestingResultsError as e:
                s.bug.monitor_add({
                    "type": "regression-testing",
                    "op": "boot",
                    "status": '--broken--'})
                raise WorkflowBugTaskError(str(e))
            s.bug.monitor_add({
                "type": "regression-testing",
                #"cycle": s.bug.sru_cycle,
                #"series": s.bug.series,
                #"source": s.bug.name,
                #"version": s.bug.version,
                "op": "boot",
                "status": result})

        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')

        retval = s._status_check_payload()

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -- testing FAILED'
        else:
            s.task.reason = 'Ongoing -- testing in progress'

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
