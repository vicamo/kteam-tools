from datetime                                   import datetime, timezone, timedelta

from wfl.log                                    import center, cleave, cdebug
from .base                                      import TaskHandler


class GeneralSignoff(TaskHandler):

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(GeneralSignoff, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._confirmed
        s.jumper['In Progress']   = s._confirmed
        s.jumper['Fix Committed'] = s._confirmed

        cleave(s.__class__.__name__ + '.__init__')

    # _confirmed
    #
    def _confirmed(s):
        center(s.__class__.__name__ + '._confirmed')
        retval = False

        s.task.reason = '{} -s waiting for signoff'.format(
            s.task.reason_state('Pending', timedelta(hours=12)))

        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval


class ProposedSignoff(GeneralSignoff):
    '''
    A Task Handler for the signoff tasks in proposed (stakeholder-signoff et al)
    '''

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while True:
            if not s.bug.debs.ready_for_testing:
                # It doesn't matter if this is a derivative package or not, if the
                # package isn't ready for testing (promoted to -proposed) then it
                # can't be set to 'Confirmed'.
                break

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval


class BuildSignoff(GeneralSignoff):
    '''
    A Task Handler for the signoff tasks in build (signing-signoff et al)
    '''

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while True:
            if s.bug.task_status(':prepare-packages') != 'Fix Released':
                break

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
