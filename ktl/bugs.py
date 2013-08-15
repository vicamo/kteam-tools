#!/usr/bin/env python
#

from ktl.utils                          import date_to_string

# DeltaTime
#
class DeltaTime():
    # __init__
    #
    def __init__(self, date, now):
        now = now.replace(tzinfo=None)
        delta = now - date.replace(tzinfo=None)
        seconds_diff = (delta.days * 86400) + delta.seconds

        sec_p_hr = 60 * 60
        self.__hours = delta.seconds / sec_p_hr
        dhs = self.__hours * sec_p_hr
        remaining_seconds = delta.seconds - dhs

        self.__minutes = (delta.seconds - dhs) / 60
        dhm = self.__minutes * 60
        self.__seconds = remaining_seconds - dhm

        if delta.days < 1:
            self.__days = 0
        else:
            self.__days = delta.days

        return

    @property
    def days(self):
        return self.__days

    @property
    def hours(self):
        return self.__hours

    @property
    def minutes(self):
        return self.__minutes

    @property
    def seconds(self):
        return self.__seconds

# Bugs
#
class Bugs():
    """
    A class for collecting methods that may be used by multiple scripts that
    work on Launchpad bugs.
    """

    # bug_info
    #
    @classmethod
    def bug_info(cls, bug, now, task=None):
        """
        Access specific elements of a LP bug and build up a dictionary of it's properties.
        """
        bug_item  = {}

        # Bug info (non task specific)
        #
        bug_item['title']      = bug.title

        for tag in bug.tags:
            if 'tags' not in bug_item:
                bug_item['tags'] = []
            bug_item['tags'].append(tag)

        bug_item['heat']               = bug.heat
        bug_item['number_of_messages'] = len(bug.messages)
        bug_item['number_affected']    = bug.lpbug.users_affected_count
        subs_num = 0
        for sub in bug.lpbug.subscriptions:
            subs_num += 1
        bug_item['number_subscribed']  = subs_num

        bug_item['date created']      = date_to_string(bug.date_created)
        bug_item['date last updated'] = date_to_string(bug.date_last_updated)
        bug_item['date last message'] = date_to_string(bug.date_last_message)

        messages = bug.messages
        bug_item['number of messages'] = len(messages)

        bug_item['properties'] = {}
        for x in bug.properties:
            bug_item['properties'][x] = bug.properties[x]

        # Task info:
        #
        if task is not None:
            bug_item['status']     = task.status
            bug_item['importance'] = task.importance

            assignee = task.assignee
            if assignee is None:
                bug_item['assignee'] = 'Unassigned'
                bug_item['assignee-name'] = 'unassigned'
            else:
                bug_item['assignee'] = assignee.display_name
                bug_item['assignee-name'] = assignee.lpperson.name

        for task in bug.tasks:
            task_item = {}
            if 'tasks' not in bug_item:
                bug_item['tasks'] = []

            task_item['name']       = task.bug_target_display_name
            task_item['target-name']= task.bug_target_name
            task_item['status']     = task.status
            task_item['importance'] = task.importance

            assignee = task.assignee
            if assignee is None:
                task_item['assignee'] = 'Unassigned'
                task_item['assignee-name'] = 'unassigned'
            else:
                task_item['assignee'] = assignee.display_name
                task_item['assignee-name'] = assignee.lpperson.name
            bug_item['tasks'].append(task_item)

        # Misc.
        #
        (bug_item['series name'], bug_item['series version']) = bug.series
        bug_item['kernel_gravity']         = bug.kernel_gravity
        bug_item['booted_kernel_version'] = bug.booted_kernel_version if bug.booted_kernel_version is not None else ''
        return bug_item

# vi:set ts=4 sw=4 expandtab:
