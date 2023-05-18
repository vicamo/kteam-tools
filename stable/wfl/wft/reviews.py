from datetime                                   import timedelta

from wfl.log                                    import center, cleave, cinfo
from .base                                      import TaskHandler


class SourceReview(TaskHandler):

    IN = 1
    NOT_IN = 2

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super().__init__(lp, task, bug)

        s.jumper['New']            = s._new
        s.jumper['Confirmed']      = s._confirmed
        s.jumper['Triaged']        = s._confirmed
        s.jumper['In Progress']    = s._confirmed
        s.jumper['Fix Committed']  = s._recind
        s.jumper['Fix Released']   = s._recind
        s.jumper['Incomplete']     = s._confirmed

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while True:
            ready = True
            for which, task_name, ready_stati in s.prerequisites:
                cinfo("{}: {} ? {}".format(s.review_task, task_name, ready_stati))
                if which == SourceReview.IN and s.bug.task_status(task_name) not in ready_stati:
                    ready = False
                elif which == SourceReview.NOT_IN and s.bug.task_status(task_name) in ready_stati:
                    ready = False
            if not ready:
                break

            # Record the delta between the build ppa and whatever follows.
            s.bug.debs.delta_record('promote-to-proposed', 'ppa', 'Proposed')
            prepare_id = s.bug.debs.prepare_id

            # Reject if the prepare_id is bad.
            if prepare_id is None:
                cinfo("Trying to go Confirmed with prepare_id==None")

            # Otherwise take the current build stamp, and ask for review.
            else:
                s.bug.clamp_assign(s.review_task, prepare_id)
                s.task.status = 'Confirmed'
                retval = True

            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _confirmed
    #
    def _confirmed(s):
        center(s.__class__.__name__ + '._confirmed')
        retval = s._recind()

        pps = s.bug.task_status(':prepare-packages')

        # If all of our binaries are now ready upgrade to Triaged.
        status = s.task.status
        if status == 'Confirmed' and pps == 'Fix Released':
            s.task.status = 'Triaged'
            retval = True

        status = s.task.status
        if status == 'Confirmed':
            state = s.task.reason_state('Pending', timedelta(hours=12))
            s.task.reason = '{} -s ready for review'.format(state)

        elif status == 'Triaged':
            s.task.reason = 'Stalled -s ready for review (built)'

        elif status == 'Incomplete':
            s.task.reason = 'Stalled -- review FAILED'

        elif status == 'In Progress':
            s.task.reason = '{} -s review in progress'.format(
                s.task.reason_state('Ongoing', timedelta(hours=4)))

        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval

    # _recind
    #
    def _recind(s):
        center(s.__class__.__name__ + '._recind')
        retval = False

        clamp = s.bug.clamp(s.review_task)
        if clamp is None or str(clamp) != str(s.bug.debs.prepare_id):
            cinfo("{} id has changed, recinding {}".format(s.review_task, s.review_task))
            if s.task.status != 'New':
                s.task.status = 'New'
                retval = True

        cleave(s.__class__.__name__ + '._recind (%s)' % retval)
        return retval


class SruReview(SourceReview):

    review_task = 'sru-review'
    prerequisites = [
            [SourceReview.IN, ':prepare-packages', ['Fix Committed', 'Fix Released']]]


