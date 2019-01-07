from wfl.log                            import center, cleave, cinfo

from .base                              import TaskHandler

class Workflow(TaskHandler):
    '''
    A Task Handler for the propose-to-proposed task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(Workflow, s).__init__(lp, task, bug)

        s.jumper['Confirmed']     = s._complete
        s.jumper['Triaged']       = s._complete
        s.jumper['In Progress']   = s._complete
        s.jumper['Fix Committed'] = s._complete

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    def evaluate_status(s, state):
#        # We ARE aware of invalid bugs ... but need a valid package.
#        if not s.bug.has_package:
#            return False
        return s.jumper[state]()

    # _complete
    #
    def _complete(s):
        """
        """
        center(s.__class__.__name__ + '._complete')
        retval = False

        while True:
            #
            # FINAL VALIDATION:
            #
            # In principle all of the tasks are now reporting complete, do final validation
            # of those tasks against each other and against the archive.
            #

            # Check that all tasks are either "Invalid" or "Fix Released"
            tasks_done = True
            for taskname in s.bug.tasks_by_name:
                if s.task == s.bug.tasks_by_name[taskname]:
                    continue
                if s.bug.tasks_by_name[taskname].status not in ['Invalid', 'Fix Released']:
                    tasks_done = False
            if tasks_done is False:
                break

            # Check that the promote-to-updates status matches -updates pocket.
            release_task = None
            if 'promote-to-updates' in s.bug.tasks_by_name:
                updates_task = 'promote-to-updates'
            if 'promote-to-release' in s.bug.tasks_by_name:
                updates_task = 'promote-to-release'
            if release_task is not None:
                promote_to_task = s.bug.tasks_by_name[updates_task]
                if promote_to_task.status == 'Invalid' and s.bug.packages_released:
                    s.task.reason = 'Stalled -- packages have been released but the task set to Invalid'
                    break
                elif promote_to_task.status == 'Fix Released' and not s.bug.packages_released:
                    s.task.reason = 'Stalled -- packages have been released but the task set to Fix Released'
                    break

            if 'promote-to-security' in s.bug.tasks_by_name:
                # Check that the promote-to-security status matches -security pocket.
                promote_to_security = s.bug.tasks_by_name['promote-to-security']
                if promote_to_security.status not in ['Invalid', 'Fix Released']:
                    s.task.reason = 'Stalled -- promote-to-security is neither "Fix Released" nor "Invalid" (%s)' % (s.bug.tasks_by_name['promote-to-security'].status)
                    break
                if promote_to_security.status == 'Invalid' and s.bug.packages_released_to_security:
                    s.task.reason = 'Stalled -- packages have been released to security, but the task is set to "Invalid"'
                    break
                elif promote_to_security.status == 'Fix Released' and not s.bug.packages_released_to_security:
                    s.task.reason = 'Stalled -- packages have not been released to security, but the task is set to "Fix Released"'
                    break

                # Check that the promote-to-security status matches that of the security-signoff.
                security_signoff = s.bug.tasks_by_name['security-signoff']
                if promote_to_security.status != security_signoff.status:
                    s.task.reason = 'Stalled -- package promote-to-security status (%s) does not match security-signoff status (%s)' % (promote_to_security.status, security_signoff.status)
                    break

            # All is completed so we can finally close out this workflow bug.
            s.bug.phase = 'Released'
            s.task.status = 'Fix Released'
            msgbody = 'All tasks have been completed and the bug is being set to Fix Released\n'
            s.bug.add_comment('Workflow done!', msgbody)
            break

        cleave(s.__class__.__name__ + '._complete (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
