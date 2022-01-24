#!/usr/bin/env python
#

from contextlib                         import contextmanager
from copy                               import copy
from datetime                           import datetime
from fcntl                              import lockf, LOCK_EX, LOCK_NB, LOCK_UN
import json
import os
import yaml

from lazr.restfulclient.errors          import PreconditionFailed

from ktl.kernel_series                  import KernelSeries
from ktl.sru_cycle                      import SruCycle

from .errors                            import WorkflowCrankError, WorkflowCorruptError
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
    def __init__(s, args, test_mode=False, ks=None, sru_cycle=None):
        center('WorkflowManager.__init__')
        s.test_mode = test_mode
        s.args = args
        s._lp = None
        s._task_map = {
            'kernel-sru-workflow'       : wfl.wft.Workflow,
            'upload-to-ppa-dnu'         : wfl.wft.IgnoreInvalid,
            'prepare-package'           : wfl.wft.PreparePackage,
            'prepare-package-lbm'       : wfl.wft.PreparePackage,
            'prepare-package-lrg'       : wfl.wft.PreparePackage,
            'prepare-package-lrm'       : wfl.wft.PreparePackage,
            'prepare-package-lrs'       : wfl.wft.PreparePackage,
            'prepare-package-meta'      : wfl.wft.PreparePackage,
            'prepare-package-ports-meta': wfl.wft.PreparePackage,
            'prepare-package-signed'    : wfl.wft.PreparePackage,
            ':prepare-packages'         : wfl.wft.SynPreparePackages,
            ':promote-to-as-proposed'   : wfl.wft.SynPromoteToAsProposed,
            'automated-testing'         : wfl.wft.AutomatedTesting,
            'promote-to-proposed'       : wfl.wft.PromoteToProposed,
            'promote-signing-to-proposed': wfl.wft.PromoteSigningToProposed,
            'verification-testing'      : wfl.wft.VerificationTesting,
            'certification-testing'     : wfl.wft.CertificationTesting,
            'regression-testing'        : wfl.wft.RegressionTesting,
            'boot-testing'              : wfl.wft.BootTesting,
            'promote-to-updates'        : wfl.wft.PromoteToUpdates,
            'promote-to-security'       : wfl.wft.PromoteToSecurity,
            'promote-to-release'        : wfl.wft.PromoteToRelease,
            'security-signoff'          : wfl.wft.SecuritySignoff,
            'snap-prepare'              : wfl.wft.SnapPrepare,
            'snap-release-to-edge'      : wfl.wft.SnapReleaseToEdge,
            'snap-release-to-beta'      : wfl.wft.SnapReleaseToBeta,
            'snap-release-to-candidate' : wfl.wft.SnapReleaseToCandidate,
            'snap-release-to-stable'    : wfl.wft.SnapReleaseToStable,
            'snap-qa-testing'           : wfl.wft.SnapQaTesting,
            'snap-certification-testing': wfl.wft.SnapCertificationTesting,
            'snap-publish'              : wfl.wft.SnapPublish,
            'sru-review'                : wfl.wft.SruReview,
            'stakeholder-signoff'       : wfl.wft.StakeholderSignoff,
            'kernel-signoff'            : wfl.wft.StakeholderSignoff,
        }
        s.kernel_series = KernelSeries() if ks is None else ks
        s.sru_cycle = SruCycle() if sru_cycle is None else sru_cycle

        WorkflowBug.sauron            = s.args.sauron
        WorkflowBug.dryrunn           = s.args.dryrun
        WorkflowBug.no_assignments    = s.args.no_assignments
        WorkflowBug.no_announcements  = s.args.no_announcements
        WorkflowBug.no_timestamps     = s.args.no_timestamps
        WorkflowBug.no_status_changes = s.args.no_status_changes
        WorkflowBug.no_phase_changes  = s.args.no_phase_changes
        WorkflowBug.local_msgqueue_port = s.args.local_msgqueue_port

        # Per bug locking.
        s.lockfile = 'swm.lock'
        s.lockfd = open(s.lockfile, 'w')

        # Load up the initial status.  If we are scaning all bugs we will
        # attempt to clean out any bugs we did not know.  We should only
        # do this if the bug is present at the start of our run to prevent
        # us cleansing bugs which were newly created and shanked by other
        # instances.
        s.status_path = 'status.yaml'
        s.status_altpath = 'status.json'
        s.status_validator = None
        s.Status_current = None
        with s.lock_status():
            s.status_start = s.status_load()
        s.status_wanted = {}

        cleave('WorkflowManager.__init__')

    @contextmanager
    def lock_bug(s, what, block=True):
        mode = LOCK_EX
        if block is False:
            mode |= LOCK_NB
        lockf(s.lockfd, mode, 1, int(what))
        yield
        lockf(s.lockfd, LOCK_UN, 1, int(what))

    @contextmanager
    def single_thread(s):
        with s.lock_bug(1, block=False):
            yield

    @contextmanager
    def lock_status(s):
        with s.lock_bug(2):
            yield

    @contextmanager
    def single_dependants_only(s):
        with s.lock_bug(3, block=False):
            yield

    def status_get(s, bugid, summary=False, modified=None):
        with s.lock_status():
            status = s.status_load()

        return status.get(bugid, {})

    def status_set(s, bugid, summary=False, update=False, modified=None):
        with s.lock_status():
            status = s.status_load()
            # If we supply no summary assume we want it unchanged.
            if summary is False:
                summary = status.get(bugid)
            if update is not False:
                if summary is None:
                    summary = {}
                summary.update(update)
            if summary is not None:
                # Pull forward persistent swm related state.
                manager = summary['manager'] = status.get(bugid, {}).get('manager', {})

                # Update the scanned/modified times.
                if modified is not None:
                    now = datetime.utcnow()
                    manager['time-scanned'] = copy(now)
                    if modified is True or 'time-modified' not in manager:
                        manager['time-modified'] = copy(now)

                status[bugid] = summary
                s.status_wanted[bugid] = True
            else:
                if bugid in status:
                    cinfo('overall status {} closing'.format(bugid))
                    del status[bugid]
                s.status_wanted[bugid] = False

            s.status_save(status)

    def status_load(s):
        status = {}
        if os.path.exists(s.status_path):
            with open(s.status_path) as rfd:
                stat = os.stat(rfd.fileno())
                validator = (stat.st_ino, stat.st_mtime)
                cinfo("VALIDATOR: {} {}".format(s.status_validator, validator))
                if validator != s.status_validator:
                    data = yaml.safe_load(rfd)
                    s.status_current = data.get('trackers', data)
                    s.status_validator = validator
            status = s.status_current

        return status

    def json_object_encode(self, obj):
        if isinstance(obj, datetime):
            return { '_isoformat': obj.isoformat() }
        raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))

    def status_save(s, status):
        # Use a top-level trackers collection to allow us to extend with
        # non-tracker information later.
        data = {'trackers': status}

        with open(s.status_path + '.new', 'w') as wfd:
            yaml.dump(data, wfd, default_flow_style=False)
        os.rename(s.status_path + '.new', s.status_path)

        with open(s.status_altpath + '.new', 'w') as wfd:
            json.dump(data, fp=wfd, default=s.json_object_encode, separators=(',', ':'))
        os.rename(s.status_altpath + '.new', s.status_altpath)

        # We are writing the file, update our cache.
        stat = os.stat(s.status_path)
        validator = (stat.st_ino, stat.st_mtime)
        s.status_current = status
        s.status_validator = (stat.st_ino, stat.st_mtime)

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

    def live_children(s, bug_nr):
        result = []
        with s.lock_status():
            status = s.status_load()

        for child_nr, child_data in status.items():
            master_bug = str(child_data.get('master-bug', 0))
            if master_bug != bug_nr:
                continue
            series = child_data.get('series', 'unknown')
            source = child_data.get('source', 'unknown')
            target = child_data.get('target', 'unknown')
            result.append((series, source, target, child_nr, child_data))

        return result

    def cycle_key(s, entry):
        cycle = entry[1].get('cycle', '-')
        if cycle != '-':
            cycle_bits = cycle.split('-')
            try:
                cycle_spin = int(cycle_bits[-1])
            except ValueError:
                cycle_spin = 0
            cycle_bits[-1] = '{:03}'.format(cycle_spin)
            cycle = '-'.join(cycle_bits)
        return cycle

    def live_trackers_for_target(s, series, source, target):
        result = []
        with s.lock_status():
            status = s.status_load()

        for tracker_nr, tracker_data in status.items():
            t_series = tracker_data.get('series', 'unknown')
            t_source = tracker_data.get('source', 'unknown')
            t_target = tracker_data.get('target', 'unknown')
            t_phase = tracker_data.get('phase', 'unknown')

            if (series == t_series and
                source == t_source and
                target == t_target and
                t_phase != 'Complete'):
                    result.append((tracker_nr, tracker_data))

        return sorted(result, key=s.cycle_key)

    def live_dependants_rescan(s):
        result = []
        with s.lock_status():
            status = s.status_load()

        for child_nr, child_data in status.items():
            rescan = False
            child_manager = child_data['manager']
            scanned = child_manager.get('time-scanned')

            # If a bug has been marked needing a scan, scan it.
            if scanned is None:
                cinfo('    LP: #{} marked for rescan/fix -- triggering'.format(child_nr), 'magenta')
                rescan = True

            if not rescan:
                # This tracker has no parent, skip it.
                parent_nr = str(child_data.get('master-bug'))
                if parent_nr is None:
                    continue

                parent_data = status.get(parent_nr)
                if parent_data is not None:
                    parent_manager = parent_data['manager']
                    modified = parent_manager.get('time-modified')

                    # If our scanned time is before the modified time then we need
                    # to be rescanned.
                    if scanned < modified:
                        cinfo('    LP: #{} parent LP: #{} modified since scanned -- triggering ({}, {})'.format(child_nr, parent_nr, modified, scanned, scanned is None or modified > scanned), 'magenta')
                        rescan = True

            if rescan:
                result.append(child_nr)

        return result

    def live_duplicates_mark(s, old, new):
        with s.lock_status():
            status = s.status_load()
            modified = False
            for child_nr, child_data in status.items():
                # This tracker has no parent, skip it.
                parent_nr = str(child_data.get('master-bug'))
                if parent_nr is None:
                    continue
                # Unrelated to the duplication in process.
                if parent_nr != old:
                    continue

                # Ignore snap-debs variants as those should remain tightly
                # coupled with their parent.
                child_variant = child_data.get('variant')
                if child_variant == 'snap-debs':
                    continue

                # Our parent is being duplicated, record the new one so we can apply it
                # on our next scan.
                child_data['manager']['fix-master'] = int(new)

                # Mark this child as needing scanning by removing its scan time.
                child_data['manager']['time-scanned'] = None
                modified = True

            if modified:
                s.status_save(status)

    # Some changes to a tracker can only safely be applied while we have the
    # lock for that bug.  The easiest way to do that is trigger scanning of
    # that bug and apply them when we encounter the bug.  Such fixes are marked
    # in the live status manager attributes, as fix-* markers.  Apply those now
    # and commit them to the persistent state.  Do all of this under the status
    # lock so setting/clearing the fix-* markers is atomic.
    def apply_fixes(s, bugid, bug):
        with s.lock_status():
            status_all = s.status_load()

            status = status_all.get(bugid)
            if status is None:
                return
            manager = status.get('manager')
            if manager is None:
                return

            bug_modified = False
            status_modified = False
            if 'fix-master' in manager:
                cinfo("{}: fix-master present master={}->{} applying".format(
                    bugid, bug.master_bug_id, manager['fix-master']))
                if bug.master_bug_id != manager['fix-master']:
                    bug.master_bug_id = manager['fix-master']
                    bug_modified = True
                del manager['fix-master']
                status_modified = True

            # Commit the changes to the bug.
            if bug_modified:
                bug.save()

            if status_modified:
                s.status_save(status_all)

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
        if s.args.bugs:
            bugs = []
            for bugid in s.args.bugs:
                if bugid.isdigit():
                    bugs.append(bugid)
                elif ':' in bugid:
                    # We will search for <series>:<source>:<target>
                    # if target is missing imply it from source.
                    bits = bugid.split(':')
                    if len(bits) < 3:
                        bits.append(bits[-1])

                    for search_id, search_data in s.status_start.items():
                        search_key = [
                            search_data.get('series', '-'),
                            search_data.get('source', '-'),
                            search_data.get('target', '-')]
                        if bits == search_key:
                            bugs.append(search_id)
                else:
                    cerror('    {}: bugid format unknown'.format(bugid), 'red')
                    continue

            for bugid in bugs:
                lpbug = s.lp.default_service.get_bug(bugid)
                cinfo('    LP: #%s - %s' % (lpbug.id, lpbug.title), 'magenta')
                retval[bugid] = lpbug.title
        elif not s.args.dependants_only:
            for project in WorkflowBug.projects_tracked:
                cinfo('project: %s' % project, 'magenta')
                search_tags            = ['kernel-release-tracking-bug', 'kernel-release-tracking-bug-live']
                search_tags_combinator = "All"
                search_status          = ["Triaged", "In Progress", "Incomplete", "Fix Committed"] # A list of the bug statuses that we care about
                search_since           = datetime(year=2013, month=1, day=1)
                lp_project = s.lp.default_service.projects[project]
                tasks = lp_project.search_tasks(status=search_status, tags=search_tags, tags_combinator=search_tags_combinator, modified_since=search_since)

                for task in tasks:
                    bug = task.bug
                    cinfo('    LP: #%s - %s' % (bug.id, bug.title), 'magenta')
                    retval[str(bug.id)] = bug.title

        cleave('WorkflowManager.buglist')
        return retval

    # manage
    #
    def manage(s):
        cinfo('Starting run ' + str(datetime.now()))
        if s.args.dependants_only:
            try:
                with s.single_dependants_only():
                    s.manage_payload()
            except BlockingIOError:
                cerror('dependants-only run already in progress.', 'red')

        elif not s.args.bugs:
            try:
                with s.single_thread():
                    s.manage_payload()
            except BlockingIOError:
                cerror('Full run already in progress.', 'red')

        else:
            s.manage_payload()
        cinfo('Completed run ' + str(datetime.now()))

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
            buglist = s.buglist
            bugs_pass = 0
            bugs_overall = 0

            if s.args.dependants_only:
                buglist = s.live_dependants_rescan()

            while len(buglist) > 0:
                # Make sure that each bug only appears once.
                buglist = list(set(buglist))

                bugs_pass += 1

                bugs_overall += len(buglist)

                buglist_rescan = []
                bugs_total = len(buglist)
                bugs_scanned = 0

                # Order such that parents are handled before their children.
                buglist = list(sorted(buglist, key=s.tracker_key))
                cinfo("manage_payload: scan={}".format(buglist))
                for bugid in buglist:
                    bugs_scanned += 1
                    with s.lock_bug(bugid):
                        cinfo('')
                        cinfo("Processing ({}/{} pass={} total={}): {} ({})".format(bugs_scanned, bugs_total, bugs_pass, bugs_overall, bugid, s.lp.bug_url(bugid)))

                        buglist_rescan += s.crank(bugid)

                # If we are interested in scanning dependants, trigger them if
                # they have a parent and that parent has been modified since
                # they were last scanned.
                if s.args.dependants or s.args.dependants_only:
                    buglist_rescan += s.live_dependants_rescan()

                buglist = buglist_rescan

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
        while True:
            try:
                return s.__crank(bugid)
            except PreconditionFailed:
                # When the cached launchpad copy of an object we are updating
                # is written back we check if the cached data we worked against
                # is still current.  Where it is not a PreconitionFailed is
                # thrown.  This could be triggered by an attempt to update the
                # main bug, or when updating any of the tasks on the bug.
                cinfo("PreconditionFailed: retrying")

    # __crank
    #
    def __crank(s, bugid):
        '''
        For the specified bug, continue to process all of the bugs tasks until none
        of them are changed from the previous processing.
        '''
        center('WorkflowManager.crank')

        #s.printlink = '%s : (%s)' % (bugid, s.lp.bug_url(bugid))
        #cinfo('Processing: %s' % s.printlink, 'cyan')

        rescan = []

        # If the bug was modified (task status changed) on that crank of the bug then
        # crank it again.
        #
        modified = False
        bug = None
        try:
            lpbug = s.lp.default_service.get_bug(bugid)
            if lpbug is None:
                cinfo('    LP: #{} (INVALID BUGID)'.format(bugid), 'magenta')
                s.status_set(bugid, None)
                raise WorkflowBugError('is invalid, skipping (and dropping)')
            if lpbug.duplicate_of is not None:
                cinfo('    LP: #{} (DUPLICATE)'.format(bugid), 'magenta')
                s.status_set(bugid, None)
                s.live_duplicates_mark(str(bugid), str(lpbug.duplicate_of.id))
                raise WorkflowBugError('is duplicated, skipping (and dropping)')
            bug = WorkflowBug(s.lp.default_service, bug=lpbug, ks=s.kernel_series, sru_cycle=s.sru_cycle, manager=s)
            if bug.error is not None:
                raise bug.error
            if bug.is_closed:
                # Update linkage.
                bug.add_live_children(s.live_children(bugid))
                bug.save()
                s.status_set(bugid, None)
                raise WorkflowBugError('is closed, skipping (and dropping)')
            if not bug.is_crankable:
                s.status_set(bugid, None)
                raise WorkflowBugError('not crankable, skipping (and dropping)')

            # Now we have a valid bug, see if we have any fixes to apply.
            s.apply_fixes(bugid, bug)

            # Update linkage.
            bug.add_live_children(s.live_children(bugid))

            tracker_status = s.status_get(bugid)

            # Catch direct modification of the bug.  We would be asked to scan
            # the bug but not ourselves modify it.
            modified_time = tracker_status.get('manager', {}).get('time-modified')
            if modified_time is not None and modified_time < lpbug.date_last_updated.replace(tzinfo=None):
                cinfo('    LP: #{} modified directly -- marking modified'.format(bugid), 'magenta')
                modified = True

            # Record existing interlocks to allow modifications to be detected.
            interlocks_before = tracker_status.get('interlocks', {})

            recrank = True
            while recrank:
                # Reset transient data for each crank run.
                bug.transient_reset_all()
                try:
                    cinfo('        ---------------------------------------  c r a n k  ---------------------------------------', 'green')
                    recrank = s.process_bug_tasks(bug)
                    modified |= recrank

                # XXX: should be a VariantError or something.
                except (PackageError, SnapError) as e:
                    for l in e.message:
                        cinfo(l, 'red')
            bug.save()

            # Update the global status for this bug.
            s.status_set(bugid, bug.status_summary(), modified=modified)
            bug.accept_new()

            # If we are a new bug and we have a master bug request that
            # be rescanned to ensure it gains our linkage.
            if bugid not in s.status_start and bug.is_derivative_package:
                cinfo("new derivative -- triggering master tracker")
                rescan.append(str(bug.master_bug_id))

            # If we are a new bug trigger all trackers in existance for this
            # target to ensure they notice if we are a blocking tracker.
            # be rescanned to ensure it gains our linkage.
            if bugid not in s.status_start:
                cinfo("new tracker -- triggering all trackers for this target")
                for tracker_nr, tracker_data in s.live_trackers_for_target(bug.series, bug.name, bug.target):
                    if str(tracker_nr) != str(bugid):
                        rescan.append(str(tracker_nr))

            # If our interlocks have changed and we have a master bug request
            # a rescan to ensure it has seen the latest interlocks.
            if bug.interlocks != interlocks_before and bug.is_derivative_package:
                cinfo("interlocks changed -- triggering master tracker")
                rescan.append(str(bug.master_bug_id))

        except (SeriesLookupFailure, WorkflowBugError) as e:
            modified = False
            for l in e.args:
                cerror(e.__class__.__name__ + ': ' + l)

        except WorkflowCrankError as e:
            modified = False
            for l in e.args:
                cerror(e.__class__.__name__ + ': ' + l)
            if bug is not None:
                bug.reasons['crank-failure'] = 'Stalled -- ' + e.args[0]
                status = bug.status_summary()
                bug.save()
                s.status_set(bugid, status, modified=False)
                bug.accept_new()

        except WorkflowCorruptError as e:
            modified = False
            for l in e.args:
                cerror(e.__class__.__name__ + ': ' + l)
            if bug is not None:
                critical = {'reason': {'crank-failure': 'Stalled -- ' + e.args[0]}}
                s.status_set(bugid, update=critical, modified=False)
                bug.accept_new()

        cleave('WorkflowManager.crank')
        return rescan

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
            username = task.assignee.username if task.assignee is not None else None
            cinfo("        %-25s  %15s  %10s  %s (%s)" % (task.name, task.status, task.importance, username, workflow_task_name), 'magenta')

            therest = task_name[len(s.projectname) + 1:].strip()
            task_name = therest

            if workflow_task_name not in s._task_map:
                task.reason = 'Stalled -- unknown workflow task'
                cinfo('        Unknown workflow task')
                continue

            try:
                cls = s._task_map[workflow_task_name](s.lp, task, bug)
                if cls.evaluate_status(task.status) and not s.args.dryrun:
                    retval = True
                    cinfo('        True')
            except (PackageError, SnapError) as e:
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
