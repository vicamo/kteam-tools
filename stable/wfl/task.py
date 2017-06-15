#!/usr/bin/env python
#
from .log                               import cdebug, center, cleave, cinfo


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
        s.__assignee = None
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

    # assignee
    #
    @property
    def assignee(s):
        '''
        Property: Gets the assignee for the task.
        '''
        if s.__assignee is None:
            assignee = s.lp_task.assignee
            if assignee is None:
                s.__assignee = '*Unassigned'
            else:
                s.__assignee = assignee.display_name
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
            s.__assignee = None
            cinfo('    Task %s assigned to %s' % (s.name, val), 'yellow')
        center(s.__class__.__name__ + '.assignee')

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

# vi:set ts=4 sw=4 expandtab:
