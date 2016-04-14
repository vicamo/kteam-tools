#!/usr/bin/python3

from lpltk.person                   import Person
from lpltk.bugs                     import Bugs
from lpltk.utils                    import (
    o2str,
    typecheck_Entry
    )

class Specification(object):
    # __init__
    #
    def __init__(self, service, specification):
        self.__service               = service
        self.__lp_specification      = typecheck_Entry(specification)

        self.__owner                 = None
        self.__approver              = None
        self.__drafter               = None
        self.__assignee              = None
        self.__starter               = None
        self.__completer             = None

        self.__date_created          = None
        self.__date_started          = None
        self.__date_completed        = None

        self.__priority              = None
        self.__definition_status     = None
        self.__implementation_status = None
        self.__lifecycle_status      = None
        self.__milestone             = None

        self.__approved              = None
        self.__complete              = None
        self.__started               = None

        self.__name                  = None
        self.__summary               = None
        self.__title                 = None
        self.__whiteboard            = None
        self.__url                   = None

        self.__bugs                  = None
        self.__dependencies          = None

    # People
    @property
    def owner(self):
        if self.__owner == None:
            self.__owner = Person(self.__bug, self.__lp_specification.owner)
        return self.__owner

    @property
    def approver(self):
        if self.__approver == None:
            self.__approver = Person(self.__bug, self.__lp_specification.approver)
        return self.__approver

    @property
    def drafter(self):
        if self.__drafter == None:
            self.__drafter = Person(self.__bug, self.__lp_specification.drafter)
        return self.__drafter

    @property
    def assignee(self):
        if self.__assignee == None:
            self.__assignee = Person(self.__bug, self.__lp_specification.assignee)
        return self.__assignee

    @property
    def starter(self):
        if self.__starter == None:
            self.__starter = Person(self.__bug, self.__lp_specification.starter)
        return self.__starter

    @property
    def completer(self):
        if self.__completer == None:
            self.__completer = Person(self.__bug, self.__lp_specification.completer)
        return self.__completer

    # Dates
    @property
    def date_created(self):
        if self.__date_created == None:
            self.__date_created = self.__lp_specification.date_created
        return self.__date_created

    @property
    def date_started(self):
        if self.__date_started == None:
            self.__date_started = self.__lp_specification.date_started
        return self.__date_started

    @property
    def date_completed(self):
        if self.__date_completed == None:
            self.__date_completed = self.__lp_specification.date_completed
        return self.__date_completed

    # State tracking
    @property
    def importance(self):
        if self.__importance == None:
            self.__importance = self.__lp_specification.importance
        return self.__importance

    @property
    def definition_status(self):
        if self.__definition_status == None:
            self.__definition_status = self.__lp_specification.definition_status
        return self.__definition_status

    @property
    def implementation_status(self):
        if self.__implementation_status == None:
            self.__implementation_status = self.__lp_specification.implementation_status
        return self.__implementation_status

    @property
    def lifecycle_status(self):
        if self.__lifecycle_status == None:
            self.__lifecycle_status = self.__lp_specification.lifecycle_status
        return self.__lifecycle_status

    @property
    def milestone(self):
        if self.__milestone == None:
            self.__milestone = self.__lp_specification.milestone
        return self.__milestone

    # State tests
    @property
    def approved(self):
        if self.__approved == None:
            self.__approved = self.__lp_specification.direction_approved
        return self.__approved

    @property
    def complete(self):
        if self.__complete == None:
            self.__complete = self.__lp_specification.complete
        return self.__complete

    @property
    def started(self):
        if self.__started == None:
            self.__started = self.__lp_specification.started
        return self.__started

    # Text
    @property
    def name(self):
        if self.__name == None:
            self.__name = o2str(self.__lp_specification.name)
        return self.__name

    @property
    def summary(self):
        if self.__summary == None:
            self.__summary = o2str(self.__lp_specification.summary)
        return self.__summary

    @property
    def title(self):
        if self.__title == None:
            self.__title = o2str(self.__lp_specification.title)
        return self.__title

    @property
    def whiteboard(self):
        if self.__whiteboard == None:
            self.__whiteboard = o2str(self.__lp_specification.whiteboard)
        return self.__whiteboard

    @property
    def url(self):
        if self.__url == None:
            self.__url = self.__lp_specification.specification_url
        return self.__url

    # Collections
    @property
    def bugs(self):
        if self.__bugs == None:
            self.__bugs = Bugs(self.__service,
                self.__lp_specification.bugs)
        return self.__bugs

    @property
    def dependencies(self):
        if self.__dependencies == None:
            # Work around circular dependencies
            from specifications import Specifications

            self.__dependencies = Specifications(self.__service,
                self.__lp_specification.dependencies_collection)
        return self.__dependencies

# vi:set ts=4 sw=4 expandtab:
