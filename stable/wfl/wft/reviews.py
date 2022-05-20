from datetime                                   import timedelta

from wfl.log                                    import center, cleave, cinfo
from .base                                      import TaskHandler


class SourceReview(TaskHandler):

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super().__init__(lp, task, bug)

        s.jumper['New']            = s._new
        s.jumper['Confirmed']      = s._confirmed
        s.jumper['In Progress']    = s._confirmed
        s.jumper['Fix Committed']  = s._confirmed
        s.jumper['Fix Released']   = s._recind

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while True:
            if s.bug.task_status(':prepare-packages') not in ('Fix Committed', 'Fix Released'):
                break

            # Record the delta between the build ppa and whatever follows.
            delta = s.bug.debs.delta_src_dst('ppa', s.bug.debs.pocket_after('ppa'))
            s.bug.bprops.setdefault('delta', {})[s.task.name] = delta
            s.bug.clamp_assign(s.review_task, s.bug.debs.prepare_id)

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _confirmed
    #
    def _confirmed(s):
        center(s.__class__.__name__ + '._confirmed')
        retval = False

        retval = s._recind()

        status = s.task.status
        if status == 'Confirmed':
            state = s.task.reason_state('Pending', timedelta(hours=12))
            s.task.reason = '{} -- ready for review'.format(state)

        elif status == 'Incomplete':
            s.task.reason = 'Stalled -- review FAILED'

        elif status == 'In Progress':
            s.task.reason = '{} -- review in progress'.format(
                s.task.reason_state('Ongoing', timedelta(hours=4)))

        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval

    # _recind
    #
    def _recind(s):
        center(s.__class__.__name__ + '._recind')
        retval = False

        clamp = s.bug.clamp(s.review_task)
        if clamp is not None and str(clamp) != str(s.bug.debs.prepare_id):
            cinfo("{} id has changed, recinding {}".format(s.review_task, s.review_task))
            if s.task.status != 'New':
                s.task.status = 'New'
                retval = True

        cleave(s.__class__.__name__ + '._recind (%s)' % retval)
        return retval


class SruReview(SourceReview):

    review_task = 'sru-review'


class NewReview(SourceReview):

    review_task = 'new-review'


# vi: set ts=4 sw=4 expandtab syntax=python
