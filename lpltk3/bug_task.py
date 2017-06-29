#!/usr/bin/python3

from .person                           import Person
from .bug                              import Bug
from .bugs                             import Bugs
from .milestone                        import Milestone
from .utils                            import (o2str, typecheck_Entry)

# BugTask
#
class BugTask(object):
    # __init__
    #
    def __init__(self, service, lp_bug_task):
        self.__service                 = service
        self.lp_bug_task               = typecheck_Entry(lp_bug_task)

        self.__assignee                = None
        self.__bug_target_display_name = None
        self.__bug_target_name         = None
        self.__bug_watch               = None
        self.__date_assigned           = None
        self.__date_closed             = None
        self.__date_confirmed          = None
        self.__date_created            = None
        self.__date_fix_committed      = None
        self.__date_fix_released       = None
        self.__date_importance_set     = None
        self.__date_in_progress        = None
        self.__date_incomplete         = None
        self.__date_left_closed        = None
        self.__date_left_new           = None
        self.__date_triaged            = None
        self.__importance              = None
        self.__is_complete             = None
        self.__milestone               = None
        self.__owner                   = None
        self.__similar_bugs            = None
        self.__target                  = None
        self.__title                   = None
        self.__upstream_bug_tracker    = None
        self.__upstream_product        = None
        self.__web_link                = None

    # __str__
    #
    def __str__(self):
        return self.display_name

    # owner
    #
    @property
    def owner(self):
        if self.__owner is None:
            lp_owner = self.lp_bug_task.owner
            if lp_owner is not None:
                self.__owner = Person(None, self.lp_bug_task.owner)
        return self.__owner

    @property
    def owner_name(self):
        if self.owner is not None:
            return o2str(self.owner.username)
        else:
            return None

    # bug_target_display_name
    #
    @property
    def bug_target_display_name(self):
        if self.__bug_target_display_name is None:
            self.__bug_target_display_name = self.lp_bug_task.bug_target_display_name
        return self.__bug_target_display_name

    # bug_target_name
    #
    @property
    def bug_target_name(self):
        if self.__bug_target_name is None:
            self.__bug_target_name = self.lp_bug_task.bug_target_name
        return self.__bug_target_name

    # bug
    #
    @property
    def bug(self):
        return Bug(self.__service, self.lp_bug_task.bug.id)

    # status
    #
    @property
    def status(self):
        return self.lp_bug_task.status

    @status.setter
    def status(self, value):
        if value == 'Incomplete' and self.lp_bug_task.status == 'Incomplete':
            self.lp_bug_task.status = 'New'
            self.lp_bug_task.lp_save()

        self.lp_bug_task.status = value
        self.lp_bug_task.lp_save()
        return

    # title
    #
    @property
    def title(self):
        if self.__title is None:
            self.__title = self.lp_bug_task.title
        return self.__title

    # is_complete
    #
    @property
    def is_complete(self):
        if self.__is_complete is None:
            self.__is_complete = self.lp_bug_task.is_complete
        return self.__is_complete

    # importance
    #
    @property
    def importance(self):
        if self.__importance is None:
            self.__importance = self.lp_bug_task.importance
        return self.__importance

    @importance.setter
    def importance(self, value):
        self.lp_bug_task.importance = value
        self.lp_bug_task.lp_save()
        return

    # assignee
    #
    @property
    def assignee(self):
        if self.__assignee is None:
            lp_assignee = self.lp_bug_task.assignee
            if lp_assignee is not None:
                self.__assignee = Person(None, self.lp_bug_task.assignee)
        return self.__assignee

    @assignee.setter
    def assignee(self, value):
        self.lp_bug_task.assignee = value
        self.lp_bug_task.lp_save()
        return

    @property
    def assignee_name(self):
        if self.assignee is not None:
            return o2str(self.assignee.username)
        else:
            return None

    # date_assigned
    #
    @property
    def date_assigned(self):
        if self.__date_assigned is None:
            self.__date_assigned = self.lp_bug_task.date_assigned
        return self.__date_assigned

    # date_closed
    #
    @property
    def date_closed(self):
        if self.__date_closed is None:
            self.__date_closed = self.lp_bug_task.date_closed
        return self.__date_closed

    # date_confirmed
    #
    @property
    def date_confirmed(self):
        if self.__date_confirmed is None:
            self.__date_confirmed = self.lp_bug_task.date_confirmed
        return self.__date_confirmed

    # date_created
    #
    @property
    def date_created(self):
        if self.__date_created is None:
            self.__date_created = self.lp_bug_task.date_created
        return self.__date_created

    # date_fix_committed
    #
    @property
    def date_fix_committed(self):
        if self.__date_fix_committed is None:
            self.__date_fix_committed = self.lp_bug_task.date_fix_committed
        return self.__date_fix_committed

    # date_fix_released
    #
    @property
    def date_fix_released(self):
        if self.__date_fix_released is None:
            self.__date_fix_released = self.lp_bug_task.date_fix_released
        return self.__date_fix_released

    # date_in_progress
    #
    @property
    def date_in_progress(self):
        if self.__date_in_progress is None:
            self.__date_in_progress = self.lp_bug_task.date_in_progress
        return self.__date_in_progress

    # date_incomplete
    #
    @property
    def date_incomplete(self):
        if self.__date_incomplete is None:
            self.__date_incomplete = self.lp_bug_task.date_incomplete
        return self.__date_incomplete

    # date_left_closed
    #
    @property
    def date_left_closed(self):
        if self.__date_left_closed is None:
            self.__date_left_closed = self.lp_bug_task.date_left_closed
        return self.__date_left_closed

    # date_left_new
    #
    @property
    def date_left_new(self):
        if self.__date_left_new is None:
            self.__date_left_new = self.lp_bug_task.date_left_new
        return self.__date_left_new

    # date_triaged
    #
    @property
    def date_triaged(self):
        if self.__date_triaged is None:
            self.__date_triaged = self.lp_bug_task.date_triaged
        return self.__date_triaged

    # determine the date the importance was set using bug activity
    #
    @property
    def date_importance_set(self):
        if (self.__date_importance_set is None and self.importance not in ['Undecided', 'Unknown']):
            target = self.bug_target_name
            for activity in self.bug.activity:
                if (activity.new_value == self.importance and activity.what_changed.split(':')[0] == target):
                    self.__date_importance_set = activity.date_changed
                    return self.__date_importance_set

    # milestone
    #
    @property
    def milestone(self):
        if self.__milestone is None:
            milestone = self.lp_bug_task.milestone
            if milestone is not None:
                self.__milestone = Milestone(self.__service, milestone)
        return self.__milestone

    # product
    #
    @property
    def upstream_product(self):
        if self.__upstream_product is None:
            self.__upstream_product = self.lp_bug_task.target.upstream_product
        return self.__upstream_product

    # bugtracker
    #
    @property
    def upstream_bug_tracker(self):
        if self.__upstream_bug_tracker is None:
            if self.upstream_product is None:
                return None
            self.__upstream_bug_tracker = self.upstream_product.bug_tracker
            if self.__upstream_bug_tracker is None:
                # If project is in a project group, the group may have bt info
                project_group = self.upstream_product.project_group
                if project_group:
                    self.__upstream_bug_tracker = project_group.bug_tracker
        return self.__upstream_bug_tracker

    # related_tasks
    #
    @property
    def related_tasks(self):
        # The following import is done here to work around a circular import
        # issue. bug_tasks imports bug.
        #
        from .bug_tasks import BugTasks

        return BugTasks(self.__service, self.lp_bug_task.related_tasks_collection)

    # target
    #
    @property
    def target(self):
        if self.__target is None:
            self.__target = self.lp_bug_task.target
        return self.__target

    @target.setter
    def target(self, value):
        self.lp_bug_task.target = value
        self.lp_bug_task.lp_save()

    # bug_watch
    #
    @property
    def bug_watch(self):
        if self.__bug_watch is None:
            self.__bug_watch = self.lp_bug_task.bug_watch
        return self.__bug_watch

    # similar_bugs
    #
    @property
    def similar_bugs(self):
        if self.__similar_bugs is None:
            self.__similar_bugs = self.lp_bug_task.findSimilarBugs()
        return Bugs(self.__service, self.__similar_bugs)

    # web_link
    #
    @property
    def web_link(self):
        if self.__web_link is None:
            self.__web_link = self.lp_bug_task.web_link
        return self.__web_link

    # to_dict
    #
    def to_dict(self):
        package = self.bug_target_display_name
        source_pkg = package.replace(" (Ubuntu)", "")
        return {
            'date_created'     : o2str(self.date_created),
            'date_closed'      : o2str(self.date_closed),
            'date_fix_released': o2str(self.date_fix_released),
            'is_complete'      : self.is_complete,
            'assignee'         : self.assignee_name,
            'target'           : source_pkg,
            'status'           : o2str(self.status),
            'importance'       : o2str(self.importance),
        }

# vi:set ts=4 sw=4 expandtab:
