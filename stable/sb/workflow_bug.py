#!/usr/bin/env python
#
from logging                            import info, debug, error, warning, basicConfig, INFO, DEBUG, WARNING

from sb.log                             import cinfo, cdebug
from sb.package                         import Package, PackageError

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
        s.__modified = False
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
                s.__modified = True
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

    # modified
    #
    @property
    def modified(s):
        return s.__modified

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

        # If a bug isn't to be processed, detect this as early as possible.
        #
        s.is_valid = s.check_is_valid(s.lpbug)

        try:
            s.__package = Package(s.lp, s)

            cinfo('                      title: "%s"' % s.title, 'blue')
            cinfo('                   pkg_name: "%s"' % s.__package.name, 'blue')
            cinfo('                pkg_version: "%s"' % s.__package.version, 'blue')
            cinfo('                     series: "%s"' % s.__package.series, 'blue')
            for d in s.__package.pkgs:
                cinfo('                        dep: "%s"' % d, 'blue')

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
        except PackageError:
            s.is_valid = False

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

    # package_fully_built
    #
    def package_fully_built(s, pkg):
        cdebug('                WorkflowBug::package_fully_built enter')
        retval = s.__package.fully_built(pkg)
        cdebug('                WorkflowBug::package_fully_built leave (True)')
        return retval

    # all_dependent_packages_fully_built
    #
    def all_dependent_packages_fully_built(s):
        cdebug('                WorkflowBug::all_dependent_packages_fully_built enter')
        retval = s.__package.all_dependent_packages_fully_built()
        cdebug('                WorkflowBug::all_dependent_packages_fully_built leave (True)')
        return retval

    # creator
    #
    def creator(s, pkg):
        cdebug('                WorkflowBug::creator enter')
        retval = s.__package.creator(pkg)
        cdebug('                WorkflowBug::creator leave (True)')
        return retval

    @property
    def pkg_name(s):
        return s.__package.name

    @property
    def pkg_version(s):
        return s.__package.version

    @property
    def series(s):
        return s.__package.series

    # modified
    #
    @property
    def modified(s):
        '''
        Have any of the tasks statuses been changed?
        '''
        retval = False
        for t in s.tasks_by_name:
            if s.tasks_by_name[t].modified:
                retval = True
                break
        return retval
