#!/usr/bin/python

from utils                        import (
    o2str,
    typecheck_Entry
    )

# Milestone
#
# A class that provides a convenient interface to a Launchpad milestone.
#
class Milestone(object):
    # __init__
    #
    # Initialize the Bug instance from a Launchpad bug.
    #
    def __init__(self, service, lp_milestone, commit_changes=True):
        self.__service        = service
        self.__lp_milestone   = typecheck_Entry(lp_milestone)
        self.__commit_changes = commit_changes

    @property
    def code_name(self):
        return o2str(self.__lp_milestone.code_name)

    @property
    def date_targeted(self):
        return self.__lp_milestone.date_targeted

    @property
    def is_active(self):
        return self.__lp_milestone.is_active

    @property
    def name(self):
        return o2str(self.__lp_milestone.name)

    @property
    def summary(self):
        return o2str(self.__lp_milestone.summary)

    @property
    def title(self):
        return o2str(self.__lp_milestone.title)

    @property
    def raw(self):
        return self.__lp_milestone


# vi:set ts=4 sw=4 expandtab:

