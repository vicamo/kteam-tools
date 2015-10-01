#!/usr/bin/env python
#
from logging                            import info, debug, error, warning, basicConfig, INFO, DEBUG, WARNING

from sb.log                             import cinfo, cdebug
from sb.package                         import Package, PackageError
from sb.errors                          import ShankError

# PackageError
#
class WorkflowBugError(ShankError):
    '''
    Thrown when some goes wrong with the WorkflowBug (e.g. when trying to
    process a non-existing bug).
    '''
    def __init__(s, emsg):
        super(ShankError, s).__init__(emsg)

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
        '''
        Property: Gets the assignee for the task.
        '''
        if s.__assignee is None:
            assignee = s.lp_task.assignee
            if assignee is None:
                s.__assignee = '*Unassigned'
            else:
                s.__assignee = assignee.display_name

    @assignee.setter
    def assignee(s, val):
        '''
        Property: Sets the assignee for the task.
        '''
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
    '''
    A helper class. Tries to encapsulate most of the common methods for working with the
    workflow bug.
    '''
    # __init__
    #
    def __init__(s, lp, projects, bugid, sauron=False, dryrun=False):
        '''
        When instantiated the bug's title is processed to find out information about the
        related package. This information is cached.
        '''
        s.lp = lp
        try:
            s.lpbug = s.lp.get_bug(bugid)
        except KeyError:
            s.is_valid = False
            cinfo('Failed to get bug #%s' % bugid, 'red')
            raise WorkflowBugError('Invalid bug number %s' % bugid)

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

                s.tasks_by_name = s._create_tasks_by_name_mapping()
        except PackageError:
            s.is_valid = False

    # check_is_valid
    #
    def check_is_valid(s, bug):
        '''
        Determine if this bug is one that we wan't to be processing. Bugs that we
        should not be processing are ones that are not currently "In Progress".
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

    # _create_tasks_by_name_mapping
    #
    def _create_tasks_by_name_mapping(s):
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
        '''
        For the package specified, the status of whether or not it is fully built
        is returned.
        '''
        retval = s.__package.fully_built(pkg)
        return retval

    # all_dependent_packages_fully_built
    #
    def all_dependent_packages_fully_built(s):
        '''
        For the kernel package associated with this bug, the status of whether or
        not all lf the dependent packages (meta, signed, lbm, etc.) are fully built
        is returned.
        '''
        retval = s.__package.all_dependent_packages_fully_built()
        return retval

    # creator
    #
    def creator(s, pkg):
        '''
        Returns the name of the person that created the source package.
        '''
        retval = s.__package.creator(pkg)
        return retval

    @property
    def pkg_name(s):
        '''
        Property: The name of the package associated with this bug.
        '''
        return s.__package.name

    @property
    def pkg_version(s):
        '''
        Returns the full version as specified in the bug title.
        '''
        return s.__package.version

    @property
    def series(s):
        '''
        Decoded from the kernel version in the bug title, the series name associated
        with that kernel version is returned.
        '''
        return s.__package.series

    @property
    def abi(s):
        '''
        The abi number from the full version in the bug title is returned.
        '''
        return s.__package.abi

    @property
    def kernel_version(s):
        '''
        Decoded from the version string in the title, the kernel version is returned.
        This is just the kernel version without the ABI or upload number.
        '''
        return s.__package.kernel

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

    # _has_prep_task
    #
    def _has_prep_task(s, taskname):
        if taskname in s.tasks_by_name:
            if s.tasks_by_name[taskname].status == "Fix Released":
                return True
        return False

    # relevant_packages_list
    #
    def relevant_packages_list(s):
        '''
        For every tracking bug there are 'prepare-package-*' tasks. Not every tracking bug has all the
        same 'prepare-pacakge-*' tasks. Also, there is a specific package associated with each of the
        'prepare-package-*' tasks.

        This method builds a list of the packages that are relevant to this particular bug.
        '''
        cdebug('                WorkflowBug::relevant_packages_list enter')
        name_meta       = 'linux-meta'
        name_ports_meta = 'linux-ports-meta'
        name_signed     = 'linux-signed'
        name_split = s.pkg_name.split('-', 1)
        if len(name_split) > 1:
            name_meta       = '%s-meta-%s'       % (name_split[0], name_split[1])
            name_ports_meta = '%s-ports-meta-%s' % (name_split[0], name_split[1])
            name_signed     = '%s-signed-%s'     % (name_split[0], name_split[1])

        name_map = {
                'prepare-package-lbm'        : 'linux-backports-modules',
                'prepare-package-meta'       : name_meta,
                'prepare-package-ports-meta' : name_ports_meta,
                'prepare-package-signed'     : name_signed
            }
        ver_split = s.pkg_version.split('-')
        main_version = ver_split[0]
        package_list = [ s.pkg_name ]
        for name in iter(name_map):
            if s._has_prep_task(name):
                if 'lbm' in name:
                    package_list.append('%s-%s' % (name_map[name], main_version))
                else:
                    package_list.append(name_map[name])

        for p in package_list:
            cdebug('                    pkg: %s' % p)
        cdebug('                WorkflowBug::relevant_packages_list leave')
        return package_list

