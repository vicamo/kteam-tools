
from wfl.log                            import center, cleave, cinfo
from .promoter                          import Promoter

class PromoteToSecurity(Promoter):
    '''
    A Task Handler for the promote-to-security task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToSecurity, s).__init__(lp, task, bug)

        s.jumper['New']           = s._ready_for_security
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion

        cleave(s.__class__.__name__ + '.__init__')

    # _ready_for_security
    #
    def _ready_for_security(s):
        """
        """
        center(s.__class__.__name__ + '._ready_for_security')
        retval = False # For the stub

        while True:

            # If we have no routing for security then we are invalid.
            if s.bug.debs.routing('Security') is None:
                s.task.status = 'Invalid'
                retval = True
                break

            # The kernels below are in evaluation.  These only get as far
            # as -proposed and will not be promoted further:
            #
            if s.bug.is_proposed_only:
                s.task.status = 'Invalid'
                if 'security-signoff' in s.bug.tasks_by_name:
                    s.bug.tasks_by_name['security-signoff'].status = 'Invalid'
                retval = True
                break

            # If the security-signoff task is 'Invalid' then this task should also
            # be 'Invalid'. This task will no longer be processed after that.
            #
            if 'security-signoff' in s.bug.tasks_by_name:
                if s.bug.tasks_by_name['security-signoff'].status == 'Invalid':
                    s.task.status = 'Invalid'
                    retval = True
                    break

            # We are only valid if there is a promote-to-updates tasks.
            if 'promote-to-updates' not in s.bug.tasks_by_name:
                s.task.status = 'Invalid'
                retval = True
                break

            # If promote-to-updates is moved Invalid we should follow.
            if s.bug.tasks_by_name['promote-to-updates'].status == 'Invalid':
                s.task.status = 'Invalid'
                retval = True
                break

            # We can consider moving Confirmed as soon as promote-to-updates
            # moves past 'Confirmed', then we will follow the packages separatly.
            if s.bug.tasks_by_name['promote-to-updates'].status in ('New', 'Confirmed'):
                break

            # Check we meet the release criteria for -security; currently
            # that we have given the packages sufficient time to replicate.
            if not s.bug.debs.ready_for_security:
                if s.bug.tasks_by_name['promote-to-updates'].status == 'Fix Released':
                    s.task.reason = 'Holding -- not ready for security (replication dwell)'
                break

            if s.bug.manual_block("promote-to-security") or s._kernel_block():
                s.task.reason = 'Stalled -- kernel-block/kernel-block-proposed tag present'
                break

            if s._in_blackout():
                s.task.reason = 'Holding -- package in development blackout'
                break

            if not s._cycle_ready() and not s._kernel_manual_release():
                s.task.reason = 'Holding -- cycle not ready to release'
                break

            # Record what is missing as we move to Confirmed.
            delta = s.bug.debs.built_in_src_dst_delta('Updates', 'Security')
            s.bug.bprops.setdefault('delta', {})[s.task.name] = delta

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._ready_for_security (%s)' % retval)
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

            if s.bug.manual_block("promote-to-security") or s._kernel_block():
                cinfo('            A kernel-block/kernel-block-proposed on this tracking bug pulling back from Confirmed', 'yellow')
                pull_back = True
            if s._in_blackout():
                cinfo('            Package now in development blackout pulling back from Confirmed', 'yellow')
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
            if not s.bug.debs.packages_released_to_security:
                if s.task.status == 'Confirmed':
                    s.task.reason = 'Pending -- ready to copy'
                else:
                    s.task.reason = 'Ongoing -- packages not yet published'
                break

            cinfo('    All components are now in -proposed', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            retval = True
            break

        # If we are a live task by here request monitoring for
        # all interesting routes.
        if s.task.status not in ('New', 'Confirmed', 'Fix Released', 'Invalid'):
            s.bug.debs.monitor_routes(["Updates", "Security"])

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
