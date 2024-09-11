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
            unprepared = s.bug.debs.older_tracker_unprepared
            if block is not None:
                s.task.reason = 'Stalled -- blocked via ' + block

            elif ready and (older is not None or unprepared is not None):
                if older is not None:
                    s.task.reason = 'Stalled -- tracker for earlier spin still active in PPA'
                    s.bug.monitor_add({
                        "type": "tracker-modified",
                        "watch": str(older)})
                if unprepared is not None:
                    s.task.reason = 'Holding -b Not ready to be cranked -- earlier spin needs preparation'
                    s.bug.monitor_add({
                        "type": "tracker-modified",
                        "watch": str(unprepared)})

            else:
                s.task.reason = 'Holding -b Not ready to be cranked'

        elif status == 'Confirmed':
            s.task.reason = 'Pending -b Debs ready to be cranked'

        elif status in ('In Progress', 'Fix Committed'):
            failures = None
            if s.bug.version is not None:
                # Work on the assumption that eventually we end up in -proposed.
                delta = s.bug.debs.delta_src_dst("ppa", "Proposed", pair_signing=True)
                failures = s.bug.debs.delta_failures_in_pocket(delta, "ppa", ignore_all_missing=True)
            if failures is None:
                if s.bug.flag('jira-in-review'):
                    s.task.reason = 'Stalled -b Debs waiting for peer-review on SRU board (jira)'
                    peer_reviewer = s.bug.peer_reviewer
                    if peer_reviewer is None:
                        peer_reviewer = "cycle-lead"
                    s.task.bug.announce_drip(
                        "swm-transition-peer-reviewable",
                        subject="@{reviewer} [{id}](https://warthogs.atlassian.net/jira/software/c/projects/KSRU/boards/205?selectedIssue={id}) {cycle} {series}:{source} is ready for your review".format(
                            reviewer=peer_reviewer,
                            id=s.bug.bprops['issue'],
                            cycle=s.task.bug.sru_spin_name,
                            series=s.task.bug.series,
                            source=s.task.bug.name
                        ),
                        every=timedelta(hours=24),
                    )
                else:
                    assignee = s.task.assignee.name if s.task.assignee is not None else "Unassigned"
                    s.task.reason = 'Ongoing -b Being cranked by: {}'.format(assignee)
            else:
                building = False
                state = 'Ongoing'
                for failure in failures:
                    if failure not in ('building', 'depwait', 'failwait'):
                        state = 'Pending'
                    #if failure == 'building':
                    #    building = True
                if 'failed' in failures or 'superseded' in failures:
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

        # Record what we are currently built from (based on recorded versions).  This
        # is used by external processes to detect updates to packages which may invalidate
        # their processing.
        s.bug.built_set('from', s.bug.debs.prepare_id)

        cleave(s.__class__.__name__ + '._common')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
