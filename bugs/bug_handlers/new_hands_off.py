#!/usr/bin/env python
#

from core.bug_handler                   import BugHandler
from core.dbg                           import Dbg

class NewHandsOff(BugHandler):
    """
    """

    # __init__
    #
    def __init__(self, cfg, lp, vout):
        Dbg.enter('NewHandsOff.__init__')
        BugHandler.__init__(self, cfg, lp, vout)
        Dbg.leave('NewHandsOff.__init__')

    # run
    #
    def run(self, bug, task, package_name):
        """
        There are certain bugs that we shouldn't mess with. This method tries to
        know about those and returns True if they are supposed to be ignored.
        """
        Dbg.enter('NewHandsOff.run')

        retval = True

        while True:

            # The bugs status must be "New".
            #
            if task.status != "New":
                retval = False
                Dbg.why('The tasks status is not "New" (%s).\n' % task.status)
                break

            # A bug that is filed for a particular CVE. This is part of the CVE/SRU
            # process.
            #
            if 'kernel-cve-tracking-bug' in bug.tags:
                retval = False
                Dbg.why('kernel-cve-tracking-bug tag exists\n')
                break

            # A bug that is filed for a particular upstream stable release.
            #
            if 'kernel-stable-tracking-bug' in bug.tags:
                retval = False
                Dbg.why('kernel-stable-tracking-bug tag exists\n')
                break

            # A bug that is used for workflow processes and is part of the kernel
            # stable teams workflow.
            #
            if 'kernel-release-tracking-bug' in bug.tags:
                retval = False
                Dbg.why('kernel-release-tracking-bug tag exists\n')
                break

            # The kernel stable team adds this tag onto bugs that get filed as part
            # of a commit revert. It's so the team doesn't forget about the revert.
            #
            if ('stable-next' in bug.tags) or ('kernel-stable-next' in bug.tags):
                retval = False
                Dbg.why('kernel-stable-next tag exists\n')
                break

            # As you'd expect, we shouldn't be touching private bugs.
            #
            if bug.private:
                retval = False
                Dbg.why('Private bug\n')
                break

            # We should not be trying to change the status of "bug watch" tasks.
            #
            watch_link = task.bug_watch
            if watch_link is not None:
                retval = False
                Dbg.why('Has a watch link.\n')
                break

            # A bug that is opened by bugproxy LP User. 
            # Request per apw for IBM bugs. 
            #
            if 'bugproxy' is bug.owner:
                retval = False
                Dbg.why('Bug was opened by bugproxy.\n')
                break

            break;

        Dbg.ret('NewHandsOff.run', retval)
        return retval

# vi:set ts=4 sw=4 expandtab:
