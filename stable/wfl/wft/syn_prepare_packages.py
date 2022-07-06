from datetime                                   import datetime, timedelta, timezone

from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler


class SynPreparePackages(TaskHandler):
    '''
    A Task Handler for the set-prepare-package pseudo task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SynPreparePackages, s).__init__(lp, task, bug)

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
        s.jumper['Fix Released']  = s._common

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    def evaluate_status(s, state):
        # We ARE aware of invalid bugs ... but need a valid package.
        if not s.bug.has_package:
            return False
        return s.jumper[state]()

    # _common
    #
    def _common(s):
        '''
        Look to see if the packages have been fully built. This is our indication that the
        packages have been prepared and we can close this task.
        '''
        center(s.__class__.__name__ + '._common')
        retval = False

        status = s.task.status
        if status == 'New':
            block = s.bug.source_block_present()
            ready = s.bug.debs.ready_to_prepare()
            older = s.bug.debs.older_tracker_in_ppa
            if block is not None:
                s.task.reason = 'Stalled -- blocked via ' + block

            elif ready and older is not None:
                s.task.reason = 'Stalled -- tracker for earlier spin still active in PPA'
                s.bug.monitor_add({
                    "type": "tracker-modified",
                    "watch": str(older)})

            else:
                s.task.reason = 'Holding -b Not ready to be cranked'

        elif status == 'Confirmed':
            s.task.reason = 'Pending -b Debs ready to be cranked'

        elif status in ('In Progress', 'Fix Committed'):
            failures = None
            if s.bug.version is not None:
                # Work on the assumption that eventually we end up in -proposed.
                delta = s.bug.debs.delta_src_dst("ppa", "Proposed")
                # XXX: we need to figure out how to represent this.
                if "lrs" in delta and "lrg" not in delta:
                    delta.append("lrg")
                failures = s.bug.debs.delta_failures_in_pocket(delta, "ppa", ignore_all_missing=True)
            if failures is None:
                if 'kernel-trello-review-prepare-packages' in s.bug.tags:
                    s.task.reason = 'Stalled -b Debs waiting for peer-review on SRU board'
                else:
                    s.task.reason = 'Ongoing -b Being cranked by: {}'.format(s.task.assignee.username)
            else:
                building = False
                state = 'Ongoing'
                for failure in failures:
                    if failure not in ('building', 'depwait', 'failwait'):
                        state = 'Pending'
                    #if failure == 'building':
                    #    building = True
                if 'failed' in failures:
                    state = 'Stalled'
                # If something is building elide any depwaits.  These are almost cirtainly waiting
                # for that build to complete.  Only show them when nothing else is showing.
                #if building:
                #    failures = [failure for failure in failures if not failure.endswith(':depwait')]
                reason = '{} -- {} in {}'.format(state,
                        "build FAILED" if state == 'Stalled' else "building",
                        "ppa")
                if len(failures) > 0:
                    reason += ' (' + s.bug.debs.failures_to_text(failures) + ')'
                else:
                    reason += ' (builds complete)'
                s.task.reason = reason

        # If we are a live task by here request monitoring for
        # all interesting routes.
        if s.bug.is_valid and s.task.status not in ('New', 'Fix Released', 'Invalid'):
            s.bug.debs.monitor_routes(["build", "build-private"])

        cleave(s.__class__.__name__ + '._common')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
