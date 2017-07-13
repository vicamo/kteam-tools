#!/usr/bin/python

from specification import Specification
from utils         import typecheck_Collection


class Specifications(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, service, lp_specifications):
        self.__service        = service
        self.__specifications = typecheck_Collection(lp_specifications)

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        self.__fetch_if_needed()
        return Specification(self.__service, self.__specifications[key])

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for specification in self.__specifications:
            s = Specification(self.__service, specification)
            yield s

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__specifications == None:
            self.__specifications = self.__service.launchpad.specifications


# vi:set ts=4 sw=4 expandtab:
