#!/usr/bin/python3

from lpltk.person             import Person
from lpltk.project_series     import ProjectSeries
from lpltk.distro_series      import DistroSeries
from lpltk.bug_target         import BugTarget
from lpltk.utils              import typecheck_Entry

class Nomination(object):
    # __init__
    #
    def __init__(self, service, bug, lp_nomination):
        self.__service        = service
        self.__bug            = bug
        self.__lp_nomination  = typecheck_Entry(lp_nomination)
        self.__date_created   = None
        self.__date_decided   = None
        self.__status         = None
        self.__distro_series  = None
        self.__product_series = None
        self.__target         = None
        self.__can_approve    = None

    @property
    def date_created(self):
        if self.__date_created == None:
            self.__date_created = self.__lp_nomination.date_created
        return self.__date_created

    @property
    def date_decided(self):
        if self.__date_decided == None:
            self.__date_decided = self.__lp_nomination.date_decided
        return self.__date_decided

    @property
    def decider(self):
        if self.__decider == None:
            self.__decider = Person(self.__bug, self.__lp_nomination.decider)
        return self.__decider

    @property
    def owner(self):
        if self.__owner == None:
            self.__owner = Person(self.__bug, self.__lp_nomination.owner)
        return self.__owner

    @property
    def status(self):
        if self.__status == None:
            self.__status = self.__lp_nomination.status
        return self.__status

    @property
    def distro_series(self):
        if self.__distro_series == None:
            lp_ds = self.__lp_nomination.distroseries
            if lp_ds != None:
                self.__distro_series = DistroSeries(self.__service, self.__bug, lp_ds)
        return self.__distro_series

    @property
    def target(self):
        if self.__target == None:
            self.__target = BugTarget(self.__service, self.__bug, self.__lp_nomination.target)
        return self.__target

    @property
    def product_series(self):
        if self.__product_series == None:
            lp_ps = self.__lp_nomination.productseries
            if lp_ps != None:
                self.__product_series = ProjectSeries(self.__service, self.__bug, lp_ps)
        return self.__product_series

    def decline(self):
        self.__lp_nomination.decline()

    def approve(self):
        self.__lp_nomination.approve()

    def can_approve(self):
        if self.__can_approve == None:
            self.__can_approve =  self.__lp_nomination.canApprove()
        return self.__can_approve

# vi:set ts=4 sw=4 expandtab:
