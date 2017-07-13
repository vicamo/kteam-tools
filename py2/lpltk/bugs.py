#!/usr/bin/python

from bug import Bug
from utils import typecheck_Collection

class Bugs(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, service, lp_bugs):
        self.__service       = service
        self.__bugs          = typecheck_Collection(lp_bugs)

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        self.__fetch_if_needed()
        return Bug(self.__service, self.__bugs[key])

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for bug in self.__bugs:
            b = Bug(self.__service, bug)
            yield b

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__bugs == None:
            self.__bugs = self.__service.launchpad.bugs


# vi:set ts=4 sw=4 expandtab:
