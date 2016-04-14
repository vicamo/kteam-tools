#!/usr/bin/python3

from lpltk.bug_tasks                   import BugTasks
from lpltk.milestone                   import Milestone
from lpltk.utils                       import typecheck_Entry

# DistributionSourcePackage
#
class DistributionSourcePackage(object):
    # __init__
    #
    def __init__(self, service, lp_distribution_source_package):
        self.__service         = service
        self.lp_source_package = typecheck_Entry(lp_distribution_source_package)
        self.__display_name    = None
        self.__name            = None
        self.__title           = None

    # display_name
    #
    @property
    def display_name(self):
        if self.__display_name == None:
            self.__display_name = self.lp_source_package.display_name
        return self.__display_name

    # name
    #
    @property
    def name(self):
        if self.__name == None:
            self.__name = self.lp_source_package.name
        return self.__name

    # title
    #
    @property
    def title(self):
        if self.__title == None:
            self.__title = self.lp_source_package.title
        return self.__title

    # searchTasks
    #
    def search_tasks(self, **params):
        if 'milestone' in params and isinstance(params['milestone'], Milestone):
            params['milestone'] = params['milestone'].raw
        bt = BugTasks(self.__service, self.lp_source_package.searchTasks(**params))
        return bt

# vi:set ts=4 sw=4 expandtab:
