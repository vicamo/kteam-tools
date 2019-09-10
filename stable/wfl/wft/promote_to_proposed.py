from datetime                           import datetime, timezone, timedelta

from wfl.log                            import center, cleave, cinfo, cdebug
from .promoter                          import Promoter


class PromoteFromTo(Promoter):
    '''
    A Task Handler for the promote-to-proposed/promote-signed-to-proposed task.

    States:

        - New:
            As soon as all packages, main, meta, signed, etc. have been built
            move this to Confirmed so an AA can copy the packages to -proposed.

        - Confirmed / Triaged / In Progress / Fix Committed
            When we verify that all components have been copied to -proposed
            we send out our announcements and then can mark this task as
            Fix Released

        - Fix Released
            We don't process when in this state. We're done.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteFromTo, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Incomplete']    = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            # If we are not required then initialisation phase will leave us
            # with not pockets.  In this case we are a noop, close ourselves
            # out now.
            if s.pocket_src is not None:
                break

            s.task.status = 'Invalid'

            retval = True
            break

        while not retval:
            if not s.bug.debs.all_in_pocket(s.pocket_dest):
                break

            s.task.status = 'Fix Committed'
            s.task.timestamp('started')

            s._add_block_proposed()

            retval = True
            break

        while not retval:
            if not s.bug.debs.all_in_pocket(s.pocket_src):
                break

            if not s.bug.debs.all_built_and_in_pocket(s.pocket_src):
                # Report PPA build status because there are no other open tasks monitoring
                # that segment.  For signing -> proposed the promote-to-proposed task is
                # already monitoring in its destination before closing.
                if s.pocket_src == 'ppa':
                    failures = s.bug.debs.all_failures_in_pocket(s.pocket_src)
                    state = 'Ongoing'
                    for failure in failures:
                        if not failure.endswith(':building') and not failure.endswith(':depwait'):
                            state = 'Pending'
                    reason = '{} -- builds not complete in {}'.format(state, s.pocket_src)
                    if failures is not None:
                        reason += ' ' + ','.join(failures)
                    s.task.reason = reason
                break

            if not s.bug.all_dependent_packages_published_tag:
                s.task.reason = 'Pending -- source package tags missing'
                break

            if 'boot-testing-requested' not in s.bug.bprops:
                s.bug.debs.send_boot_testing_requests()
                s.bug.bprops['boot-testing-requested'] = True

            if s.bug.is_derivative_package:
                if not s.master_bug_ready_for_proposed():
                    s.task.reason = 'Holding -- master bug not ready for proposed'
                    break

            if (not s.bug.debs.pocket_clear(s.pocket_dest, s.pocket_after) and
                not s._kernel_unblock_ppa()):
                s.task.reason = 'Stalled -- another kernel is currently pending in {}'.format(s.pocket_dest)
                break

            if s._kernel_block_ppa():
                s.task.reason = 'Holding -- manual kernel-block/kernel-block-ppa present'
                break
            if s._cycle_hold():
                s.task.reason = 'Holding -- cycle on hold'
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')

            s._add_block_proposed()

            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _verify_promotion
    #
    def _verify_promotion(s):
        center(s.__class__.__name__ + '._verify_promotion')
        retval = False

        while not retval:
            if s.task.status not in ('Confirmed'):
                break
            if not s._kernel_block_ppa() and not s._cycle_hold():
                break

            if s._kernel_block_ppa():
                cinfo('            A kernel-block/kernel-block-ppa tag exists on this tracking bug pulling back from Confirmed', 'yellow')
            if s._cycle_hold():
                cinfo('            Cycle on hold pulling back from Confirmed', 'yellow')

            s.task.status = 'New'

            retval = True
            break

        while not retval:
            if s.task.status in ('Fix Committed', 'Incomplete'):
                break

            if not s.bug.debs.all_in_pocket(s.pocket_dest):
                break

            s.task.status = 'Fix Committed'

            retval = True
            break

        while not retval:
            # Check if the packages are published completely yet.
            if not s.bug.debs.all_in_pocket(s.pocket_dest):
                # Confirm the packages remain available to copy.
                if not s.bug.debs.all_built_and_in_pocket(s.pocket_src):
                    s.task.reason = 'Alert -- packages no longer available'
                    if s.task.status != 'Incomplete':
                        s.task.status = 'Incomplete'
                        retval = True
                    break

                if s.task.status == 'Confirmed':
                    state = s.task.reason_state('Pending', timedelta(hours=12))
                    s.task.reason = '{} -- ready for review'.format(state)
                elif s.task.status == 'Incomplete':
                    s.task.reason = 'Stalled -- review FAILED'
                elif s.task.status == 'Fix Committed':
                    failures = s.bug.debs.all_failures_in_pocket(s.pocket_dest)
                    state = s.task.reason_state('Ongoing', timedelta(hours=4))
                    for failure in failures:
                        if not failure.endswith(':building') and not failure.endswith(':depwait'):
                            state = 'Pending'
                    reason = '{} -- package copies requested to {}'.format(state, s.pocket_dest)
                    if failures is not None:
                        reason += ' ' + ','.join(failures)
                    s.task.reason = reason
                else:
                    s.task.reason = '{} -- review in progress'.format(
                        s.task.reason_state('Ongoing', timedelta(hours=4)))
                break
            if not s.bug.debs.all_built_and_in_pocket(s.pocket_dest):
                failures = s.bug.debs.all_failures_in_pocket(s.pocket_dest)
                state = 'Ongoing'
                for failure in failures:
                    if not failure.endswith(':building') and not failure.endswith(':depwait'):
                        state = 'Pending'
                reason = '{} -- package copied to {}'.format(state, s.pocket_dest)
                if failures is not None:
                    reason += ' ' + ','.join(failures)
                s.task.reason = reason
                break
            if s.pocket_dest == 'Proposed':
                if not s.bug.debs.ready_for_testing:
                    s.task.reason = 'Ongoing -- packages waiting in -proposed for mirror sync'
                    break

                # Check if packages were copied to the right pocket->component
                #
                (good, mis_lst) = s.bug.debs.check_component_in_pocket('kernel-stable-Promote-to-proposed-end', s.pocket_dest)
                # Not ready to check...
                if good is None:
                    cinfo('        packages not ready to check components')
                    break

                # Checked as bad.
                elif good is False:
                    s.task.reason = 'Stalled -- packages are in the wrong component'
                    # NOTE: when we update components the package will be republished
                    # which triggers swm-publishing to detect it automatically so we avoid
                    # the need to request a refresh_at.

                    cinfo('checking %s task status is %s' % (s.task.name, s.task.status))
                    if s.task.status != 'Incomplete':
                        s.task.status = 'Incomplete'
                        retval = True

                        body  = "The following packages ended up in the wrong"
                        body += " component in the %s pocket:\n" % (s.pocket_dest)
                        for item in mis_lst:
                            cdebug('%s %s - is in %s instead of %s' % (item[0], item[1], item[2], item[3]), 'green')
                            body += '\n%s %s - is in %s instead of %s' % (item[0], item[1], item[2], item[3])

                        subject = '[ShankBot] [bug %s] Packages copied to the wrong component' % (s.bug.lpbug.id)
                        to_address  = "kernel-team@lists.ubuntu.com"
                        to_address += ", ubuntu-installer@lists.ubuntu.com"
                        cinfo('        sending email alert')
                        s.bug.send_email(subject, body, to_address)

                        body += "\n\nOnce this is fixed, set the "
                        body += "%s to Fix Released again" % (s.task.name)
                        s.bug.add_comment('Packages outside of proper component', body)

                    cinfo('        packages ended up in the wrong pocket')
                    break

                # If we've already been through here and already sent out the announcement
                # don't go through it again.
                #
                if 'proposed-announcement-sent' not in s.bug.bprops:
                    if not s.bug.source.private:
                        s.bug.send_upload_announcement('proposed')
                    s.bug.bprops['proposed-announcement-sent'] = True
                if 'proposed-testing-requested' not in s.bug.bprops:
                    s.bug.debs.send_proposed_testing_requests()
                    s.bug.bprops['proposed-testing-requested'] = True

            cinfo('    All components are now in -proposed', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')

            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval


class PromoteToProposed(PromoteFromTo):
    '''
    A Task Handler for the promote-to-proposed task.

    States:

        - New:
            As soon as all packages, main, meta, signed, etc. have been built
            move this to Confirmed so an AA can copy the packages to -proposed.

        - Confirmed / Triaged / In Progress / Fix Committed
            When we verify that all components have been copied to -proposed
            we send out our announcements and then can mark this task as
            Fix Released

        - Fix Released
            We don't process when in this state. We're done.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteToProposed, s).__init__(lp, task, bug)

        s.pocket_src = 'ppa'
        if (s.bug.debs.routing('Signing') and
                'prepare-package-signed' in s.bug.tasks_by_name and
                s.bug.tasks_by_name['prepare-package-signed'] != 'Invalid'):
            s.pocket_dest = 'Signing'
            s.pocket_after = 'Proposed'
        else:
            s.pocket_dest = 'Proposed'
            s.pocket_after = 'Release/Updates'
        cdebug("promote-to-proposed: pocket_dest={}".format(s.pocket_dest))

        cleave(s.__class__.__name__ + '.__init__')


class PromoteSigningToProposed(PromoteFromTo):
    '''
    A Task Handler for the promote-signing-to-proposed task.

    States:

        - New:
            As soon as all packages, main, meta, signed, etc. have been built
            move this to Confirmed so an AA can copy the packages to -proposed.

        - Confirmed / Triaged / In Progress / Fix Committed
            When we verify that all components have been copied to -proposed
            we send out our announcements and then can mark this task as
            Fix Released

        - Fix Released
            We don't process when in this state. We're done.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PromoteSigningToProposed, s).__init__(lp, task, bug)

        if (s.bug.debs.routing('Signing') and
                'prepare-package-signed' in s.bug.tasks_by_name and
                s.bug.tasks_by_name['prepare-package-signed'] != 'Invalid'):
            s.pocket_src = 'Signing'
            s.pocket_dest = 'Proposed'
            s.pocket_after = 'Release/Updates'
        else:
            s.pocket_src = None
            s.pocket_dest = None
            s.pocket_after = None

        cleave(s.__class__.__name__ + '.__init__')

# vi: set ts=4 sw=4 expandtab syntax=python
