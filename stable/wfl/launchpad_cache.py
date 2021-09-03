#!/usr/bin/python3

from launchpadlib.launchpad import Launchpad


class LaunchpadCacheNamedOperation:

    def __init__(self, value, key, cache):
        self.__value = value
        self.__key = key
        self.__cache = cache

    def __call__(self, *args, **kwargs):
        op_key = kwargs[self.__key]
        if op_key not in self.__cache:
            self.__cache[op_key] = self.__value.__call__(*args, **kwargs)
        return self.__cache[op_key]


class LaunchpadCacheAttr:

    def __init__(self, value):
        self.__value = value

    def __getattr__(self, item):
        return self.__value.__getattr__(item)

    def __str__(self):
        return str(self.__value)


class LaunchpadCacheArchives(LaunchpadCacheAttr):

    __reference_cache = {}

    def __init__(self, value):
        super().__init__(value)

        self.getByReference = LaunchpadCacheNamedOperation(value.getByReference, 'reference', self.__reference_cache)


class LaunchpadCacheDistributionsEntry(LaunchpadCacheAttr):

    def __init__(self, value):
        super().__init__(value)

        self.getSeries = LaunchpadCacheNamedOperation(value.getSeries, 'name_or_version', dict())


class LaunchpadCacheDistributions:

    __cache = {}

    def __init__(self, value):
        self.__value = value

    def __getitem__(self, item):
        if item not in self.__cache:
            value = LaunchpadCacheDistributionsEntry(self.__value[item])
            self.__cache[item] = value
        return self.__cache[item]


class LaunchpadCacheProjectsEntry(LaunchpadCacheAttr):

    def __init__(self, value):
        super().__init__(value)
        self.getSeries = LaunchpadCacheNamedOperation(value.getSeries, 'name', dict())


class LaunchpadCacheProjects:

    __cache = {}

    def __init__(self, value):
        self.__value = value

    def __getitem__(self, item):
        if item not in self.__cache:
            value = LaunchpadCacheProjectsEntry(self.__value[item])
            self.__cache[item] = value
        return self.__cache[item]


class LaunchpadCacheGitRepositories(LaunchpadCacheAttr):

    __path_cache = {}

    def __init__(self, value):
        super().__init__(value)

        self.getByPath = LaunchpadCacheNamedOperation(value.getByPath, 'path', self.__path_cache)


class LaunchpadCachePeople:

    __cache = {}

    def __init__(self, value):
        self.__value = value

    def __getitem__(self, item):
        if item not in self.__cache:
            self.__cache[item] = self.__value[item]
        return self.__cache[item]


class LaunchpadCache(Launchpad):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._me = False

        self.archives = LaunchpadCacheArchives(self.archives)
        self.distributions = LaunchpadCacheDistributions(self.distributions)
        self.projects = LaunchpadCacheProjects(self.projects)
        self.git_repositories = LaunchpadCacheGitRepositories(self.git_repositories)
        self.people = LaunchpadCachePeople(self.people)

    @property
    def me(self):
        if self._me is False:
            # Work around a redirect handling issue in python3-lazr.restfulclient
            # which fails when trying to carry over non-GET requests.  Look up
            # my name (via +me), and then manually resolve that name to a user.
            self._me = self.people[self.lp.me.name]
        return self._me
