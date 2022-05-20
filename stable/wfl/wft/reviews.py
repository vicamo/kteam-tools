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

    def evaluate_status(self, status):
        # SIGNING-BOT: we have two different workflows for reviewing and
        # promoting kernels to proposed: the manual two step process which
        # utilises a pair of copy-proposed-kernel incantations, and signing-bot
        # driven workflow.
        #
        # When performing the manual two step process we implicitly perform the
        # new-review as part of the promote-to-proposed copy, so we effectivly
        # ignore that task and let promote-to-proposed move Confirmed once the
        # kernels are otherwise ready to promote.  If the new-review is then
        # signed off we will also switch into canonical-signing-bot mode, and
        # that task becomes blocking on our workflow.
        if 'kernel-signing-bot' not in self.bug.tags:
            # Interlock with manual promotion.  If we move beyond confirmed and
            # we are not under the control of canonical-signing-bot then
            # promote-to-proposed status defines new-review status. Copy it over.
            nr_status = self.task.status
            sr_status = self.bug.task_status('promote-to-proposed')
            if sr_status == 'In Progress':
                 nr_status = 'In Progress'

            elif sr_status == 'Fix Committed':
                 nr_status = 'Fix Released'

            elif sr_status == 'Incomplete':
                 nr_status = 'Incomplete'

            if self.task.status != nr_status:
                cinfo('            no canonical-signing-bot tracking manual promotion promote-to-proposed={} new-review={}'.format(sr_status, nr_status))
                self.task.status = nr_status
                return True

        return super().evaluate_status(status)


# vi: set ts=4 sw=4 expandtab syntax=python
