from datetime                                   import datetime, timedelta, timezone

from wfl.log                                    import center, cleave, cinfo, cdebug
from wfl.gcp_bucket                             import GcpBucketObject, GcpBucketError
from .base                                      import TaskHandler

class Promoter(TaskHandler):
    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(Promoter, s).__init__(lp, task, bug)
        cleave(s.__class__.__name__ + '.__init__')

    def _cycle_ready(s):
        if s.bug.is_development or (s.bug.master_bug is not None and s.bug.master_bug.is_development):
            return True

        if s.bug.sru_spin is None:
            return False
        return s.bug.sru_spin.ready_to_release

    def _cycle_hold(s):
        if s.bug.is_development or (s.bug.master_bug is not None and s.bug.master_bug.is_development):
            return False

        # If the cycle is not defined just hold the kernel.
        if s.bug.sru_spin is None:
            return True
        return s.bug.sru_spin.hold

    def _in_blackout(s):
        '''
        If a package is under a development blackout return True.
        '''
        return s.bug.swm_config.in_blackout(datetime.now())

    def _kernel_block(s):
        '''
        If a 'kernel-block' tag exist return True.
        '''
        center(s.__class__.__name__ + '._kernel_block')
        retval = False

        if 'kernel-block' in s.bug.tags or 'kernel-block-proposed' in s.bug.tags:
            retval = True

        cleave(s.__class__.__name__ + '._kernel_block (%s)' % retval)
        return retval

    def _kernel_manual_release(s):
        '''
        If a 'kernel-manual-release' tag exist return True.
        '''
        center(s.__class__.__name__ + '._kernel_manual_release')
        retval = False

        if 'kernel-manual-release' in s.bug.tags:
            retval = True

        cleave(s.__class__.__name__ + '._kernel_manual_release (%s)' % retval)
        return retval

    def _kernel_block_ppa(s):
        '''
        If a 'kernel-block-ppa' tag exist return True.
        '''
        center(s.__class__.__name__ + '._kernel_block_ppa')
        retval = False

        if 'kernel-block' in s.bug.tags or 'kernel-block-ppa' in s.bug.tags:
            retval = True

        cleave(s.__class__.__name__ + '._kernel_block_ppa (%s)' % retval)
        return retval

    def _kernel_unblock_ppa(s):
        '''
        If a 'kernel-unblock-ppa' tag exist return True.
        '''
        center(s.__class__.__name__ + '._kernel_unblock_ppa')
        retval = False

        if 'kernel-unblock-ppa' in s.bug.tags:
            retval = True

        cleave(s.__class__.__name__ + '._kernel_unblock_ppa (%s)' % retval)
        return retval

    def _block_proposed(s):
        '''
        If any 'block-proposed' tags still exist return True.
        '''
        center(s.__class__.__name__ + '.block_proposed')
        retval = False

        if ('block-proposed' in s.bug.tags) or ('block-proposed-%s' % s.bug.series in s.bug.tags):
            return True

        cleave(s.__class__.__name__ + '.block_proposed (%s)' % retval)
        return retval

    def _signoff_verified(s, which):
        '''
        Check if the *-signoff task has been set to 'Fix Released'. Development
        series tracking bugs do not have this task and should always return True.
        '''
        center(s.__class__.__name__ + '._signoff_verified({})'.format(which))
        retval = False
        if which not in s.bug.tasks_by_name:
            retval = True
        elif s.bug.tasks_by_name[which].status in ('Fix Released', 'Invalid'):
            retval = True
        else:
            cinfo('            {} is neither "Fix Released" nor "Invalid" ({})'.format(
                which, s.bug.tasks_by_name[which].status), 'yellow')
        cleave(s.__class__.__name__ + '._signoff_verified ({})'.format(retval))
        return retval

    def _all_signoffs_verified(s):
        missing = []
        for signoff in ('stakeholder-signoff', 'kernel-signoff', 'security-signoff'):
            if not s._signoff_verified(signoff):
                missing.append(signoff)

        if len(missing):
            s.task.reason = 'Holding -- waiting for signoffs: {}'.format(' '.join(missing))

        return len(missing) == 0

    # _testing_completed
    #
    def _testing_completed(s):
        """
        """
        center(s.__class__.__name__ + '._testing_completed')
        retval = False # For the stub

        while True:
            # If all testing tasks have been set to Fix Released we are ready
            # to release.
            #
            testing_tasks = [
                'automated-testing',
                'regression-testing',
            ]
            if not s.bug.is_development_series:
                testing_tasks.append('certification-testing')
                testing_tasks.append('verification-testing')
            tested = True
            for task in testing_tasks:
                if task not in s.bug.tasks_by_name:
                    s.task.reason = 'Stalled -- %s task is missing' % (task,)
                    tested = False
                elif s.bug.tasks_by_name[task].status not in ['Fix Released', 'Invalid', "Won't Fix"]:
                    cinfo('            %s is not in %s (%s)' % (task, ['Fix Released', 'Invalid', "Won't Fix"], s.bug.tasks_by_name[task].status), 'yellow')
                    tested = False

            if not tested:
                break

            retval = True
            break

        cleave(s.__class__.__name__ + '._testing_completed (%s)' % retval)
        return retval

    # _prerequisites_released(s):
    #
    def _prerequisites_released(s):
        center(s.__class__.__name__ + '._prerequisites_released')
        retval = True

        # Look up the GKE kernel flavour.  Allows us to point
        # linux-image-gke-5.4 to the gcp kernel binaries.
        kernel_flavour = s.bug.swm_config.gke_flavour

        # Build a list of packages we are expecting.
        gke_nvidia_packages = []
        gke_releases = s.bug.swm_config.gke_releases
        if gke_releases:
            for release in gke_releases:
                gke_nvidia_packages.append('{}-{}-stable-amd64'.format(kernel_flavour, release))
        gke_nvidia_packages += s.bug.swm_config.gke_nvidia_packages
        nvidia_releases = s.bug.swm_config.nvidia_releases

        # Check the list of artifacts.
        if gke_nvidia_packages or nvidia_releases:
            wanted = []
            for release in nvidia_releases:
                if s.bug.swm_config.nvidia_driver_legacy_naming:
                    wanted.append(('nvidia-driver-gke_{}-{}-{}-{}.'.format(s.bug.kernel, s.bug.abi, kernel_flavour, release), True))
                wanted.append(('nvidia-driver-gke_{}-{}-{}-{}-{}.'.format(s.bug.series, s.bug.kernel, s.bug.abi, kernel_flavour, release), True))
            for flavour in gke_nvidia_packages:
                wanted.append(('current-driver-{}-{}-{}-{}'.format(s.bug.series, s.bug.kernel, s.bug.abi, flavour), False))

            missing = []
            for obj, prefix in wanted:
                cdebug("checking prefix={} {}".format(prefix, obj))
                gke_object = GcpBucketObject('ubuntu_nvidia_packages', obj, prefix=prefix)
                if gke_object.present is False:
                    if prefix:
                        obj += '*'
                    cdebug("missing {}".format(obj))
                    missing.append(obj)
            if len(missing) > 0:
                if len(missing) > 3:
                    missing = missing[0:2] + ['(+{} others)'.format(len(missing) - 2)]
                s.bug.reasons['prerequisite-nvidia'] = "Pending -- Nvidia objects not found -- {}".format(' '.join(missing))
                s.bug.refresh_at(datetime.now(timezone.utc) + timedelta(hours=1),
                    'polling for nvidia objects {}'.format(' '.join(missing)))
                retval = False

        missing = s.bug.debs.prerequisite_packages()
        cinfo("PREREQ-PACKAGES missing={}".format(missing))
        if len(missing):
            s.bug.reasons['prerequisite-packages'] = "Pending -- packages not released -- {}".format(' '.join(missing))
            retval = False

        cleave(s.__class__.__name__ + '._prerequisites_released (%s)' % retval)
        return retval

    # master_bug_ready
    #
    def master_bug_ready(s):
        center(s.__class__.__name__ + '.master_bug_ready')
        retval = False

        master = s.bug.master_bug

        # If we are a development kernel and our parent is not then we should
        # ignore our parents status.  We do not want to hold development kernels
        # if their testing is good, it is the wild west after all.
        if s.bug.is_development and not master.is_development:
            retval = True
            cleave(s.__class__.__name__ + '.master_bug_ready (%s)' % retval)
            return retval

        # Check if it already released.  If it did we do not need to check if it is
        # otherwise ready to release.
        for task in ('promote-to-updates', 'promote-to-release'):
            if task in master.tasks_by_name and master.tasks_by_name[task].status == 'Fix Released':
                cdebug('master bug already released')
                retval = True
                cleave(s.__class__.__name__ + '.master_bug_ready (%s)' % retval)
                return retval

        if master.debs.routing('Updates') is None and master.debs.routing('Release') is None:
            retval = True
            cinfo('master bug has no routing for Updates/Release ignoring', 'yellow')

        else:
            # Check if the master bug could release.
            required_sru_tasks = {
                'prepare-package'            : ['Fix Released'],
                'prepare-package-lbm'        : ['Fix Released'],
                'prepare-package-meta'       : ['Fix Released'],
                'prepare-package-ports-meta' : ['Fix Released'],
                'prepare-package-signed'     : ['Fix Released'],
                'promote-to-proposed'        : ['Confirmed', 'Fix Released'],
                'promote-to-updates'         : ['Confirmed', 'In Progress', 'Fix Released'],
                'promote-to-release'         : ['Confirmed', 'In Progress', 'Fix Released'],
            }

            testing_complete = ['Fix Released', "Won't Fix"]
            required_sru_tasks['automated-testing']     = testing_complete
            required_sru_tasks['regression-testing']    = testing_complete

            # XXX: as the tasks are invalid (through being missing) it is not
            #      clear we cannot just check them all always.
            if not master.is_development_series:
                required_sru_tasks['certification-testing'] = testing_complete
                required_sru_tasks['verification-testing']  = testing_complete

            tasks = required_sru_tasks
            retval = True
            for t in tasks:
                if master.task_status(t) not in (tasks[t] + ['Invalid']):
                    cinfo('master bug task %s is \'%s\' and not one of: %s' % (t, master.tasks_by_name[t].status, str(tasks[t])), 'yellow')
                    retval = False
                    break

        if 'kernel-block' in master.tags or 'kernel-block-proposed' in master.tags:
            cinfo('master bug is blocked')
            retval = False

        cleave(s.__class__.__name__ + '.master_bug_ready (%s)' % retval)
        return retval

    # master_bug_ready
    #
    def master_bug_ready_for_proposed(s):
        center(s.__class__.__name__ + '.master_bug_ready')
        retval = False

        required_sru_tasks = {
            'promote-to-proposed'        : ['Confirmed', 'In Progress', 'Fix Committed', 'Fix Released'],
        }

        master = s.bug.master_bug

        # If the master bug does not have routing for -proposed we should not block on it.
        if master.debs.routing('Proposed') is None:
            retval = True
            cinfo('master bug has no routing for Proposed ignoring', 'yellow')

        else:
            tasks = required_sru_tasks
            retval = True
            for t in tasks:
                try:
                    if master.tasks_by_name[t].status not in tasks[t]:
                        cinfo('master bug task %s is \'%s\' and not one of: %s' % (t, master.tasks_by_name[t].status, str(tasks[t])), 'yellow')
                        retval = False
                        break
                except KeyError:
                    cdebug('master bug does not contian the %s task' % t)

        cleave(s.__class__.__name__ + '.master_bug_ready (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
