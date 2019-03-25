#!/usr/bin/env python
#
from datetime                           import datetime
import yaml
import re
from lib.utils                          import date_to_string
from .log                               import cdebug, center, cleave, cinfo
from .package                           import Package, PackageError
from ktl.shanky                         import send_to_shankbot
from .errors                            import ShankError
from .deltatime                         import DeltaTime
from .task                              import WorkflowBugTask
from ktl.kernel_series                  import KernelSeries
from ktl.sru_cycle                      import SruCycle
from .swm_config                        import SwmConfig
from .git_tag                           import GitTag


# WorkflowBugError
#
class WorkflowBugError(ShankError):
    '''
    Thrown when some goes wrong with the WorkflowBug (e.g. when trying to
    process a non-existing bug).
    '''
    pass


# WorkflowBug
#
class WorkflowBug():
    '''
    A helper class. Tries to encapsulate most of the common methods for working with the
    workflow bug.
    '''
    projects_tracked  = ['kernel-development-workflow', 'kernel-sru-workflow']
    dryrun            = False
    no_assignments    = False
    no_announcements  = False
    sauron            = False
    no_timestamps     = False
    no_status_changes = False
    no_phase_changes  = False
    local_msgqueue_port = None

    # __init__
    #
    def __init__(s, lp, bugid, ks=None):
        '''
        When instantiated the bug's title is processed to find out information about the
        related package. This information is cached.
        '''
        s.lp = lp
        try:
            s.lpbug = s.lp.get_bug(bugid)
        except KeyError:
            s.is_valid = False
            cdebug('Failed to get bug #%s' % bugid, 'red')
            raise WorkflowBugError('Invalid bug number %s' % bugid)

        # Pass along any "global" settings to the WorkflowBugTask.
        #
        WorkflowBugTask.dryrun = WorkflowBug.dryrun
        WorkflowBugTask.no_status_changes = WorkflowBug.no_status_changes
        WorkflowBugTask.no_assignments = WorkflowBug.no_assignments
        WorkflowBugTask.no_timestamps = WorkflowBug.no_timestamps

        s.kernel_series = KernelSeries() if ks is None else ks

        s.title = s.lpbug.title
        s._tags = None
        s.bprops = s.load_bug_properties()
        s.overall_reason = None
        s.is_development_series = False
        s._master_bug = False
        s._sru_spin = False

        # If a bug isn't to be processed, detect this as early as possible.
        #
        (s.is_workflow, s.is_valid) = s.check_is_valid(s.lpbug)
        s.properties = s.lpbug.properties

        # Try and decode the title for package/versions/source etc.
        if not s.__title_decode():
            raise WorkflowBugError('Package not identified from title')
        if s.series is None:
            raise WorkflowBugError('Series not identified from tags')
        if s.source is None:
            raise WorkflowBugError('Source not found in kernel-series')
        s.is_development_series = s.source.series.development
        s.is_development = s.source.development

        try:
            s.debs = Package(s.lp, s, ks=s.kernel_series)

            cinfo('                      title: "%s"' % s.title, 'blue')
            cinfo('                   is_valid: %s' % s.is_valid, 'blue')
            cinfo('                is_workflow: %s' % s.is_workflow, 'blue')
            cinfo('                       name: "%s"' % s.name, 'blue')
            cinfo('                    version: "%s"' % s.version, 'blue')
            cinfo('                     series: "%s"' % s.series, 'blue')
            cinfo('      is development series: %s' % s.is_development_series, 'blue')
            for d in s.debs.pkgs:
                cinfo('                        dep: "%s"' % d, 'blue')

            if s.is_derivative_package:
                cinfo('                 derivative: yes (%s)' % s.master_bug_id, 'blue')
            else:
                cinfo('                 derivative: no', 'blue')
            cinfo('')

            cinfo('    Targeted Project:', 'cyan')
            cinfo('        %s' % s.workflow_project, 'magenta')
            cinfo('')
            props_dump = yaml.safe_dump(s.bprops, default_flow_style=False).strip().split('\n')
            if len(props_dump) > 0:
                cinfo('    SWM Properties:', 'cyan')
                for prop in props_dump:
                    cinfo('        {}'.format(prop), 'magenta')

        except PackageError as e:
            # Report why we are not valid.
            for l in e.args:
                cinfo(l, 'red')
            s.overall_reason = e.args[0]
            s.is_valid = False
            s.debs = None

        s.tasks_by_name = s._create_tasks_by_name_mapping()

    def __title_decode(s):
        txt = s.title

        matched = False
        #                              .- package name (group(1))
        #                             /           .- kernel version (group(2))
        #                            /           /          .- version/abi separator (group(3))
        #                           /           /          /
        ver_rc     = re.compile("(\S+): (\d+\.\d+\.\d+)([-\.])(\d+)\.(\d+)([~a-z\d.]*)")
        #                                                       /      /       /
        #                                                      /      /       .- backport extra (m.group(6))
        #                                                     /      .- upload number (m.group(5))
        #                                                    .- abi (group(4))

        #info('     Extract package info\n')
        m = ver_rc.search(txt)
        if m is not None:
            matched = True
            cdebug('package: %s' % m.group(1))
            cdebug('version: %s%s%s.%s%s' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
            cdebug(' kernel: %s' % m.group(2))
            cdebug('    abi: %s' % m.group(4))

            s.name = m.group(1)
            s.version = '%s%s%s.%s%s' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6))
            s.kernel = m.group(2)
            s.abi = m.group(4)

        # Try just a package match.
        if not matched:
            #                            .- package name (group(1))
            #                           /
            pkg_rc     = re.compile("(\S+):")
            m = pkg_rc.search(txt)
            if m is not None:
                matched = True
                cdebug('package: %s' % m.group(1))
                cdebug('version: INVALID')

                s.name = m.group(1)
                s.version = None

                s.is_valid = False

        # Work out what series this package is published in...
        series_tag_entry = None
        for tag in s.lpbug.tags:
            series_tag_entry = s.kernel_series.lookup_series(codename=tag)
            if series_tag_entry:
                break

        if not matched:
            cwarn(' ** None of the regular expressions matched the title (%s)' % txt)
            return False

        # Set the series attribute
        cdebug(' series: %s' % series_tag_entry.codename)
        s.series = series_tag_entry.codename

        # Lookup the KernelSeries package and attach that.
        source = None
        if series_tag_entry:
            source = series_tag_entry.lookup_source(s.name)
        s.source = source

        return True

    # _remove_live_tag
    #
    def _remove_live_tag(s):
        # If this task is now closed, also drop the live tag.
        if s.is_valid and s.tasks_by_name[s.workflow_project].status == 'Fix Released':
            if s._dryrun:
                cinfo('    dryrun - workflow task is closed -- removing -live tag', 'red')
            else:
                cinfo('    action - workflow task is closed -- removing -live tag', 'red')

                # Drop the "-live" tag as this one is moving dead.
                if 'kernel-release-tracking-bug-live' in s.lpbug.tags:
                    s.lpbug.tags.remove('kernel-release-tracking-bug-live')

    # save
    #
    def save(s):
        s.save_bug_properties()
        s._remove_live_tag()

    @property
    def _dryrun(s):
        return WorkflowBug.dryrun

    @property
    def _no_announcements(s):
        return WorkflowBug.no_announcements

    @property
    def _sauron(s):
        return WorkflowBug.sauron

    # master_bug_property_name
    #
    @property
    def master_bug_property_name(s):
        for prop_name in (
            'master-bug',
            'kernel-stable-master-bug',
            'kernel-master-bug',
            ):
            if prop_name in s.bprops:
                return prop_name
        return 'master-bug'

    # is_derivative_package
    #
    @property
    def is_derivative_package(s):
        return s.master_bug_property_name in s.bprops

    # master_bug
    #
    @property
    def master_bug_id(s):
        '''
        '''
        return s.bprops[s.master_bug_property_name]

    # master_bug
    #
    @property
    def master_bug(s):
        '''
        Find the 'master' bug of which this is a derivative and return that bug.
        '''
        if s._master_bug is False:
            if s.is_derivative_package:
                try:
                    s._master_bug = WorkflowBug(s.lp, s.master_bug_id, ks=s.kernel_series)
                except:
                    raise WorkflowBugError("invalid master bug link")
            else:
                s._master_bug = None
        return s._master_bug

    # load_bug_properties
    #
    def load_bug_properties(s):
        center(s.__class__.__name__ + '.load_bug_properties')
        retval = {}
        started = False
        buf = ''

        description = s.lpbug.description
        for l in description.split('\n'):
            if started:
                buf += l + '\n'
            if l.startswith('-- swm properties --'):
                started = True

        if started and buf is not None:
            # Launchpad will convert leading spaces into utf-8 non-breaking spaces
            # when you manually edit the description in the web interface.
            buf = buf.replace('\xa0', ' ')
            try:
                retval = yaml.safe_load(buf)
                if retval is None:
                    retval = {}
            except:
                cinfo('Exception thrown trying to load bug properties', 'red')
                retval = {}

        cleave(s.__class__.__name__ + '.load_bug_properties')
        return retval

    # save_bug_properties
    #
    def save_bug_properties(s):
        center(s.__class__.__name__ + '.save_bug_properties')

        retval = None
        newd = ''

        if len(s.bprops) > 0:
            new_props = yaml.safe_dump(s.bprops, default_flow_style=False).strip()

            description = s.lpbug.description
            for l in description.split('\n'):
                if l.startswith('-- swm properties --'):
                    break
                newd += l + '\n'

            newd += '-- swm properties --\n'
            newd += new_props

            if s.lpbug.description != newd:
                if s._dryrun:
                    cinfo('    dryrun - updating SWM properties', 'red')
                else:
                    cinfo('    action - updating SWM properties', 'red')
                    s.lpbug.description = newd
            else:
                cinfo('    noop - SWM properties unchanged', 'yellow')
            for line in new_props.split('\n'):
                cinfo('        ' + line, 'magenta')

        cleave(s.__class__.__name__ + '.save_bug_properties')
        return retval

    # reason_reset_all
    #
    def reason_reset_all(s):
        '''
        Reset all existing reasons for this bug.
        '''
        if 'reason' in s.bprops:
            del s.bprops['reason']

    def status_summary(s):
        '''
        Return the current reason set for this bug.
        '''
        status = s.bprops

        # Add the current tasks status information.
        task = status.setdefault('task', {})
        for taskname in s.tasks_by_name:
            task[taskname] = {
                'status': s.tasks_by_name[taskname].status,
                }
            # XXX: ownership of tasks should be more obvious, but this is
            # only needed while we have combo bugs in reality.
            if (taskname.startswith('snap-') and s.snap is not None and
                s.snap.name != s.name):
                task[taskname]['target'] = s.snap.name

        if s.overall_reason is not None:
            status.setdefault('reason', {})['overall'] = s.overall_reason

        try:
            status['cycle'] = s.sru_cycle
            status['series'] = s.series
            status['package'] = s.name
            if s.version is not None:
                status['version'] = s.version
        except:
            pass

        # Do not expose this API error.
        master_bug = s.master_bug_property_name
        if master_bug != 'master-bug' and master_bug in status:
            status['master-bug'] = status[master_bug]
            del status[master_bug]

        return status

    # check_is_valid
    #
    def check_is_valid(s, bug):
        '''
        Determine if this bug is one that we want to be processing. Bugs that we
        should not be processing are ones that are not currently "In Progress".
        '''
        workflow = False
        valid = False
        for t in s.lpbug.tasks:
            task_name       = t.bug_target_name

            if task_name in WorkflowBug.projects_tracked:
                workflow = True
                s.workflow_project = task_name
                if t.status == 'In Progress':
                    valid = True
                    continue
                else:
                    if s._sauron:
                        continue
                    cdebug('        Not processing this bug because master task state is set to %s' % (t.status))
                    cdebug('        Quitting this bug')

        return (workflow, valid)

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

            if task_name.startswith(s.workflow_project):
                if '/' in task_name:
                    task_name = task_name[len(s.workflow_project) + 1:].strip()
                tasks_by_name[task_name] = WorkflowBugTask(t, task_name, s.debs, s)
            else:
                cinfo('        %-25s' % (task_name), 'magenta')
                cinfo('            Action: Skipping non-workflow task', 'magenta')

        return tasks_by_name

    # valid_package
    #
    def valid_package(s, pkg):
        center(s.__class__.__name__ + '.valid_package')

        # XXX: this is not deb related.
        retval = pkg in s.debs.pkgs

        cleave(s.__class__.__name__ + '.valid_package')
        return retval

    def published_tag(s, pkg):
        published = True

        package_package = None
        for package in s.source.packages:
            if (package.type == pkg or (
                package.type is None and pkg == 'main')
                ):
                package_package = package
                break
        if package_package is not None:
            version = s.debs.upload_version(pkg)
            if version is None:
                published = False
            else:
                git_tag = GitTag(package_package, version)
                if git_tag.verifiable and not git_tag.present:
                    published = False

        return published

    # all_dependent_packages_published_tag
    #
    @property
    def all_dependent_packages_published_tag(s):
        '''
        For the kernel package associated with this bug, the status of whether or
        not all of the dependent packages (meta, signed, lbm, etc.) have published
        tags is returned.
        '''
        retval = True

        bi = s.debs.build_info
        for pkg in bi:
            if not s.published_tag(pkg):
                cinfo('        %s missing tag.' % (pkg), 'yellow')
                retval = False
                break

        return retval

    @property
    def swm_config(s):
        '''
        Flag information from kernel-series.
        '''
        return SwmConfig(s.source.swm_data)

    @property
    def kernel_version(s):
        '''
        Decoded from the version string in the title, the kernel version is returned.
        This is just the kernel version without the ABI or upload number.
        '''
        return s.kernel

    @property
    def tags(s):
        '''
        Returns a list of the tags on the bug.
        '''
        if s._tags is None:
            s._tags = []
            for t in s.lpbug.tags:
                s._tags.append(t)
        return s._tags

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
            if s.tasks_by_name[taskname].status != "Invalid":
                return True
        return False

    # phase
    #
    @property
    def phase(s):
        return s.bprops.get('phase')

    @phase.setter
    def phase(s, phasetext):
        """
        Add the phase we're entering as a 'property', along with a time stamp.
        """
        center(s.__class__.__name__ + '.set_phase')

        # We have to check here to see whether the same status is already set,
        # or we will overwrite the timestamp needlessly
        if s.phase == phasetext:
            # we already have this one
            cdebug('Not overwriting identical phase property (%s)' % phasetext)
            cleave(s.__class__.__name__ + '.set_phase')
            return
        # Handle dryrun mode
        if s._dryrun or WorkflowBug.no_phase_changes:
            cinfo('    dryrun - Changing bug phase to <%s>' % phasetext, 'red')
            cleave(s.__class__.__name__ + '.set_phase')
            return

        # Add phase and time stamp
        cdebug('Changing bug phase to <%s>' % phasetext)
        now = datetime.utcnow()
        now.replace(tzinfo=None)
        tstamp = date_to_string(now)

        s.bprops['phase'] = phasetext
        s.bprops['phase-changed'] = tstamp
        cleave(s.__class__.__name__ + '.set_phase')

    # has_new_abi
    #
    def has_new_abi(s):
        tasks_abi = ['prepare-package-lbm', 'prepare-package-meta', 'prepare-package-ports-meta']
        retval = False
        for taskname in tasks_abi:
            if taskname in s.tasks_by_name:
                if s.tasks_by_name[taskname].status != "Invalid":
                    return True
        return retval

    # sru_spin
    #
    @property
    def sru_spin(s):
        if s._sru_spin is False:
            spin = None
            for t in s.tags:
                if t.startswith('kernel-sru-cycle-'):
                    spin = t.replace('kernel-sru-cycle-', '')
            if spin is not None:
                spin = SruCycle().lookup_spin(spin, allow_missing=True)
            s._sru_spin = spin

        return s._sru_spin

    # sru_cycle
    #
    @property
    def sru_cycle(s):
        spin = s.sru_spin
        if spin is not None:
            spin = spin.name
        else:
            spin = '1962.11.02-00'
        return spin

    def send_email(s, subject, body, to):
        from .bugmail import BugMail
        BugMail.load_config('email.yaml')
        BugMail.to_address = to
        BugMail.send(subject, body)

    # send_upload_announcement
    #
    def send_upload_announcement(s, pocket):
        """
        Send email with upload announcement
        """
        center(s.__class__.__name__ + '.send_upload_announcement')

        # -------------------------------------------------------------------------------------------------------------
        # Email Notice
        # -------------------------------------------------------------------------------------------------------------

        cdebug('Sending upload announcement')

        to_address  = "kernel-team@lists.ubuntu.com"
        to_address += ", ubuntu-installer@lists.ubuntu.com"

        abi_bump = s.has_new_abi()

        subject = "[" + s.series + "] " + s.name + " " + s.version + " uploaded"
        if abi_bump:
            subject += " (ABI bump)"

        if s._dryrun or s._no_announcements:
            cinfo('    dryrun - Sending announcement to shankbot', 'red')
        else:
            send_to_shankbot(subject + '\n')

        body  = "A new " + s.series + " kernel has been uploaded into "
        body += pocket + ". "
        if abi_bump:
            body += "Note the ABI bump. "
        body += "\nThe full changelog about all bug fixes contained in this "
        body += "upload can be found at:\n\n"
        body += "https://launchpad.net/ubuntu/" + s.series + "/+source/"
        body += s.name + "/" + s.version + "\n\n"
        body += "-- \nThis message was created by an automated script,"
        body += " maintained by the\nUbuntu Kernel Team."

        if s._dryrun or s._no_announcements:
            cinfo('    dryrun - Sending email announcement', 'red')
        else:
            s.send_email(subject, body, to_address)

        cleave(s.__class__.__name__ + '.send_upload_announcement')
        return

    def add_comment(s, subject, body):
        """
        Add comment to tracking bug
        """
        center(s.__class__.__name__ + '.add_comment')
        if s._dryrun:
            cinfo('    dryrun - Adding comment to tracking bug', 'red')
            cdebug('')
            cdebug('subject: %s' % (subject))
            for l in body.split('\n'):
                cdebug('comment: %s' % (l))
            cdebug('')
        else:
            cdebug('Adding comment to tracking bug')
            s.lpbug.add_comment(body, subject)
        cleave(s.__class__.__name__ + '.add_comment')

    # timestamp
    #
    def timestamp(s, keyvalue):
        '''
        Add the supplied key with a timestamp. We do not replace existing keys
        '''
        center(s.__class__.__name__ + '.timestamp')

        # if s._dryrun or s.no_timestamps:
        #     cinfo('    dryrun - Adding timestamp for \'%s\'' % keyvalue, 'red')
        # else:
        #     if keyvalue not in s.bprops:
        #         cinfo('    Adding timestamp for \'%s\'' % keyvalue)
        #         now = datetime.utcnow().replace(tzinfo=None)
        #         s.bprops[keyvalue] = date_to_string(now)

        cleave(s.__class__.__name__ + '.timestamp')

    # has_package
    #
    @property
    def has_package(s):
        return s.debs is not None

    # is_proposed_only
    #
    @property
    def is_proposed_only(s):
        return False

    # workflow_duplicates
    #
    @property
    def workflow_duplicates(s):
        retval = []

        # XXX: XXX: lpltk does NOT let me get to the duplicate list!?!?!?!
        duplicates = s.lpbug.lpbug.duplicates
        #duplicates = [ s.lp.get_bug('1703532') ]
        for dup in duplicates:
            dup_wb = WorkflowBug(s.lp, dup.id, ks=s.kernel_series)
            if not dup_wb.is_workflow or not dup_wb.is_valid:
                continue
            retval.append(dup_wb)

        return retval

# vi:set ts=4 sw=4 expandtab:
