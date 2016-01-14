#!/usr/bin/env python
#

from core.bug_handler                   import BugHandler
from ktl.termcolor                      import colored

class RequiredLogs(BugHandler):
    """
    The Kernel Team requires every bug to have certain logs attached before it can be worked on. The
    KernelBug class knows which logs are required. The rules for this method are:

    Bug status == "New":

       1. If the correct logs are attached the status is changed from "New" to "Confirmed".

       2. If it does not have the correct logs attached:
          a) It's status is changed from "New" to "Incomplete"
          b) A comment is added to the bug asking for the logs to be attached and how.
          c) The tag: "needs-logs" is added to the bug.

    Bug status == "Incomplete" & tagged with "needs-logs":

      1. If the correct logs are attached, the status is changed from "Incomplete" to
         "Confirmed".

      2. If it does not have the correct logs attached, no changes are made to it.

    Note: Only section 1, #1 has been implemented.
    """

    # __init__
    #
    def __init__(self, cfg, lp, vout):
        BugHandler.__init__(self, cfg, lp, vout)

        self.comment = "This bug is missing log files that will aid in diagnosing the problem. While running an Ubuntu kernel (not a mainline or third-party kernel) please enter the following command in a terminal window:\n\napport-collect %s\n\nand then change the status of the bug to 'Confirmed'.\n\nIf, due to the nature of the issue you have encountered, you are unable to run this command, please add a comment stating that fact and change the bug status to 'Confirmed'.\n\nThis change has been made by an automated script, maintained by the Ubuntu Kernel Team."
        self.comment_subject = "Missing required logs."
        self.confirm_subject = "Status changed to Confirmed"
        self.confirm_body = "This change was made by a bot."

    # change_status
    #
    def change_status(self, bug, task, package_name, new_status):
        nominations = bug.nominations
        if len(nominations) > 0:
            if task.status == "New":
                try:
                    task.status = new_status  # Make the status change
                except:
                    pass # Just eat this one and move onto the nominations
            for nomination in nominations:
                if nomination.status != 'Approved': continue
                task_name = '%s (Ubuntu %s)' % (package_name, nomination.target.name.title())
                t = bug.get_relevant_task(task_name)
                if t is not None and t.status == "New":
                    self.show_buff += colored('%s Status: "%s" -> "%s"; ' % (task_name, t.status, new_status), 'green')
                    t.status = new_status  # Make the status change
        else:
            self.show_buff += colored('%s Status: "%s" -> "%s" ' % (task.bug_target_name, task.status, new_status), 'green')
            if task.status == "New":
                task.status = new_status  # Make the status change

    # hands_off
    #
    def hands_off(self, bug, task, package_name):
        """
        There are certain bugs that we shouldn't mess with. This method tries to
        know about those and returns True if they are supposed to be ignored.
        """
        retval = False

        while True:

            # A bug that is filed for a particular CVE. This is part of the CVE/SRU
            # process.
            #
            if 'kernel-cve-tracking-bug' in bug.tags:
                retval = True
                break

            # A bug that is used for workflow processes and is part of the kernel
            # stable teams workflow.
            #
            if 'kernel-release-tracking-bug' in bug.tags:
                retval = True
                break

            # The kernel stable team adds this tag onto bugs that get filed as part
            # of a commit revert. It's so the team doesn't forget about the revert.
            #
            if ('stable-next' in bug.tags) or ('kernel-stable-next' in bug.tags):
                retval = True
                break

            # As you'd expect, we shouldn't be touching private bugs.
            #
            if bug.private:
                retval = True
                break

            # We should not be trying to change the status of "bug watch" tasks.
            #
            watch_link = task.bug_watch
            if watch_link is not None:
                retval = True
                break

            break;
        return retval

    # run
    #
    def run(self, bug, task, package_name):
        retval = True

        if not self.hands_off(bug, task, package_name):
            if task.status == "New":
                if self.show_buff == '':
                    self.show_buff += 'Bug: %s  ' % bug.id
                if bug.has_required_logs:
                    bug.add_comment(self.confirm_body, self.confirm_subject)
                    self.change_status(bug, task, package_name, "Confirmed")
                else:
                    bug.add_comment(self.comment % (bug.id), self.comment_subject)
                    self.change_status(bug, task, package_name, "Incomplete")

        return retval

# vi:set ts=4 sw=4 expandtab:
