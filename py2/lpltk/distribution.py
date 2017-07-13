#!/usr/bin/python

from bug_tasks                   import BugTasks
from distribution_source_package import DistributionSourcePackage
from distro_series               import DistroSeries
from milestones                  import Milestones
from person                      import Person
from specification               import Specification
from utils                       import typecheck_Entry

# Distribution
#
class Distribution(object):
    # __init__
    #
    def __init__(self, service, lp_distribution):
        self.__service = service
        self.__lp_distribution = typecheck_Entry(lp_distribution)

        self.__owner        = None
        self.__display_name = None
        self.__all_series = None
        self.__supported_series = None
        self.__current_series  = None
        self.__stable_series = None
        self.__all_milestones  = None
        self.__active_milestones = None

    # __str__
    #
    def __str__(self):
        return self.display_name

    # owner
    #
    @property
    def owner(self):
        if self.__owner == None:
            self.__owner = Person(None, self.__lp_distribution.owner)
        return self.__owner

    # display_name
    #
    @property
    def display_name(self):
        if self.__display_name == None:
            self.__display_name = self.__lp_distribution.display_name
        return self.__display_name

    # all_series
    #
    @property
    def all_series(self):
        '''Returns a list of all the series registered for this distro'''
        if self.__all_series == None:
            self.__all_series = []
            for series in self.__lp_distribution.series:
                self.__all_series.append(DistroSeries(self.__service, None, series))

        return self.__all_series

    # supported_series
    #
    @property
    def supported_series(self):
        '''Returns a list of series that are supported'''
        if self.__supported_series == None:
            self.__supported_series = []
            for series in self.all_series:
                if series.status == 'Supported':
                    self.__supported_series.append(series)

        return self.__supported_series

    # current_series
    #
    @property
    def current_series(self):
        '''The current series under development'''
        if self.__current_series == None:
            self.__current_series = DistroSeries(self.__service, None, self.__lp_distribution.current_series)

        return self.__current_series

    # stable_series
    #
    @property
    def stable_series(self):
        '''The latest stable release series'''
        if self.__stable_series is not None:
            return self.__stable_series

        for series in self.all_series:
            if series.status == "Current Stable Release":
                self.__stable_series = series
                return self.__stable_series

    # all_milestones
    #
    @property
    def all_milestones(self):
        if self.__all_milestones == None:
            self.__all_milestones = Milestones(self.__service, self.__lp_distribution.all_milestones)

        return self.__all_milestones

    # active_milestones
    #
    @property
    def active_milestones(self):
        if self.__active_milestones == None:
            self.__active_milestones = Milestones(self.__service, self.__lp_distribution.active_milestones)

        return self.__active_milestones

    # get_source_package
    #
    def get_source_package(self, source_pkg):
        source_package = self.__lp_distribution.getSourcePackage(name = source_pkg)
        if source_package is None:
            return None
        return DistributionSourcePackage(self.__service, source_package)

    # get_series
    #
    def get_series(self, string):
        return DistroSeries(self.__service, None, self.__lp_distribution.getSeries(name_or_version = string))

    # searchTasks
    #
    def search_tasks(self, **params):
        #bt = BugTasks(self.__service, self.lp_project.searchTasks(**params))
        bt = BugTasks(self.__service, self.__lp_distribution.searchTasks(**params))
        return bt

    # get_specification - Blueprints
    #
    def get_specification(self, specification_name):
        specification = self.__lp_distribution.getSpecification(name = specification_name)
        if specification is None:
            return None
        return Specification(self.__service, specification)

# vi:set ts=4 sw=4 expandtab:
