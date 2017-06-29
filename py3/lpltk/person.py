#!/usr/bin/python3

from .utils                     import o2str, typecheck_Entry

# Person
#
# A class that provides a convenient interface to a Launchpad person.
# (as returned from a call to the bug.owner property)
#
class Person(object):
    # __init__
    #
    # Initialize the Person instance from a Launchpad bug.
    #
    def __init__(self, tkbug, lpperson):
        if tkbug is not None:
            self.__commit_changes = tkbug.commit_changes
        self.__tkbug           = tkbug
        self.__person          = typecheck_Entry(lpperson)

        self.__username        = None
        self.__full_name       = None
        self.__karma           = None
        self.__email_addresses = None

    def __eq__(self, other):
        if other is None:
            return self.__person is None
        return self.__person == other.__person

    def __ne__(self, other):
        if other is None:
            return self.__person is not None
        return self.__person != other.__person

    #--------------------------------------------------------------------------
    # username
    #
    @property
    def username(self):
        if self.__username is None:
            self.__username = self.lpperson.name
        return self.__username

    #--------------------------------------------------------------------------
    # display_name
    #
    @property
    def display_name(self):
        return self.full_name

    #--------------------------------------------------------------------------
    # full_name
    #
    @property
    def full_name(self):
        if self.__full_name is None:
            self.__full_name = o2str(self.__person.display_name)
        return self.__full_name

    #--------------------------------------------------------------------------
    # first_name
    #
    @property
    def first_name(self):
        if self.__full_name is None:
            self.__full_name = o2str(self.__person.display_name)
        return self.__full_name.split(' ')[0]

    #--------------------------------------------------------------------------
    # email_addresses - list of confirmed email addresses, if not hidden
    #
    @property
    def email_addresses(self):
        if self.__person is None:
            return None
        if self.__email_addresses is None:
            self.__email_addresses = []
            if not self.__person.hide_email_addresses:
                for email_obj in self.__person.confirmed_email_addresses:
                    self.__email_addresses.append(email_obj.email)
        return self.__email_addresses

    #--------------------------------------------------------------------------
    # karma
    #
    @property
    def karma(self):
        if self.__karma is None:
            self.__karma = self.__person.karma
        return self.__karma

    #--------------------------------------------------------------------------
    # lpperson
    #
    @property
    def lpperson(self):
        return self.__person

    #--------------------------------------------------------------------------
    # subscribed_package_names - Returns a list of strings corresponding to
    #     source packages that the person (team) is subscribed to.
    #
    @property
    def subscribed_package_names(self):
        pkgs = []
        for pkg in self.__person.getBugSubscriberPackages():
            pkgs.append(pkg.display_name.split(' ')[0])
        return pkgs

    #--------------------------------------------------------------------------
    # teams - Returns a list of names of teams this person belongs to.
    #
    @property
    def super_teams(self):
        teams = []
        for team in self.__person.super_teams:
            teams.append(o2str(team.name))
        return teams

# vi:set ts=4 sw=4 expandtab:
