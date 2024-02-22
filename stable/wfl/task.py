#!/usr/bin/env python
#
from datetime                           import datetime, timezone

from .log                               import cdebug, center, cleave, cinfo, cwarn


# WorkflowBugTask
#
class WorkflowBugTask(object):
    dryrun = False
    no_assignments = False
    no_status_changes = False
    no_timestamps = False

    # __init__
    #
    def __init__(s, lp_task, task_name, package, bug):
        s.__status   = None
        s.__assignee = False
        setattr(s, 'name', task_name)
        setattr(s, 'importance', lp_task.importance)
        setattr(s, 'lp_task', lp_task)
        s.__modified = False
        s.bug = bug
        s.package = package

    @property
    def dryrun(s):
        return WorkflowBugTask.dryrun

    @property
    def no_assignments(s):
        return WorkflowBugTask.no_assignments

    # status
    #
    @property
    def status(s):
        '''
        Property: Gets the status for the task.
        '''
        if s.__status is None:
            s.__status = s.lp_task.status
        return s.__status

    @status.setter
    def status(s, val):
        '''
        Property: Sets the status for the task.
        '''
        center(s.__class__.__name__ + '.status')
        cdebug('    val : %s' % val)
        if s.dryrun or WorkflowBugTask.no_status_changes:
            if s.status != val:
                cinfo('    dryrun - Set task %s to state %s (from %s)' % (s.name, val, s.status), 'red')
            else:
                cinfo('    dryrun - Set task %s to state %s (already %s)' % (s.name, val, s.status), 'yellow')
        else:
            if s.status != val:
                cinfo('    Task %s status changing from %s to %s' % (s.name, s.__status, val), 'yellow')
                s.__modified = True
                s.lp_task.status = val
                s.__status = None
        cleave(s.__class__.__name__ + '.status')

    # reason
    #
    @property
    def reason(s):
        '''
        Property: Gets the current blocking reason.
        '''
        return s.bug.bprops.get('reason', {}).get(s.name, '')

    @reason.setter
    def reason(s, val):
        '''
        Property: Sets the current blocking reason.
        '''
        cwarn("    task-reason {} {}".format(s.name, val))
        s.bug.bprops.setdefault('reason', {})[s.name] = val

    # assignee
    #
    @property
    def assignee(s):
        '''
        Property: Gets the assignee for the task.
        '''
        if s.__assignee is False:
            s.__assignee = s.lp_task.assignee
        return s.__assignee

    @assignee.setter
    def assignee(s, val):
        '''
        Property: Sets the assignee for the task.
        '''
        center(s.__class__.__name__ + '.assignee')
        if s.dryrun or s.no_assignments:
            cinfo('    dryrun - Assign task %s to %s' % (s.name, val), 'red')
        else:
            # FIXME bjf: Turns out that due to s.assignee having never returned an assignee
            #            the following code didn't work as intended. This should be fixed.
            #            In the mean time, just don't try to optimize it.
            #
            # new_assignee = None
            # current_assignee = s.assignee
            # if current_assignee and current_assignee.username != val.name:
            #     new_assignee = val
            # elif not current_assignee:
            #     new_assignee = val
            # if new_assignee:
            #     cdebug('            Task %s assigned to: %s' % (s.name, val), 'red')
            #     s.lp_task.assignee = val
            #     s.__assignee = None
            # else:
            #     cdebug('            Task %s already assigned to %s' % (s.name, val), 'red')
            s.lp_task.assignee = val
            s.__assignee = False
            cinfo('    Task %s assigned to %s' % (s.name, val), 'yellow')
        cleave(s.__class__.__name__ + '.assignee')

    # reason_state
    #
    def reason_state(s, ok_state, acceptable):
        task_start = s.lp_task.date_left_new
        now = datetime.now(timezone.utc)
        cdebug("{} stall check {} {}".format(s.name, now, now - task_start, now - task_start > acceptable))
        state = ok_state
        if now - task_start > acceptable:
            state = 'Stalled'
        else:
            s.bug.refresh_at(task_start + acceptable, "{} stall check {}".format(s.name, acceptable))
        return state

    @property
    def date_confirmed(self):
        return self.lp_task.date_confirmed.replace(tzinfo=None)

    # modified
    #
    @property
    def modified(s):
        return s.__modified

    # timestamp
    #
    def timestamp(s, keyvalue):
        '''
        Add the supplied key with a timestamp. We do not replace existing keys
        '''
        center(s.__class__.__name__ + '.timestamp')

        # if WorkflowBugTask.dryrun or WorkflowBugTask.no_timestamps:
        #     cinfo('    dryrun - Adding timestamp for \'%s\'' % keyvalue, 'red')
        # else:
        #     if s.name not in s.bug.bprops:
        #         s.bug.bprops[s.name] = {}

        #     now = datetime.utcnow().replace(tzinfo=None)
        #     s.bug.bprops[s.name][keyvalue] = date_to_string(now)
        #     cinfo('    Adding timestamp for \'%s\'' % keyvalue)

        cleave(s.__class__.__name__ + '.timestamp')


# WorkflowBugTaskSynthetic
#
class WorkflowBugTaskSynthetic(WorkflowBugTask):

    # __init__
    #
    def __init__(self, task_name, bug):
        self.bug = bug
        self.name = task_name

        self.__status   = None
        self.__assignee = None
        self.importance = 'Medium'
        self.lp_task = None
        self.__modified = False

    # status
    #
    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, val):
        self.__status = val

    # assignee
    #
    @property
    def assignee(self):
        return self.__assignee

    @assignee.setter
    def assignee(self, val):
        self.__assignee = val


class WorkflowBugTaskSynPreparePackages(WorkflowBugTaskSynthetic):

    @property
    def status(self):
        stati = set()
        stati.add('Invalid')
        for task_name, task in self.bug.tasks_by_name.items():
            if task_name.startswith('prepare-package'):
                stati.add(task.status)
            if task_name == 'prepare-package':
                self.assignee = task.assignee

        # Find the most retrograde status.
        for status in (
                'Opinion',
                'Incomplete',
                'Confirmed',
                'Triaged',
                'In Progress',
                'Fix Committed',
                'Fix Released',
                'New',
                'Invalid',
            ):
            if status in stati:
                break

        return status

    @status.setter
    def status(self, val):
        raise ValueError()


class WorkflowBugTaskSynPersistent(WorkflowBugTaskSynthetic):

    @property
    def status(self):
        return self.bug.bprops.get('synthetic', {}).get(self.name, 'New')

    @status.setter
    def status(self, val):
        syn_state = self.bug.bprops.setdefault('synthetic', {})
        syn_state[self.name] = val


# vi:set ts=4 sw=4 expandtab:
