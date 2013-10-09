#!/usr/bin/env python
#
from logging                            import info, debug, error, warning, basicConfig, INFO, DEBUG, WARNING
import re

from ktl.termcolor                      import colored
from ktl.ubuntu                         import Ubuntu
from sb.log                             import cinfo

# WorkflowBugTask
#
class WorkflowBugTask(object):
    # __init__
    #
    def __init__(s, lp_task, task_name, dryrun):
        s.dryrun = dryrun
        s.__status   = None
        s.__assignee = None
        setattr(s, 'name', task_name)
        setattr(s, 'importance', lp_task.importance)
        setattr(s, 'lp_task', lp_task)
        s.bug = lp_task.bug

    # status
    #
    @property
    def status(s):
        if s.__status is None:
            s.__status = s.lp_task.status
        return s.__status

    @status.setter
    def status(s, val):
        if s.dryrun:
            cinfo('        ')
            cinfo('Dryrun - Set task %s to state %s' % (s.name, val), 'red')
        else:
            if s.status != val:
                s.lp_task.status = val
                s.__status = None
                cinfo('            Task %s status: %s' % (s.name, val), 'red')
            else:
                cinfo('            Task %s already %s' % (s.name, val), 'red')

    # assignee
    #
    @property
    def assignee(s):
        if s.__assignee is None:
            assignee = s.lp_task.assignee
            if assignee is None:
                s.__assignee = '*Unassigned'
            else:
                s.__assignee = assignee.display_name

    @assignee.setter
    def assignee(s, val):
        if s.dryrun:
            cinfo('        ')
            cinfo('Dryrun - Assign task %s to %s' % (s.name, val), 'red')
        else:
            new_assignee = None
            current_assignee = s.assignee
            if current_assignee and current_assignee.username != val.name:
                new_assignee = val
            elif not current_assignee:
                new_assignee = val
            if new_assignee:
                cinfo('            Task %s assigned to: %s' % (s.name, val), 'red')
                s.lp_task.assignee = val
                s.__assignee = None
            else:
                cinfo('            Task %s already assigned to %s' % (s.name, val), 'red')

# WorkflowBug
#
class WorkflowBug():
    # __init__
    #
    def __init__(s, lp, projects, bugid, sauron=False, dryrun=False):
        s.lp = lp
        s.lpbug = s.lp.get_bug(bugid)
        s.projects = projects
        s.sauron = sauron
        s.title = s.lpbug.title
        s.dryrun = dryrun

        s.__package_name = None

        cinfo('                      title: "%s"' % s.title, 'blue')

        try:
            s.pkg_name = re.findall('linux[^:]*', s.title)[0]
        except IndexError:
            s.pkg_name = None
        cinfo('                   pkg_name: "%s"' % s.pkg_name, 'blue')

        try:
            s.pkg_version = re.findall('([0-9]+\.[^ ]+)', s.title)[0]
        except IndexError:
            s.pkg_version = None
        cinfo('                pkg_version: "%s"' % s.pkg_version, 'blue')

        if s.pkg_name is not None and s.pkg_version is not None:
            s.series = Ubuntu().series_name(s.pkg_name, s.pkg_version)
        else:
            s.series = None
        cinfo('                     series: "%s"' % s.series, 'blue')

        # If a bug isn't to be processed, detect this as early as possible.
        #
        s.is_valid = s.check_is_valid(s.lpbug)

        if s.is_valid:
            cinfo('    Targeted Project:', 'cyan')
            cinfo('        %s' % s.targeted_project)
            cinfo('')
            s.properties = s.lpbug.properties
            if len(s.properties) > 0:
                cinfo('    Properties:', 'cyan')
                for prop in s.properties:
                    cinfo('        %s: %s' % (prop, s.properties[prop]))

            s.tasks_by_name = s.create_tasks_by_name()

    # check_is_valid
    #
    def check_is_valid(s, bug):
        '''
        Determine if this bug is one that we wan't to be processing.
        '''
        retval = True
        for t in s.lpbug.tasks:
            task_name       = t.bug_target_name

            if task_name in s.projects:
                s.targeted_project = task_name
                if t.status == 'In Progress':
                    continue
                else:
                    if s.sauron:
                        continue
                    cinfo('        Not processing this bug because master task state is set to %s' % (t.status))
                    cinfo('        Quitting this bug')
                    retval = False

        return retval

    # create_tasks_by_name
    #
    def create_tasks_by_name(s):
        '''
        We are only interested in the tasks that are specific to the workflow project. Others
        are ignored.
        '''
        tasks_by_name = {}

        cinfo('')
        cinfo('    Scanning bug tasks:', 'cyan')

        for t in s.lpbug.tasks:
            task_name       = t.bug_target_name

            if task_name.startswith(s.targeted_project):
                if '/' in task_name:
                    task_name = task_name[len(s.targeted_project)+1:].strip()
                tasks_by_name[task_name] = WorkflowBugTask(t, task_name, s.dryrun)
            else:
                cinfo('')
                cinfo('        %-25s' % (task_name))
                cinfo('            Action: Skipping non-workflow task')

        return tasks_by_name


