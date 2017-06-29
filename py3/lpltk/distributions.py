#!/usr/bin/python3

from .distribution                    import Distribution

class Distributions(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, service):
        self.__service       = service
        self.__distributions = None

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        self.__fetch_if_needed()
        return Distribution(self.__service, self.__distributions[key])

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for distro in self.__distributions:
            d = Distribution(self.__service, distro)
            yield d

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__distributions is None:
            self.__distributions = self.__service.launchpad.distributions

# vi:set ts=4 sw=4 expandtab:
