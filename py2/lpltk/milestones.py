#!/usr/bin/python

from milestone                        import Milestone
from utils                            import typecheck_Collection

class Milestones(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, service, lp_milestones):
        self.__service       = service
        self.__lp_milestones = typecheck_Collection(lp_milestones)

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        return Milestone(self.__service, self.__lp_milestones[key])

    # __iter__
    #
    def __iter__(self):
        for milestone in self.__lp_milestones:
            d = Milestone(self.__service, milestone)
            yield d

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

# vi:set ts=4 sw=4 expandtab:
