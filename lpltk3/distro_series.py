#!/usr/bin/python3

from lpltk.milestones               import Milestones
from lpltk.person                   import Person
from lpltk.utils                    import (o2str, typecheck_Entry)

class DistroSeries(object):
    # __init__
    #
    def __init__(self, service, bug, lp_distro_series):
        self.__service           = service
        self.__bug               = bug
        self.__lp_distro_series  = typecheck_Entry(lp_distro_series)

        self.__date_created      = None
        self.__date_released     = None
        self.__owner             = None
        self.__status            = None
        self.__driver            = None
        self.__active            = None
        self.__supported         = None
        self.__description       = None
        self.__display_name      = None
        self.__full_series_name  = None
        self.__name              = None
        self.__summary           = None
        self.__title             = None
        self.__active_milestones = None

    @property
    def date_created(self):
        if self.__date_created == None:
            self.__date_created = self.__lp_distro_series.date_created
        return self.__date_created

    @property
    def date_released(self):
        if self.__date_released == None:
            self.__date_released = self.__lp_distro_series.datereleased
        return self.__date_released

    @property
    def owner(self):
        if self.__owner == None:
            self.__owner = Person(self.__bug, self.__lp_distro_series.owner)
        return self.__owner

    @property
    def driver(self):
        if self.__driver == None:
            self.__driver = Person(self.__bug, self.__lp_distro_series.driver)
        return self.__driver

    @property
    def status(self):
        if self.__status == None:
            self.__status = self.__lp_distro_series.status
        return self.__status

    @property
    def active(self):
        if self.__active == None:
            self.__active = self.__lp_distro_series.active
        return self.__active

    @property
    def supported(self):
        if self.__supported == None:
            self.__supported = self.__lp_distro_series.supported
        return self.__supported

    @property
    def description(self):
        if self.__description == None:
            self.__description = o2str(self.__lp_distro_series.description)
        return self.__description

    @property
    def display_name(self):
        if self.__display_name == None:
            self.__display_name = o2str(self.__lp_distro_series.displayname)
        return self.__display_name

    @property
    def full_series_name(self):
        if self.__full_series_name == None:
            self.__full_series_name = o2str(self.__lp_distro_series.fullseriesname)
        return self.__full_series_name

    @property
    def name(self):
        if self.__name == None:
            self.__name = o2str(self.__lp_distro_series.name)
        return self.__name

    @property
    def summary(self):
        if self.__summary == None:
            self.__summary = o2str(self.__lp_distro_series.summary)
        return self.__summary

    @property
    def title(self):
        if self.__title == None:
            self.__title = o2str(self.__lp_distro_series.title)
        return self.__title

    @property
    def active_milestones(self):
        if self.__active_milestones == None:
            self.__active_milestones = Milestones(self.__service,
                self.__lp_distro_series.active_milestones)
        return self.__active_milestones

# vi:set ts=4 sw=4 expandtab:
