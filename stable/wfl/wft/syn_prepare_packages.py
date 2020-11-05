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
                s.task.reason = 'Stalled -- previous cycle tracker in PPA'

            elif s._trello_block_source():
                s.task.reason = 'Stalled -- blocked on SRU board'

            else:
                s.task.reason = 'Holding -b Not ready to be cranked'

        elif status == 'Confirmed':
            s.task.reason = 'Pending -b Debs ready to be cranked'

        elif status in ('In Progress', 'Fix Committed'):
            failures = s.bug.debs.all_failures_in_pocket("ppa", ignore_all_missing=True)
            if failures is None:
                if 'kernel-trello-review-prepare-packages' in s.bug.tags:
                    s.task.reason = 'Stalled -b Debs waiting for peer-review on SRU board'
                else:
                    s.task.reason = 'Ongoing -b Being cranked by: {}'.format(s.task.assignee.username)
                return
            building = False
            state = 'Ongoing'
            for failure in failures:
                if not failure.endswith(':building') and not failure.endswith(':depwait'):
                    state = 'Pending'
                if failure.endswith(':building'):
                    building = True
            # If something is building elide any depwaits.  These are almost cirtainly waiting
            # for that build to complete.  Only show them when nothing else is showing.
            if building:
                failures = [failure for failure in failures if not failure.endswith(':depwait')]
            reason = '{} -- building in {}'.format(state, "ppa")
            if failures is not None:
                reason += ' ' + ' '.join(failures)
            s.task.reason = reason

        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
