#!/usr/bin/python3

class BugTags(object):
    # __init__
    #
    def __init__(self, tkbug):
        self.__tkbug          = tkbug
        self.__tags           = None
        self.__commit_changes = tkbug.commit_changes

    # __len__
    #
    def __len__(self):
        self.__fetch_if_needed()
        return len(self.__tags)

    # __getitem__
    #
    def __getitem__(self, key):
        self.__fetch_if_needed()
        return self.__tags[key]

    # __setitem__
    #
    def __setitem__(self, key, value):
        self.__fetch_if_needed()
        self.__tags[key] = value
        self.__save_tags()

    # __delitem__
    #
    def __delitem__(self, key):
        self.__fetch_if_needed()
        del self.__tags[key]
        self.__save_tags()

    # __iter__
    #
    def __iter__(self):
        self.__fetch_if_needed()
        for tag in self.__tags:
            yield tag

    # __contains__
    #
    def __contains__(self, item):
        self.__fetch_if_needed()
        return item in self.__tags

    # __save_tags
    #
    def __save_tags(self):
        if self.__commit_changes:
            self.__tkbug.lpbug.tags = self.__tags
            self.__tkbug.lpbug.lp_save()

    # __fetch_if_needed
    #
    def __fetch_if_needed(self):
        if self.__tags == None:
            self.__tags = self.__tkbug.lpbug.tags

    # append
    #
    def append(self, item):
        self.__fetch_if_needed()
        if not isinstance(item, str):
            raise TypeError("Must be a string")
        self.__tags.append(item)
        self.__save_tags()

    # extend
    #
    def extend(self, items):
        self.__fetch_if_needed()
        if not isinstance(items, list):
            raise TypeError("Must be a list")
        self.__tags.extend(items)
        self.__save_tags()

    # remove
    #
    def remove(self, item):
        self.__fetch_if_needed()
        if not isinstance(item, str):
            raise TypeError("Must be a string")
        self.__tags.remove(item)
        self.__save_tags()

# vi:set ts=4 sw=4 expandtab:
