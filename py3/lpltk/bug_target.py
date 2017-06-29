#!/usr/bin/python3

from .utils                         import typecheck_Entry

class BugTarget(object):
    # __init__
    #
    def __init__(self, service, bug, lp_bug_target):
        self.__service        = service
        self.__bug            = bug
        self.__lp_bug_target  = typecheck_Entry(lp_bug_target)
        self.__name           = None

    @property
    def name(self):
        if self.__name is None:
            self.__name = self.__lp_bug_target.name
        return self.__name

# vi:set ts=4 sw=4 expandtab:
