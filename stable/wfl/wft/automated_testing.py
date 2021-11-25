import json
from urllib.request import urlopen
from urllib.error import HTTPError

from wfl.bug                                    import WorkflowBugTaskError
from wfl.errors                                 import ShankError
from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler
import requests


class AutomatedTestingResultsError(ShankError):
    pass


class AutomatedTestingResultsOne:

    def __init__(self, data):
        self.data = data

    @property
    def status(self):
        return self.data.get("state")

    @property
    def summary(self):
        return self.data.get("summary", "--unknown--")

    @property
    def is_ongoing(self):
        return self.status is not None and self.status.upper() == 'MISS'

    @property
    def is_awol(self):
        return self.status is None or self.status.upper() == 'NONE'

    @property
    def is_failure(self):
        return self.status is not None and self.status.upper() in ['REGR', 'REGN']

    @property
    def is_pass(self):
        return self.status is not None and self.status.upper() in ['GOOD', 'FAIL', 'NEUTRAL']

    @property
    def task_status(self):
        if self.is_awol:
            return 'Triaged'
        if self.is_ongoing:
            return 'In Progress'
        if self.is_pass:
            return 'Fix Released'
        return 'Incomplete'


class AutomatedTestingResultsOverall:

    _url = "https://people.canonical.com/~kernel/status/adt-matrix/overall-results-data.json"

    def __init__(self, url=None, data=None):
        if url is None:
            url = self._url

        cinfo("ATC creating url={}".format(url))

        if data is None:
            try:
                response = urlopen(url)
                data = response.read()
            except HTTPError as e:
                data = AutomatedTestingResultsError("overall-results-data fetch failure -- " + str(e.reason))

        if isinstance(data, Exception):
            self.data = data

        elif data is not None:
            if not isinstance(data, str):
                data = data.decode('utf-8')
            self.data = json.loads(data)
        else:
            self.data = {}

    def lookup_result(self, series, source, version):
        if isinstance(self.data, Exception):
            raise self.data

        for record in self.data:
            if (record.get('series') == series and
                    record.get('source') == source and
                    record.get('latest_version') == version):
                break
        else:
            record = {}

        return AutomatedTestingResultsOne(record)


class AutomatedTestingResults:

    _cache = None

    @classmethod
    def lookup_result(cls, series, source, version, url=None):
        if cls._cache is None:
            cls._cache = AutomatedTestingResultsOverall(url)
        atc = cls._cache

        return atc.lookup_result(series, source, version)


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
                cinfo("automated-testing invalid with no Proposed route")
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

        present = s.bug.debs.all_built_and_in_pocket_or_after('Proposed')
        if not present:
            if s.task.status not in ('Incomplete', 'Fix Released', "Won't Fix", 'Opinion'):
                cinfo('Kernels no longer present in Proposed moving Aborted (Opinion)', 'yellow')
                s.task.status = 'Opinion'
                retval = True

        elif present and s.task.status == 'Opinion':
            s.task.status = 'New'
            retval = True

        elif 'automated-testing-failed' in s.bug.tags:
            cdebug('Automated Testing tagged as FAILED', 'yellow')
            if s.task.status != 'Incomplete':
                s.task.status = 'Incomplete'
                retval = True

        elif 'automated-testing-passed' in s.bug.tags:
            cdebug('Automated Testing tagged as PASSED', 'yellow')
            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        elif s.task.status != 'In Progress' and promote_status not in ('New', 'Confirmed', 'Invalid'):
            cinfo('kernels promoted successfully from Proposed', 'green')

        # Otherwise use the testing status as posted by adt-matrix summariser.
        else:
            try:
                result = AutomatedTestingResults.lookup_result(s.bug.series, s.bug.name, s.bug.version)
                task_status = result.task_status
                if s.task.status != task_status:
                    cinfo("AutomatedTestingResults {} -> status {}".format(result.summary, task_status))
                    s.task.status = task_status
                    retval = True
                s.bug.monitor_add({
                    "type": "automated-testing",
                    #"series": s.bug.series,
                    #"source": s.bug.name,
                    #"version": s.bug.version,
                    "status": result.status})
            except AutomatedTestingResultsError as e:
                s.bug.monitor_add({
                    "type": "automated-testing",
                    "status": '--broken--'})
                raise WorkflowBugTaskError(str(e))


        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')

        retval = s._status_check_payload()

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -s testing FAILED'
        else:
            s.task.reason = 'Ongoing -s testing in progress'

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
