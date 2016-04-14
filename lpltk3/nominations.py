#!/usr/bin/python3

from lpltk.nomination            import Nomination

class Nominations(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, service, bug):
        self.__service       = service
        self.__bug           = bug
        self.__lp_nominations   = None

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        self.__fetch_if_needed()
        return Nomination(self.__service, self.__bug, self.__lp_nominations[key])

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for nom in self.__lp_nominations:
            n = Nomination(self.__service, self.__bug, nom)
            yield n

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__lp_nominations == None:
            self.__lp_nominations = self.__bug.lpbug.getNominations()

# vi:set ts=4 sw=4 expandtab:
