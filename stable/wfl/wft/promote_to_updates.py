
from wfl.log                            import center, cleave, cinfo, cdebug
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

            # Confirm we think we are in proposed.
            if s.bug.task_status('promote-to-proposed') != 'Fix Released':
                break

            # There is no point in considering prerequisites before we are
            # at least in proposed.
            if not s.bug.debs.all_built_in_src_dst('Proposed', 'Updates'):
                cdebug("promote-to-updates not all built")
                reason = 'Stalled -- promote-to-proposed complete but not all packages are reporting built'
                detail = s.bug.debs.all_built_in_src_dst_detail("Proposed", "Updates")
                if len(detail):
                    reason += ": " + ", ".join(detail)
                s.task.reason = reason
                break

            # Note this will set appropriate reasons.
            prerequisites = s._prerequisites_released()

            # If testing is not complete, we are not ready to release.
            if not s._testing_completed():
                cdebug("promote-to-updates testing not complete")
                break

            # See if we are blocked by a derivative.
            blocks = s.bug.block_present('hold-promote-to-updates')
            if blocks is not None:
                cinfo("promote-to-updates held {}".format(blocks))
                s.task.reason = blocks
                break

            if not prerequisites and not s.bug.manual_unblock("prerequisites"):
                s.task.reason = 'Pending -- prerequisites not ready'
                break

            if s.bug.debs.older_tracker_in_proposed_any and not s.bug.manual_unblock("earlier-spin"):
               # This is more serious if the cycle is actually ready to release.
               severity = "Stalled" if s._cycle_ready() else "Holding"
               s.task.reason = severity + ' -- waiting for earlier spin to move to Updates'
               break

            if s.bug.manual_block("promote-to-updates") or s._kernel_block():
                s.task.reason = 'Stalled -- kernel-block/kernel-block-proposed tag present'
                break

            if s._in_blackout():
                s.task.reason = 'Holding -- package in development blackout'
                break

            if not s._all_signoffs_verified():
                # Note this will set an appropriate reason.
                cdebug("promote-to-updates signoffs not verified")
                break

            if not s._cycle_ready() and not s._kernel_manual_release():
                s.task.reason = 'Holding -- cycle not ready to release'
                break

            if s.bug.master_bug is not None:
                if not s.master_bug_ready() and not s._kernel_manual_release():
                    s.task.reason = 'Holding -- parent tracker not ready for release'
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

            pull_back = False

            if s._kernel_manual_release():
                break

            if s.bug.master_bug is not None:
                if not s.master_bug_ready():
                    cinfo('            Master bug no longer ready pulling back from Confirmed', 'yellow')
                    pull_back = True

            blocks = s.bug.block_present('hold-promote-to-updates')
            if blocks is not None:
                cinfo("promote-to-updates held {}".format(blocks))
                cinfo('            A hold-promote-to-updates present ({}) on this tracking bug pulling back from Confirmed'.format(blocks), 'yellow')
                pull_back = True

            # Note this will set appropriate reasons.
            prerequisites = s._prerequisites_released()
            if not prerequisites and not s.bug.manual_unblock("prerequisites"):
                cinfo("            Prerequisites not reported available pulling back from Confirmed", 'yellow')
                pull_back = True

            if s.bug.debs.older_tracker_in_proposed_any and not s.bug.manual_unblock("earlier-spin"):
                cinfo("            Earlier spin active in Proposed pulling back from Confirmed", 'yellow')
                pull_back = True

            if s.bug.manual_block("promote-to-updates") or s._kernel_block():
                cinfo('            A kernel-block/kernel-block-proposed on this tracking bug pulling back from Confirmed', 'yellow')
                pull_back = True

            if s._in_blackout():
                cinfo('            Package now in development blackout pulling back from Confirmed', 'yellow')
                pull_back = True

            if not s._all_signoffs_verified():
                # Note this will set an appropriate reason.
                pull_back = True

            if not s._cycle_ready():
                cinfo('            Cycle no longer ready for release pulling back from Confirmed', 'yellow')
                pull_back = True

            if pull_back:
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

                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -- ready to copy'
                else:
                    s.task.reason = 'Ongoing -- packages not yet published'
                break

            cinfo('    All components are now in -updates', 'magenta')
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
