#!/usr/bin/env python
#

from core.bug_handler                   import BugHandler
from ktl.termcolor                      import colored
import re

class Duplicate1(BugHandler):
    """
    WARNING: at /build/buildd/linux-2.6.35/net/sched/sch_generic.c:258 dev_watchdog+0x1fd/0x210()
    """

    # __init__
    #
    def __init__(self, lp, vout):
        BugHandler.__init__(self, lp, vout)
        self.target_rc = re.compile(r'^WARNING: at /build/buildd/linux-2.6.35/net/sched/sch_generic.c:258 dev_watchdog\+0x1fd\/0x210\(\)$')

    # run
    #
    def run(self, bug, task, package_name):
        retval = True

        try:
            content = bug.find_attachment('OopsText.txt')
            if content is None:
                raise Exception# Caught below

            for line in content.split('\n'):
                if self.target_rc.match(line):
                    if self.show_buff == '':
                        self.show_buff += 'Bug: %s  ' % bug.id
                    self.show_buff += colored('%s Is a duplicate of 733233' % (task.bug_target_name), 'green')
                    bug.lpbug.duplicate_of = duplicate.lpbug
                    bug.lpbug.lp_save()

        except:
            pass

        return retval

# vi:set ts=4 sw=4 expandtab:

