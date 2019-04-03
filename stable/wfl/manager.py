#!/usr/bin/env python
#

from contextlib                         import contextmanager
from datetime                           import datetime
from fcntl                              import lockf, LOCK_EX, LOCK_NB, LOCK_UN
import os
import yaml

from ktl.kernel_series                  import KernelSeries

from .log                               import center, cleave, cdebug, cinfo, cerror
from .launchpad                         import Launchpad
from .launchpad_stub                    import LaunchpadStub
from .bug                               import WorkflowBug, WorkflowBugError
from .package                           import PackageError, SeriesLookupFailure
from .snap                              import SnapError
from .bugmail                           import BugMailConfigFileMissing
import wfl.wft

# WorkflowManager
#
class WorkflowManager():
    # __init__
    #
    def __init__(s, args, test_mode=False, ks=None):
        center('WorkflowManager.__init__')
        s.test_mode = test_mode
        s.args = args
        s._lp = None
        s._task_map = {
            'kernel-sru-workflow'       : wfl.wft.Workflow,
            'upload-to-ppa-dnu'         : wfl.wft.IgnoreInvalid,
            'prepare-package'           : wfl.wft.PreparePackage,
            'prepare-package-lbm'       : wfl.wft.PreparePackage,
            'prepare-package-lrm'       : wfl.wft.PreparePackage,
            'prepare-package-meta'      : wfl.wft.PreparePackage,
            'prepare-package-ports-meta': wfl.wft.PreparePackage,
            'prepare-package-signed'    : wfl.wft.PreparePackage,
            'automated-testing'         : wfl.wft.AutomatedTesting,
            'promote-to-proposed'       : wfl.wft.PromoteToProposed,
            'verification-testing'      : wfl.wft.VerificationTesting,
            'certification-testing'     : wfl.wft.CertificationTesting,
            'regression-testing'        : wfl.wft.RegressionTesting,
            'promote-to-updates'        : wfl.wft.PromoteToUpdates,
            'promote-to-security'       : wfl.wft.PromoteToSecurity,
            'promote-to-release'        : wfl.wft.PromoteToRelease,
            'security-signoff'          : wfl.wft.SecuritySignoff,
            'snap-release-to-edge'      : wfl.wft.SnapReleaseToEdge,
            'snap-release-to-beta'      : wfl.wft.SnapReleaseToBeta,
            'snap-release-to-candidate' : wfl.wft.SnapReleaseToCandidate,
            'snap-release-to-stable'    : wfl.wft.SnapReleaseToStable,
            'snap-qa-testing'           : wfl.wft.SnapQaTesting,
            'snap-certification-testing': wfl.wft.SnapCertificationTesting,
            'snap-publish'              : wfl.wft.SnapPublish,
            'stakeholder-signoff'       : wfl.wft.StakeholderSignoff,
        }
        s.kernel_series = KernelSeries() if ks is None else ks

        WorkflowBug.sauron            = s.args.sauron
        WorkflowBug.dryrunn           = s.args.dryrun
        WorkflowBug.no_assignments    = s.args.no_assignments
        WorkflowBug.no_announcements  = s.args.no_announcements
        WorkflowBug.no_timestamps     = s.args.no_timestamps
        WorkflowBug.no_status_changes = s.args.no_status_changes
        WorkflowBug.no_phase_changes  = s.args.no_phase_changes
        WorkflowBug.local_msgqueue_port = s.args.local_msgqueue_port

        # Load up the initial status.  If we are scaning all bugs we will
        # attempt to clean out any bugs we did not know.  We should only
        # do this if the bug is present at the start of our run to prevent
        # us cleansing bugs which were newly created and shanked by other
        # instances.
        s.status_path = 'status.yaml'
        s.status_start = {}
        if os.path.exists(s.status_path):
            with open(s.status_path) as rfd:
                s.status_start = yaml.safe_load(rfd)
        s.status_wanted = {}

        # Per bug locking.
        s.lockfile = 'swm.lock'
        s.lockfd = open(s.lockfile, 'w')

        cleave('WorkflowManager.__init__')

    @contextmanager
    def lock_thing(s, what, block=True):
        mode = LOCK_EX
        if block is False:
            mode |= LOCK_NB
        lockf(s.lockfd, mode, 1, int(what))
        yield
        lockf(s.lockfd, LOCK_UN, 1, int(what))

    def status_set(s, bugid, summary):
        with s.lock_thing(2):
            status = {}
            if os.path.exists(s.status_path):
                with open(s.status_path) as rfd:
                    status = yaml.safe_load(rfd)

            if summary is not None:
                status[bugid] = summary
                s.status_wanted[bugid] = True
            else:
                if bugid in status:
                    cinfo('overall status {} closing'.format(bugid))
                    del status[bugid]
                s.status_wanted[bugid] = False

            s.status_save(status)

    def status_clean(s):
        with s.lock_thing(2):
            status = {}
            if os.path.exists(s.status_path):
                with open(s.status_path) as rfd:
                    status = yaml.safe_load(rfd)

            for bugid in dict(status):
                if (bugid in s.status_start and
                    s.status_wanted.get(bugid, False) is False
                    ):
                    cinfo('overall status {} dropping'.format(bugid))
                    del status[bugid]

            s.status_save(status)

    def status_save(s, status):
        with open(s.status_path + '.new', 'w') as rfd:
            yaml.dump(status, rfd, default_flow_style=False)
        os.rename(s.status_path + '.new', s.status_path)

    # Returns a tuple (depth, master-bug-number, bug-number) which will be used
    # to sort a list of bug numbers.  By sorting by master-bug chain length we
    # ensure we see all of the top level bugs first, then all direct children,
    # then all of their direct children and so on.  We then sort by master bug
    # number in order to group bugs sharing a master bug together.  Finally we
    # sort by the primary bug number to ensure a stable sort order in every
    # run.
    #
    # Note #1: that we are a class member function so when we are used by
    # sorted() and family we will implicitly retain access to self, and through
    # that to the status_start that contains.
    #
    # Note #2: we are forming part of the sort key from external data, we
    # lookup the master_bug number and also count the master_bug link depth in
    # the status_start data which is an associative array of information by bug
    # number.  This contains a master-bug element when such is present.
    def tracker_key(s, bug_nr):
        # If we do not know this bug at all, order it last.
        if bug_nr not in s.status_start:
            return (100, 0, bug_nr)

        # Follow the master-bug links we have recorded back up the hierachy
        # counting the number of levels.
        master_bug = bug_nr
        depth = 0
        while master_bug != '0':
            master_bug = str(s.status_start.get(master_bug, {}).get('master-bug', 0))
            depth += 1

        # Order by depth, master-bug, primary bug.
        key = (depth, str(s.status_start.get(bug_nr, {}).get('master-bug', 0)), bug_nr)
        return key

    @property
    def lp(s):
        if s._lp is None:
            if s.test_mode is True:
                s._lp = LaunchpadStub(s.args)
            else:
                s._lp = Launchpad(False)
        return s._lp

    @property
    def buglist(s):
        '''
        Return a list of all the bugs that need to be processed.
        '''
        center('WorkflowManager.buglist')
        retval = {}
        cinfo('Starting run ' + str(datetime.now()))
        if s.args.bugs:
            for bugid in s.args.bugs:
                lpbug = s.lp.default_service.get_bug(bugid)
                if lpbug.duplicate_of is not None:
                    cinfo('    LP: #%s - %s (DUPLICATE)' % (lpbug.id, lpbug.title), 'magenta')
                    s.status_set(bugid, None)
                    continue
                cinfo('    LP: #%s - %s' % (lpbug.id, lpbug.title), 'magenta')
                retval[bugid] = lpbug.title
        else:
            for project in WorkflowBug.projects_tracked:
                cinfo('project: %s' % project, 'magenta')
                search_tags            = ['kernel-release-tracking-bug', 'kernel-release-tracking-bug-live']
                search_tags_combinator = "All"
                search_status          = ["Confirmed", "In Progress", "Incomplete", "Fix Committed"] # A list of the bug statuses that we care about
                search_since           = datetime(year=2013, month=1, day=1)
                lp_project = s.lp.default_service.projects[project]
                tasks = lp_project.search_tasks(status=search_status, tags=search_tags, tags_combinator=search_tags_combinator, modified_since=search_since)

                for task in tasks:
                    bug = task.bug
                    if bug.duplicate_of is not None:
                        cinfo('    LP: #%s - %s (DUPLICATE)' % (bug.id, bug.title), 'magenta')
                        s.status_set(str(bug.id), None)
                        continue
                    cinfo('    LP: #%s - %s' % (bug.id, bug.title), 'magenta')
                    retval[str(bug.id)] = bug.title

        cleave('WorkflowManager.buglist')
        return retval

    # manage
    #
    def manage(s):
        if not s.args.bugs:
            try:
                with s.lock_thing(1, block=False):
                    s.manage_payload()
            except BlockingIOError:
                cerror('Full run already in progress.', 'red')
        else:
            s.manage_payload()

    # manage_payload
    #
    def manage_payload(s):
        '''
        This drives the overall process. It gets a list of the bugs that need to
        be worked (if not specified) and then runs through each of them.
        '''
        center('WorkflowManager.manage_payload')
        try:
            # Run the list based on the master chain depth, shortest first.
            for bugid in sorted(s.buglist, key=s.tracker_key):
                with s.lock_thing(bugid):
                    s.crank(bugid)

            if not s.args.bugs:
                s.status_clean()

        except BugMailConfigFileMissing as e:
            print(e.message)

        # Handle the user presses <ctrl-C>.
        #
        except KeyboardInterrupt:
            pass

        cleave('WorkflowManager.manage_payload')
        return 0

    # crank
    #
    def crank(s, bugid):
        '''
        For the specified bug, continue to process all of the bugs tasks until none
        of them are changed from the previous processing.
        '''
        center('WorkflowManager.crank')

        s.printlink = '%s : (%s)' % (bugid, s.lp.bug_url(bugid))
        cinfo('')
        cinfo('Processing: %s' % s.printlink, 'cyan')

        # If the bug was modified (task status changed) on that crank of the bug then
        # crank it again.
        #
        modified = True
        try:
            bug = WorkflowBug(s.lp.default_service, bugid, ks=s.kernel_series)
            bug.reason_reset_all()
            while modified:
                try:
                    cinfo('        ---------------------------------------  c r a n k  ---------------------------------------', 'green')
                    modified = s.process_bug_tasks(bug)

                # XXX: should be a VariantError or something.
                except (PackageError, SnapError) as e:
                    for l in e.message:
                        cinfo(l, 'red')
            bug.save()

            # Update the global status for this bug.
            s.status_set(bugid, bug.status_summary())

        except (SeriesLookupFailure, WorkflowBugError) as e:
            modified = False
            for l in e.args:
                cerror(e.__class__.__name__ + ': ' + l)

        cleave('WorkflowManager.crank')

    # process_bug_tasks
    #
    def process_bug_tasks(s, bug):
        '''
        Go through every workflow task and perform the associated actions
        based on the current state (status) of that task.
        '''
        center('WorkflowManager.process_bug_tasks')

        # Determine this bugs project.
        #
        for task in bug.lpbug.tasks:
            task_name = task.bug_target_name
            if task_name in WorkflowBug.projects_tracked:
                s.projectname = task_name
                break

        retval = False
        for workflow_task_name in sorted(bug.tasks_by_name):
            task = bug.tasks_by_name[workflow_task_name]
            cinfo('')
            cinfo("        %-25s  %15s  %10s  %s (%s)" % (task.name, task.status, task.importance, task.assignee, workflow_task_name), 'magenta')

            therest = task_name[len(s.projectname) + 1:].strip()
            task_name = therest

            if workflow_task_name not in s._task_map:
                task.reason = 'unknown workflow task'
                cinfo('        Unknown workflow task')
                continue

            try:
                cls = s._task_map[workflow_task_name](s.lp, task, bug)
                if cls.evaluate_status(task.status) and not s.args.dryrun:
                    retval = True
                    cinfo('        True')
            except (PackageError, WorkflowBugError) as e:
                for l in e.args:
                    cerror(e.__class__.__name__ + ': ' + l)
                task.reason = 'Stalled -- ' + e.__class__.__name__ + ': ' + e.args[0]

            # Insert a default reason for anything which is active and did not say why.
            if task.reason == '' and workflow_task_name not in WorkflowBug.projects_tracked:
                if task.status == 'Confirmed':
                    task.reason = 'Pending -- Ready'
                elif task.status in ('In Progress', 'Fix Committed'):
                    task.reason = 'Ongoing -- status ' + task.status
                elif task.status == 'Incomplete':
                    task.reason = 'Stalled -- FAILED'

        cleave('WorkflowManager.process_bug_tasks')
        return retval

# vi:set ts=4 sw=4 expandtab:
