#!/usr/bin/python

import sys
from bug_task                        import BugTask
from utils                           import (
    typecheck_Collection,
    typecheck_Entry,
    )

class BugTasks(object):
    # __init__
    #
    # Initialize the instance from a Launchpad bug.
    #
    def __init__(self, service, lp_tasks):
        self.__service       = service
        self.__lp_tasks      = typecheck_Collection(lp_tasks)

        self.__filter_distro = None
        self.__filter_status = None
        self.__filter_bug_tracker_type = None
        self.__filtered_tasks = None

    def filtered_tasks(self):
        if self.__filtered_tasks is None:
            self.__filtered_tasks = list(self.__iter__())
        return self.__filtered_tasks

    # __len__
    #
    def __len__(self):
        return len(self.filtered_tasks())

    # __getitem__
    #
    def __getitem__(self, key):
        tasks = self.filtered_tasks()
        return tasks[key]

    # __iter__
    #
    def __iter__(self):
        for task in self.__lp_tasks:
            if self.__filter_distro:
                if self.__filter_distro not in task.bug_target_display_name:
                    continue

            if self.__filter_status:
                status = self.__filter_status
                is_complete = task.is_complete
                if status == 'open' and is_complete:
                    continue
                if status == 'complete' and not is_complete:
                    continue
                if status not in ['open', 'complete'] and task.status != status:
                    continue

            if self.__filter_bug_tracker_type:
                bt_type = self.__filter_bug_tracker_type
                upstream_product = task.target.upstream_product
                if upstream_product is None:
                    continue
                bt = upstream_product.bug_tracker
                if bt is None:
                    # Is this part of a project group?
                    project_group = upstream_product.project_group
                    if project_group is not None:
                        bt = project_group.bug_tracker
                if bt is None:
                    sys.stderr.write("No bug tracker found for upstream product\n")
                    continue
                sys.stderr.write("Bug tracker type: %s (looking for %s)\n" %(bt.bug_tracker_type, bt_type))
                if bt.bug_tracker_type != bt_type:
                    continue

            d = BugTask(self.__service, task)
            yield d

    # __contains__
    #
    def __contains__(self, item):
        return item in self.__iter__()

    # Filters
    def set_filter_by_distro(self, distroname='Ubuntu'):
        '''Only include tasks that are targeted to the given distro'''
        self.__filter_distro = distroname
        self.__filtered_tasks = None

    def set_filter_by_status(self, state):
        '''Include tasks only in the specified state

        The regular bug statuses "Incomplete", "Fix Committed", et al
        are supported, as well as special keywords 'open' and 'complete'.
        '''
        self.__filter_status = state
        self.__filtered_tasks = None

    def set_filter_by_bug_tracker_type(self, bugtracker_type):
        '''Include only tasks for upstream projects using this type of bug tracker'''
        self.__filter_bug_tracker_type = bugtracker_type
        self.__filtered_tasks = None

# vi:set ts=4 sw=4 expandtab:
