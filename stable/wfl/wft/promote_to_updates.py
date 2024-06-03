
from wfl.log                            import center, cleave, cinfo, cdebug, centerleave
from .promoter                          import Promoter

class PromoteToUpdates(Promoter):
    '''
    A Task Handler for the propose-to-proposed task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToUpdates, s).__init__(lp, task, bug)

        s.jumper['New']           = s._ready_for_updates
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Incomplete']    = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion

        cleave(s.__class__.__name__ + '.__init__')


    @centerleave
    def _ready_to_promote(s):
            # Confirm we think we are in proposed.
            if s.bug.task_status('promote-to-proposed') != 'Fix Released':
                return False

            # There is no point in considering prerequisites before we are
            # at least in proposed.
            if not s.bug.debs.all_built_in_src_dst('Proposed', 'Updates'):
                cdebug("promote-to-updates not all built")
                reason = 'Stalled -- promote-to-proposed complete but not all packages are reporting built'
                detail = s.bug.debs.all_built_in_src_dst_detail("Proposed", "Updates")
                if len(detail):
                    if len(detail) > 3:
                        detail = detail[0:2] + ['(+{} others)'.format(len(detail) - 2)]
                    reason += ": " + ", ".join(detail)
                s.task.reason = reason
                return False

            # Note this will set appropriate reasons.
            prerequisites = s._prerequisites_released()

            # If testing is not complete, we are not ready to release.
            if not s._testing_completed():
                cdebug("promote-to-updates testing not complete")
                return False

            # See if we are blocked by a derivative.
            blocks = s.bug.block_present('hold-promote-to-updates')
            if blocks is not None:
                cinfo("promote-to-updates held {}".format(blocks))
                s.task.reason = blocks
                return False

            if not prerequisites and not s.bug.manual_unblock("prerequisites"):
                s.task.reason = 'Pending -- prerequisites not ready'
                return False

            if s.bug.debs.older_tracker_in_proposed_any and not s.bug.manual_unblock("earlier-spin"):
                # This is more serious if the cycle is actually ready to release.
                severity = "Stalled" if s._cycle_ready() else "Holding"
                s.task.reason = severity + ' -- waiting for earlier spin to move to Updates'
                return False

            if s.bug.manual_block("promote-to-updates") or s._kernel_block():
                s.task.reason = 'Stalled -- kernel-block/kernel-block-proposed tag present'
                return False

            if s._in_blackout():
                s.task.reason = 'Holding -- package in development blackout'
                return False

            if not s._all_signoffs_verified():
                # Note this will set an appropriate reason.
                cdebug("promote-to-updates signoffs not verified")
                return False

            if not s._cycle_ready() and not s._kernel_manual_release():
                s.task.reason = 'Holding -- cycle not ready to release'
                return False

            if s.bug.master_bug is not None:
                if not s.master_bug_ready() and not s._kernel_manual_release():
                    s.task.reason = 'Holding -- parent tracker not ready for release'
                    return False

            return True

    # _ready_for_updates
    #
    def _ready_for_updates(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_updates')
        retval = False

        while True:
            # If we have no routing for updates then we are invalid.
            if s.bug.debs.routing('Updates') is None:
                cinfo("promote-to-updates invalid with no Updates route")
                s.task.status = 'Invalid'
                retval = True
                break

            # The kernels below are in evaluation.  These only get as far
            # as -proposed and will not be promoted further:
            #
            if s.bug.is_proposed_only:
                s.task.status = 'Invalid'
                retval = True
                break

            # Confirm we are ready to promote.
            if not s._ready_to_promote():
                break

            # Record what is missing as we move to Confirmed.
            delta = s.bug.debs.built_in_src_dst_delta('Proposed', 'Updates')
            s.bug.bprops.setdefault('delta', {})[s.task.name] = delta

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._ready_for_updates (%s)' % retval)
        return retval

    # _verify_promotion
    #
    def _verify_promotion(s):
        center(s.__class__.__name__ + '._verify_promotion')
        retval = False

        while not retval:
            if s.task.status not in ('Confirmed'):
                break

            if not s._ready_to_promote():
                s.task.status = 'New'
                retval = True

            break

        while not retval:
            # Check if packages were copied to the right pocket->component
            #
            if not s.bug.debs.packages_released:
                # Confirm the packages remain available to copy.
                if not s.bug.debs.all_built_in_src_dst('Proposed', 'Updates'):
                    s.task.reason = 'Alert -- packages no longer available'
                    if s.task.status != 'Incomplete':
                        s.task.status = 'Incomplete'
                        retval = True
                    break
                elif s.task.status == "Incomplete":
                    s.task.status = "New"
                    retval = True
                    break

                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -- ready to copy'
                elif (s.task.status == 'Fix Committed'
                    and s.bug.debs.all_in_pocket("Updates")
                    and s.bug.debs.any_superseded_in_pocket("Updates")
                ):
                    s.task.reason = 'Stalled -- packages published with superseded binaries'
                else:
                    s.task.reason = 'Ongoing -- packages not yet published'
                break

            cinfo('    All components are now in -updates', 'magenta')
            if (
                "-aws" in s.bug.name
                or "-azure" in s.bug.name
                or "-gcp" in s.bug.name
                or "-ibm" in s.bug.name
                or "-oracle" in s.bug.name
            ):
                s.bug.announce(
                    "cloud-transition-updates",
                    subject="[LP#{id}](https://launchpad.net/bugs/{id}) {cycle} {series}:{source} in updates".format(
                        id=s.bug.lpbug.id,
                        cycle=s.bug.sru_spin_name,
                        series=s.bug.series,
                        source=s.bug.name,
                    )
                )
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            retval = True
            break

        # If we are a live task by here request monitoring for
        # all interesting routes.
        if s.task.status not in ('New', 'Confirmed', 'Fix Released', 'Invalid'):
            s.bug.debs.monitor_routes(["Proposed", "Updates"])

        cleave(s.__class__.__name__ + '._verify_promotion (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