class NewReview(SourceReview):

    review_task = 'new-review'
    prerequisites = [
            [SourceReview.IN, ':prepare-packages', ['Fix Committed', 'Fix Released']],
            [SourceReview.NOT_IN, 'sru-review', ['New', 'Incomplete']]]

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super().__init__(lp, task, bug)

        s.jumper['Fix Committed']  = s._built

        cleave(s.__class__.__name__ + '.__init__')

    def fetch_binary_list(self, src):
        if src is None:
            return False, []
        happy = True
        for build in src.getBuilds():
            if build.buildstate != 'Successfully built':
                happy = False
        binaries = []
        binaries_seen = set()
        for binary in src.getPublishedBinaries(active_binaries_only=False):
            status = binary.status
            flags = [status]
            binary_arch = binary.distro_arch_series_link.split("/")[-1]
            binary_name = binary.binary_package_name
            duplicate_key = (binary_name, binary_arch)
            if duplicate_key in binaries_seen:
                continue
            binaries_seen.add(duplicate_key)
            if status != "Published":
                happy = False
            # Handle base versions (x.y.z-a) in package names as -ABI.
            binary_bits = binary.binary_package_version.split(".")
            if len(binary_bits) >= 4:
                binary_abi = ".".join(binary.binary_package_version.split(".", 4)[0:3])
                binary_name_abi = binary_name.replace("-" + binary_abi, "-ABI")
            else:
                binary_name_abi = binary_name
            if binary_name != binary_name_abi:
                flags.append("ABI")
            binaries.append((binary_name_abi, binary_arch, flags))
        return happy, binaries

    def signing_compat(self, compatibility):
        if compatibility == None:
            return "--not-present--"
        if len(compatibility) == 0:
            return "--empty--"
        return " ".join(compatibility)

    def fetch_usc(self, package_spph):
        changes_url = package_spph.changesFileUrl()
        if changes_url is None:
            return False, None

        # If we managed to find a changes file then we can extract the list.
        changes_url = changes_url.replace('https://launchpad.net/', 'https://api.launchpad.net/devel/')
        changes = self.lp._browser.get(changes_url)
        compatibility = None
        for line in changes.decode('utf-8').rstrip().split('\n'):
            if line.startswith("Ubuntu-Compatible-Signing:"):
                compatibility = line.split()[1:]
        cinfo("Ubuntu-Compatible-Signing {} source".format(self.signing_compat(compatibility)))

        # If there are builds available check they are matching compatibility.
        happy = True
        compatibility_match = True
        for build in package_spph.getBuilds():
            # If we managed to find a changes file then we can extract the list.
            changes_url = build.changesfile_url
            if changes_url is None:
                cinfo("  Ubuntu-Compatible-Signing - {} build not available".format(build.arch_tag))
                happy = False
                continue
            changes_url = build.changesfile_url.replace('https://launchpad.net/', 'https://api.launchpad.net/devel/')
            changes = self.lp._browser.get(changes_url)
            build_compat = None
            for line in changes.decode('utf-8').rstrip().split('\n'):
                if line.startswith("Ubuntu-Compatible-Signing:"):
                    build_compat = line.split()[1:]
                    if compatibility != build_compat:
                        compatibility_match = False
            cinfo("  Ubuntu-Compatible-Signing {} {}".format(self.signing_compat(build_compat), build.arch_tag))

        # Report compatibility error.
        if not compatibility_match:
            cinfo("compatibility missmatch")
            happy = False

        return happy, compatibility

    # new_binaries
    #
    def new_binaries(s):
        center(s.__class__.__name__ + '.new_binaries')
        retval = True

        pocket_next = 'Release' if s.bug.is_development_series else 'Updates' 
        pocket_next_routing = s.bug.debs.pocket_routing(pocket_next)
        pocket_next_route = pocket_next_routing[0] if pocket_next_routing is not None else None

        bi = s.bug.debs.build_info
        happy_overall = True
        binaries_old = []
        binaries_new = []
        for pkg in s.bug.debs.dependent_packages_for_pocket(pocket_next):
            cinfo('considering {} in {} -> {} '.format(pkg, 'ppa', bi[pkg]['ppa']['source']))
            happy, binaries = s.fetch_binary_list(bi[pkg]['ppa']['source'])
            happy_overall &= happy
            binaries_new += binaries
            cinfo('  happy={} binaries={}'.format(happy, len(binaries)))
            if happy:
                happy, compatibility = s.fetch_usc(bi[pkg]['ppa']['source'])
                happy_overall &= happy
                cinfo('  happy={} compatibility={}'.format(happy, compatibility))

            cinfo('considering {} in {} -> {} '.format(pkg, pocket_next, bi[pkg][pocket_next]['source']))
            happy, binaries = s.fetch_binary_list(bi[pkg][pocket_next]['source'])
            binaries_old += binaries
            cinfo('  happy={} binaries={}'.format(happy, len(binaries)))

        # Perform a New comparison.  We have collected all of the binaries for the
        # old and new sources packages.  Eliminate those from the new found in the old,
        # for the remainder attempt to look them up directly.  If they are still not found
        # they are most likely New (or an ABI specific file).
        if pocket_next_route is None:
            # This is an entirely New kernel, we have no packages in pocket_next for it.
            cinfo("Completely new kernel considering New")
            new_binaries = True

        else:
            pocket_next_archive, pocket_next_pocket = pocket_next_route
            cinfo("{} {}".format(len(binaries_old), len(binaries_new)))
            new_binaries = False
            for binary, arch, flags in binaries_new:
                if (binary, arch, flags) in binaries_old:
                    cinfo("{} MATCH-OLD".format(binary))
                else:
                    bins_old = pocket_next_archive.getPublishedBinaries(
                        exact_match=True, order_by_date=True,
                        binary_name=binary, pocket=pocket_next_pocket
                    )
                    if len(bins_old) > 0:
                        cinfo("{} MATCH-ARCHIVE".format(binary))
                    else:
                        cinfo("{} MISS-MATCH".format(binary))
                        new_binaries = True

        retval = not happy_overall or new_binaries
        cinfo("happy_overall={} new_binaries={} -> retval={}".format(happy_overall, new_binaries, retval))

        cleave(s.__class__.__name__ + '.new_binaries (%s)' % retval)
        return retval

    # _built
    #
    def _built(s):
        center(s.__class__.__name__ + '._built')
        retval = s._recind()

        # If all of our binaries are now ready upgrade to Triaged.
        if s.bug.task_status(':prepare-packages') == 'Fix Released':
            # Check the binary status, if there are News then this
            # new-review needs to be re-considered.
            if s.new_binaries():
                cinfo('New binaries detected moving Triaged')
                s.task.status = 'Triaged'
                retval = True
            else:
                cinfo('No New binaries detected moving Fix Released')
                s.task.status = 'Fix Released'
                retval = True

        s.task.reason = 'Ongoing -s review complete (waiting for binaries)'

        return retval

    @property
    def signing_bot(s):
        has_bot = False
        for task_name in s.bug.tasks_by_name:
            if task_name.startswith('canonical-signing-jobs'):
                has_bot = True
        return has_bot or 'kernel-signing-bot' in s.bug.tags

    def evaluate_status(self, status):
        # SIGNING-BOT: we have two different workflows for reviewing and
        # promoting kernels to proposed: the manual two step process which
        # utilises a pair of copy-proposed-kernel incantations, and signing-bot
        # driven workflow.
        #
        # When performing the manual two step process we implicitly perform the
        # new-review as part of the promote-to-proposed copy, so we effectivly
        # ignore that task and let promote-to-proposed move Confirmed once the
        # kernels are otherwise ready to promote.  If the new-review is then
        # signed off we will also switch into canonical-signing-bot mode, and
        # that task becomes blocking on our workflow.
        if not self.signing_bot:
            # Interlock with manual promotion.  If we move beyond confirmed and
            # we are not under the control of canonical-signing-bot then
            # promote-to-proposed status defines new-review status. Copy it over.
            nr_status = self.task.status
            sr_status = self.bug.task_status('promote-to-proposed')
            if sr_status == 'In Progress':
                 nr_status = 'In Progress'

            elif sr_status == 'Fix Committed':
                 nr_status = 'Fix Released'

            elif sr_status == 'Incomplete':
                 nr_status = 'Incomplete'

            if self.task.status != nr_status:
                cinfo('            no canonical-signing-bot tracking manual promotion promote-to-proposed={} new-review={}'.format(sr_status, nr_status))
                self.task.status = nr_status
                return True

        return super().evaluate_status(status)


# vi: set ts=4 sw=4 expandtab syntax=python
