#!/usr/bin/python

from project                    import Project

class Projects(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, service):
        self.__service       = service
        self.__projects = None

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        self.__fetch_if_needed()
        return Project(self.__service, self.__projects[key])

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for project in self.__projects:
            d = Project(self.__service, project)
            yield d

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__projects == None:
            self.__projects = self.__service.launchpad.projects


# vi:set ts=4 sw=4 expandtab:
