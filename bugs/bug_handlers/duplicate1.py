#!/usr/bin/env python
#

from core.bug_handler                   import BugHandler
from ktl.termcolor                      import colored
import re

class Duplicate1(BugHandler):
    """
    Looking for duplicates of LP # 733223. This is an oops reporting:
    WARNING: at /build/buildd/linux-2.6.38/drivers/gpu/drm/radeon/radeon_fence.c:248 radeon_fence_wait+0x2ea/0x360 [radeon]()
    """

    # __init__
    #
    def __init__(self, lp, vout):
        BugHandler.__init__(self, lp, vout)
        self.target_rc = re.compile(r'^WARNING: at /build/buildd/linux-2.6.38/drivers/gpu/drm/radeon/radeon_fence.c:248 radeon_fence_wait\+0x2ea/0x360 \[radeon\]\(\)$')

    # run
    #
    def run(self, bug, task, package_name):
        retval = True

        try:
            duplicate = self.lp.get_bug("733223")

            if bug.duplicate_of is not None:
                raise Exception# Caught below

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

