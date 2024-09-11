from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler


class CanonicalSigningJobs(TaskHandler):

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(CanonicalSigningJobs, s).__init__(lp, task, bug)

        s.jumper['Triaged']       = s._ready
        s.jumper['In Progress']   = s._monitor
        s.jumper['Fix Committed'] = s._monitor
        s.jumper['Incomplete']    = s._failed
        s.jumper['Expired']       = s._expired

        cleave(s.__class__.__name__ + '.__init__')

    # _ready
    #
    def _ready(s):
        center(s.__class__.__name__ + '._ready')
        retval = False

        while not retval:
            # Allow In Progress to avoid race conditions triggered by the normal
            # ordering:
            #  new-review -> In Progress
            #  canonical-signing-jobs -> Triaged
            #  new-review -> Fix Released
            nrs = s.bug.task_status("new-review")
            if nrs not in ("In Progress", "Fix Committed", "Fix Released"):
                cinfo("new-review is not marked approved, recinding signing")
                s.task.status = "New"
                retval = True
                break
            if nrs != "Fix Released":
                break

            ptps = s.bug.task_status("promote-to-proposed")
            if ptps == "Invalid":
                cinfo("promote-to-proposed is marked Invalid, fail signing")
                s.task.status = "Incomplete"
                retval = True

            elif ptps not in ("New", "Triaged"):
                cinfo("promote-to-proposed is no longer pending, start signing")
                s.task.status = "Confirmed"
                retval = True

            break

        cleave(s.__class__.__name__ + '._ready (%s)' % retval)
        return retval

    # _monitor
    #
    def _monitor(s):
        center(s.__class__.__name__ + '._monitor')
        retval = s._recind()

        while not retval:
            s.task.reason = "Ongoing -s signing request in-progress"
            s.bug.monitor_add({
                'type': 'launchpad-task',
                'lp-api': s.task.lp_task.self_link,
                'status': s.task.lp_task.status})
            break

        cleave(s.__class__.__name__ + '._monitor (%s)' % retval)
        return retval

    # _failed
    #
    def _failed(s):
        center(s.__class__.__name__ + '._failed')
        retval = False

        s.reason = "Stalled -s signing request failed/recinded"

        cleave(s.__class__.__name__ + '._failed (%s)' % retval)
        return retval

    # _recind
    #
    def _recind(s):
        center(s.__class__.__name__ + '._recind')
        retval = False

        if s.bug.task_status('new-review') != 'Fix Released':
            cinfo("new-review no longer approved, recinding")
            if s.task.status != 'Incomplete':
                s.task.status = 'Incomplete'
                retval = True

        cleave(s.__class__.__name__ + '._recind (%s)' % retval)
        return retval
