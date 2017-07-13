#!/usr/bin/python

from person                   import Person
from utils                    import (o2str, typecheck_Entry)

class ProjectSeries(object):
    # __init__
    #
    def __init__(self, service, bug, lp_project_series):
        self.__service           = service
        self.__bug               = bug
        self.__lp_project_series = typecheck_Entry(lp_project_series)
        self.__date_created      = None
        self.__owner             = None
        self.__status            = None
        self.__driver            = None
        self.__active            = None
        self.__display_name      = None
        self.__name              = None
        self.__summary           = None
        self.__title             = None

    @property
    def date_created(self):
        if self.__date_created == None:
            self.__date_created = self.__lp_project_series.date_created
        return self.__date_created

    @property
    def owner(self):
        if self.__owner == None:
            self.__owner = Person(self.__bug, self.__lp_project_series.owner)
        return self.__owner

    @property
    def driver(self):
        if self.__driver == None:
            self.__driver = Person(self.__bug, self.__lp_project_series.driver)
        return self.__driver

    @property
    def status(self):
        if self.__status == None:
            self.__status = self.__lp_project_series.status
        return self.__status

    @property
    def active(self):
        if self.__active == None:
            self.__active = self.__lp_project_series.active
        return self.__active

    @property
    def display_name(self):
        if self.__display_name == None:
            self.__display_name = o2str(self.__lp_project_series.displayname)
        return self.__display_name

    @property
    def name(self):
        if self.__name == None:
            self.__name = o2str(self.__lp_project_series.name)
        return self.__name

    @property
    def summary(self):
        if self.__summary == None:
            self.__summary = o2str(self.__lp_project_series.summary)
        return self.__summary

    @property
    def title(self):
        if self.__title == None:
            self.__title = o2str(self.__lp_project_series.title)
        return self.__title

# vi:set ts=4 sw=4 expandtab:
