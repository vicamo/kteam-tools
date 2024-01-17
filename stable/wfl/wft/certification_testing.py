from datetime                                   import datetime, timezone
from wfl.bug                                    import WorkflowBugTaskError
from wfl.context                                import ctx
from wfl.log                                    import center, cleave, cdebug, cwarn, cinfo
from wfl.test_observer                          import TestObserverResults, TestObserverError
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

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._status_check
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
                cinfo("certification-testing invalid with no Proposed route")
                s.task.status = 'Invalid'
                retval = True
                break

            if not s.bug.debs.ready_for_testing:
                break

            if s.bug.built_in != 1:
                route_archive, route_pocket = s.bug.debs.pocket_route("Proposed")
                cinfo("APW route_archive={}".format(route_archive.reference))
                if route_archive.reference != "ubuntu":
                    s.task.status = "Invalid"
                    retval = True
                    break

            s.task.status = "Confirmed"
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    def match_result(self, data, source):
        sources = [package.name for package in source.packages]

        # XXX: recover the meta package name from the name field; "." is
        # mapped to "_".
        meta = data.get("name", "??").replace("_", ".")

        cinfo("  meta={}".format(meta))

        # We will assume this is published in the "stage".
        pocket = data.get("stage", "proposed")
        route = source.routing.lookup_route(pocket)
        cinfo("  route={}".format(route))

        for dest in route.entries:
            cinfo("    dest={} name={} reference={} pocket={}".format(dest, dest.name, dest.reference, dest.pocket))

            archive = ctx.lp.archives.getByReference(reference=dest.reference)
            binaries = archive.getPublishedBinaries(
                order_by_date=True,
                exact_match=True,
                binary_name=meta,
                version=data.get("version"),
            )

            if len(binaries) == 0:
                continue

            binary = binaries[0]
            cinfo(" {} ?? {}".format(binary.source_package_name, sources))
            if binary.source_package_name in sources:
                return True
            break
        return False

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._status_check')
        retval = False

        present = s.bug.debs.all_built_and_in_pocket_or_after('Proposed')
        if not present:
            if s.task.status not in ('Incomplete', 'Fix Released', "Won't Fix", 'Opinion'):
                cinfo('Kernels no longer present in Proposed moving Aborted (Opinion)', 'yellow')
                s.task.status = 'Opinion'
                retval = True

        elif present and s.task.status == 'Opinion':
            s.task.status = 'New'
            retval = True

        elif 'certification-testing-failed' in s.bug.tags:
            cdebug('Certification Testing tagged as FAIL', 'yellow')
            if s.task.status != 'Confirmed' and s.task.status != 'Incomplete':
                msgbody = 'The bug was tagged as certification-testing-failed\n'
                s.bug.add_comment('Certification Testing FAILURE', msgbody)
                s.task.status = 'Incomplete'
                retval = True

        elif 'certification-testing-passed' in s.bug.tags:
            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        else:
            result = None
            try:
                observer = TestObserverResults()
                existing = s.bug.group_get("test-observer", "proposed")
                if existing is not None:
                    result = observer.lookup_result(existing)
                    cinfo("TO direct result={}".format(result))
                else:
                    results = observer.lookup_results(
                        "deb",
                        series=s.bug.source.series.codename,
                        stage="proposed",
                        version=s.bug.debs.package_version_exact("meta"),
                    )
                    cinfo("TO results={}".format(results))
                    for current in results:
                        if s.match_result(current, s.bug.source):
                            cinfo("TO deb match result={}".format(current))
                            s.bug.group_set("test-observer", "proposed", current.get("id"))
                            result = current
                            break
                if result is not None:
                    status = result.get("status", "UNKNOWN")
                    tstatus = {
                        "UNDECIDED": "In Progress",
                        "APPROVED": "Fix Released",
                    }.get(status, "Incomplete")
                    cinfo("TO deb result-status={} task-status={}".format(status, tstatus))
                    if s.task.status != tstatus:
                        s.task.status = tstatus
                        retval = True
            except TestObserverError as e:
                s.bug.refresh_at(
                    datetime.now(timezone.utc) + timedelta(minutes=30),
                    "polling due to test-observer failure",
                )
                raise WorkflowBugTaskError(str(e))

            if result:
                s.bug.monitor_add({
                    "type": "test-observer",
                    "id": result.get("id"),
                    "status": result.get("status"),
                })
            else:
                s.bug.refresh_at(
                    datetime.now(timezone.utc) + timedelta(minutes=30),
                    "polling waiting for initial status",
                )

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -s testing FAILED'
        else:
            s.task.reason = 'Ongoing -s testing in progress'

        cleave(s.__class__.__name__ + '._status_check (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
