#!/usr/bin/env python
#

from logging                            import info, debug, error, warning, basicConfig, INFO, DEBUG, WARNING
from sb.exceptions                      import FalseReturn

class PrepPackage():
    # __init__
    #
    def __init__(s, targeted_project, task):
        s.task = task
        s.targeted_project = targeted_project
        s.__preconditions_met = True

        if s.targeted_project == 'kernel-sru-workflow':
            s.taskname = 'promote-to-proposed'
        else:
            s.taskname = 'package-testing'

        # Tests for required preconditions
        #
        try:
            # Status must be 'New'
            #
            if s.task.status != 'New':
                s.__preconditions_met = False
                raise FalseReturn('                                Nothing done for status %s' % s.task.status)

        except FalseReturn as e:
            info(e.message)

    @property
    def preconditions_met(s):
        return s.__preconditions_met

    # action
    #
    def action(s):
        info('            PrepPackage.action: %s' % s.task.name)
        retval = False

        try:
            pass

        except FalseReturn as e:
            info(e.message)
            retval = False

        return retval

# vi:set ts=4 sw=4 expandtab syntax=python:
