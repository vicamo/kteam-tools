#!/usr/bin/python3

from lpltk.utils                import (
    o2str,
    typecheck_Entry
    )
from lpltk.person               import Person

# Message
#
class Message(object):
    # __init__
    #
    def __init__(self, tkbug, lpmessage):
        self.__tkbug          = tkbug
        self.__commit_changes = tkbug.commit_changes
        self.__message        = typecheck_Entry(lpmessage)
        self.__owner          = None
        self.__content        = None
        self.__date_created   = None
        self.__parent         = None
        self.__subject        = None

    # owner
    #
    @property
    def owner(self):
        if self.__owner == None:
            self.__owner = Person(self.__tkbug, self.__message.owner)
        return self.__owner

    # content
    @property
    def content(self):
        if self.__content == None:
            self.__content = o2str(self.__message.content)
        return self.__content

    # date_created
    @property
    def date_created(self):
        if self.__date_created == None:
            self.__date_created = self.__message.date_created
        return self.__date_created

    # parent
    @property
    def parent(self):
        if self.__parent == None:
            self.__parent = Message(self.__tkbug, self.__message.parent)
        return self.__parent

    # subject
    @property
    def subject(self):
        if self.__subject == None:
            self.__subject = o2str(self.__message.subject)
        return self.__subject

# vi:set ts=4 sw=4 expandtab:
