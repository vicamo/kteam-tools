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

    # _trello_block_source
    #
    def _trello_block_source(s):
        if 'kernel-trello-blocked-debs-prepare' in s.bug.tags or 'kernel-trello-blocked-prepare-packages' in s.bug.tags:
            return True
        return False

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
            if s.bug.debs.older_tracker_in_ppa:
                s.task.reason = 'Stalled -- tracker for earlier spin still active in PPA'
                s.bug.refresh_at(datetime.now(timezone.utc) + timedelta(minutes=30),
                    '{}:{} polling previous cycle tracker'.format(
                    s.bug.series, s.bug.name))

            elif s._trello_block_source():
                s.task.reason = 'Stalled -- blocked on SRU board'

            else:
                s.task.reason = 'Holding -b Not ready to be cranked'

        elif status == 'Confirmed':
            s.task.reason = 'Pending -b Debs ready to be cranked'

        elif status in ('In Progress', 'Fix Committed'):
            failures = None
            if s.bug.version is not None:
                # Work on the assumption that eventually we end up in -proposed.
                #if s.bug.task_status('promote-signing-to-proposed') != 'Invalid':
                #    dst_pocket = "Signing"
                #else:
                #    dst_pocket = "Proposed"
                dst_pocket = "Proposed"
                delta = s.bug.debs.delta_src_dst("ppa", dst_pocket)
                failures = s.bug.debs.delta_failures_in_pocket(delta, "ppa", ignore_all_missing=True)
            if failures is None:
                if 'kernel-trello-review-prepare-packages' in s.bug.tags:
                    s.task.reason = 'Stalled -b Debs waiting for peer-review on SRU board'
                else:
                    s.task.reason = 'Ongoing -b Being cranked by: {}'.format(s.task.assignee.username)
                return
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

        cleave(s.__class__.__name__ + '._common')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
