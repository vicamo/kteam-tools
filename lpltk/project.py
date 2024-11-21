#!/usr/bin/python3

from .person                           import Person
from .bug_tasks                        import BugTasks
from .utils                            import typecheck_Entry

# Project
#
class Project(object):
    # __init__
    #
    def __init__(self, service, lp_project):
        self.__service = service
        self.lp_project = typecheck_Entry(lp_project)

        self.__owner        = None
        self.__display_name = None
        self.__name         = None

    # __str__
    #
    def __str__(self):
        return self.display_name

    # owner
    #
    @property
    def owner(self):
        if self.__owner is None:
            self.__owner = Person(None, self.lp_project.owner)
        return self.__owner

    # name
    #
    @property
    def name(self):
        if self.__name is None:
            self.__name = self.lp_project.name
        return self.__name

    # display_name
    #
    @property
    def display_name(self):
        if self.__display_name is None:
            self.__display_name = self.lp_project.display_name
        return self.__display_name

    # searchTasks
    #
    def search_tasks(self, **params):
        bt = BugTasks(self.__service, self.lp_project.searchTasks(**params))
        return bt

    # self_link
    #
    @property
    def self_link(self):
        return self.lp_project.self_link

# vi:set ts=4 sw=4 expandtab:
