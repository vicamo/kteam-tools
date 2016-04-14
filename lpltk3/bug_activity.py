#!/usr/bin/python3

from lpltk.person                   import Person
from lpltk.utils                    import (
    o2str,
    typecheck_Entry
    )

class Activity(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, service, bug):
        self.__service       = service
        self.__bug           = bug
        self.__lp_activities = None

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        self.__fetch_if_needed()
        return BugActivity(self.__service, self.__bug, self.__lp_activities[key])

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for activity in self.__lp_activities:
            n = BugActivity(self.__service, self.__bug, activity)
            yield n

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__lp_activities == None:
            self.__lp_activities = self.__bug.lpbug.activity

class BugActivity(object):
    # __init__
    #
    def __init__(self, service, bug, lp_bug_activity):
        self.__service           = service
        self.__bug               = bug
        self.__lp_bug_activity   = typecheck_Entry(lp_bug_activity)
        self.__date_changed      = None
        self.__person            = None
        self.__old_value         = None
        self.__new_value         = None
        self.__message           = None
        self.__what_changed      = None

    @property
    def date_changed(self):
        if self.__date_changed == None:
            self.__date_changed = self.__lp_bug_activity.datechanged
        return self.__date_changed

    @property
    def person(self):
        if self.__person == None:
            self.__person = Person(self.__bug, self.__lp_bug_activity.person)
        return self.__person

    @property
    def old_value(self):
        if self.__old_value == None:
            self.__old_value = self.__lp_bug_activity.oldvalue
        return self.__old_value

    @property
    def new_value(self):
        if self.__new_value == None:
            self.__new_value = self.__lp_bug_activity.newvalue
        return self.__new_value

    @property
    def what_changed(self):
        if self.__what_changed == None:
            self.__what_changed = self.__lp_bug_activity.whatchanged
        return self.__what_changed

    @property
    def message(self):
        if self.__message == None:
            self.__message = o2str(self.__lp_bug_activity.message)
        return self.__message

# vi:set ts=4 sw=4 expandtab:
