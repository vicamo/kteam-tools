#!/usr/bin/python3

from lpltk.message              import Message

class Messages(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, tkbug):
        self.__tkbug                = tkbug
        self.__commit_changes       = tkbug.commit_changes
        self.__messages             = None

    # __len__
    #
    def __len__(self):
        return len(list(self.__iter__()))

    # __getitem__
    #
    def __getitem__(self, key):
        return list(self.__iter__())[key]

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for msg in self.__messages:
            m = Message(self.__tkbug, msg)
            yield m

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__messages == None:
            self.__messages = self.__tkbug.lpbug.messages_collection


# vi:set ts=4 sw=4 expandtab:
