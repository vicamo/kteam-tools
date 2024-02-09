from datetime                                   import datetime, timedelta, timezone

from lazr.restfulclient.errors                  import BadRequest

from wfl.bug                                    import WorkflowBugTaskError
from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler


class SynPromoteToAsProposed(TaskHandler):
    '''
    A Task Handler for the promote-to-as-proposed pseudo task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SynPromoteToAsProposed, s).__init__(lp, task, bug)

        # The tracking bug should start this task out as 'Confirmed'
        # for primary packages.  Derivatives should flip to 'Confirmed'
        # as soon as their primary is uploaded.
        #
        s.jumper['New']           = s._common
        s.jumper['Opinion']       = s._common
        s.jumper['Confirmed']     = s._common
        s.jumper['Triaged']       = s._common
        s.jumper['In Progress']   = s._common
        s.jumper['Fix Committed'] = s._common

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    #def evaluate_status(s, state):
    #    # We ARE aware of invalid bugs ... but need a valid package.
    #    if not s.bug.has_package:
    #        return False
    #    return s.jumper[state]()

    # _common
    #
    def _common(s):
        '''
        Look to see if the packages have been fully built. This is our indication that the
        packages have been prepared and we can close this task.
        '''
        center(s.__class__.__name__ + '._common')
        retval = False

        while not retval:
            status_ptp = s.bug.task_status('promote-signing-to-proposed')
            if status_ptp == 'Invalid':
                status_ptp = s.bug.task_status('promote-to-proposed')
            if (status_ptp == 'Invalid'
                or s.bug.debs.routing('as-proposed') is None
                or (s.bug.built_in is not None and len(s.bug.debs.routing('as-proposed')) < s.bug.built_in)
            ):
                if status_ptp == 'Invalid':
                    cinfo("promote-to-proposed: invalid, marking invalid")
                elif s.bug.debs.routing('as-proposed') is None:
                    cinfo("no as-proposed route, marking invalid")
                elif s.bug.built_in is not None and len(s.bug.debs.routing('as-proposed')) < s.bug.built_in:
                    cinfo("no as-proposed route-entry, marking invalid")

                if s.task.status != 'Invalid':
                    s.task.status = 'Invalid'
                    retval = True
                break

            if status_ptp not in ('Fix Committed', 'Fix Released'):
                cinfo("promote-to-proposed: {}, waiting for likely completion".format(status_ptp))
                break

            if not s.bug.debs.all_built_and_in_pocket_or_after('Proposed'):
                cinfo("packages are not all in Proposed")
                break

            s.task.reason = 'Ongoing -- packages not yet published'

            if s.task.status not in ('Fix Committed', 'Fix Released'):
                cinfo("packages ready for copy, requesting")
                (dst_archive, dst_pocket) = s.bug.debs.routing('as-proposed')[s.bug.built_in - 1]
                for dep in s.bug.debs.dependent_packages_for_pocket('Proposed'):
                    package = s.bug.debs.pkgs[dep]
                    build_route_entry = s.bug.debs.build_route_entry(dep, "Proposed")
                    if build_route_entry:
                        src_archive, src_pocket = build_route_entry.archive, build_route_entry.pocket
                        version = build_route_entry.version
                    else:
                        src_archive, src_pocket, version = None, None, None
                    cinfo("copying from {}:{}:{} to {}:{}:{} package {}:{}".format(src_archive, src_pocket, s.bug.series, dst_archive, dst_pocket, s.bug.series, dep, package))
                    try:
                        dst_archive.copyPackage(
                            from_archive=src_archive, from_series=s.bug.series, from_pocket=src_pocket,
                            to_series=s.bug.series, to_pocket=dst_pocket,
                            source_name=package, version=version,
                            include_binaries=True)
                    except BadRequest:
                        raise WorkflowBugTaskError("copy failed")
                if s.task.status != 'Fix Committed':
                    s.task.status = 'Fix Committed'
                    retval = True
                break

            if not s.bug.debs.all_built_and_in_pocket('as-proposed'):
                cinfo("packages are not all in as-proposed")
                break

            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True
            break

        # If we are a live task by here request monitoring for
        # all interesting routes.
        if s.task.status not in ('New', 'Confirmed', 'Fix Released', 'Invalid'):
            s.bug.debs.monitor_routes(['as-proposed'])

        cleave(s.__class__.__name__ + '._common')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
