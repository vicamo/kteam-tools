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
        s.jumper['Triaged']       = s._new
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Incomplete']    = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion
        s.jumper['Fix Released']  = s._recind

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

        # Identify the packages which are incomplete -- first step.
        for pocket in s.pockets_watch:
            delta = s.bug.debs.delta_src_dst(s.pocket_src, pocket)
            # If everything which is not fully published is in the pocket
            # this is the pocket for us.
            if s.bug.debs.delta_in_pocket(delta, pocket):
                break

        while not retval:
            task_src_ready = True
            for task_src in s.task_srcs:
                if s.bug.task_status(task_src) not in ('Fix Committed', 'Fix Released', 'Invalid'):
                    task_src_ready = False
            if not task_src_ready:
                break

            if not s.bug.debs.delta_in_pocket(delta, s.pocket_dest):
                break

            s.task.status = 'Fix Committed'
            s.task.timestamp('started')

            retval = True
            break

        while not retval:
            task_src_ready = True
            for task_src in s.task_srcs:
                if s.bug.task_status(task_src) not in ('Fix Released', 'Invalid'):
                    task_src_ready = False
            if not task_src_ready:
                break

            if not s.bug.debs.delta_built_pocket(delta, s.pocket_src):
                break

            if not s.bug.all_dependent_packages_published_tag:
                s.task.reason = 'Pending -- source package tags missing'
                break

            if s.bug.is_derivative_package:
                if not s.master_bug_ready_for_proposed():
                    s.task.reason = 'Holding -- master bug not ready for proposed'
                    break

            clear = True
            for pocket_dest, pockets_after in s.pockets_clear:
                if not s.bug.debs.pocket_clear(pocket_dest, pockets_after):
                    clear = False
                    break
            if not clear and not s._kernel_unblock_ppa():
                s.task.reason = 'Stalled -- another kernel is currently pending in {}'.format(pocket_dest)
                s.bug.refresh_at(datetime.now(timezone.utc) + timedelta(minutes=30),
                        '{}:{} waiting for {} to become clear'.format(s.bug.series, s.bug.name, pocket_dest))
                break

            older = s.bug.debs.older_tracker_in_proposed
            if older is not None:
                s.task.reason = 'Stalled -- tracker for earlier spin still active in Proposed'
                s.bug.monitor_add({
                    "type": "tracker-modified",
                    "watch": str(older)})
                break

            if s._kernel_block_ppa():
                s.task.reason = 'Stalled -- manual kernel-block/kernel-block-ppa present'
                break

            if s._cycle_hold():
                s.task.reason = 'Stalled -- cycle on hold'
                break

            # Record what is missing as we move to Confirmed.
            s.bug.bprops.setdefault('delta', {})[s.task.name] = delta
            s.bug.clamp_assign('promote-to-proposed', s.bug.debs.prepare_id)

            # If this was pre-approved and things are ready, then move it to in-progress
            # so it is not listed as needing manual review.
            if s.task.status == 'Triaged':
                s.task.status = 'In Progress'

            else:
                s.task.status = 'Confirmed'

            s.task.timestamp('started')

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

            pull_back = False
            if s._kernel_block_ppa():
                cinfo('            A kernel-block/kernel-block-ppa tag exists on this tracking bug pulling back from Confirmed', 'yellow')
                pull_back = True
            if s.bug.debs.older_tracker_in_proposed is not None:
                cinfo('            A previous spin tracker is active in proposed pulling back from Confirmed', 'yellow')
                pull_back = True
            if s._cycle_hold():
                cinfo('            Cycle on hold pulling back from Confirmed', 'yellow')
                pull_back = True

            if pull_back:
                s.task.status = 'New'
                retval = True

            break

        # Identify the packages which are incomplete.
        cdebug("promote-to-proposed: checking delta in {}".format(s.pockets_watch))
        for pocket in s.pockets_watch:
            delta = s.bug.debs.delta_src_dst(s.pocket_src, pocket)
            # If everything which is not fully published is in the pocket
            # this is the pocket for us.
            if s.bug.debs.delta_in_pocket(delta, pocket):
                break
        cdebug("promote-to-proposed: pocket={} delta={}".format(pocket, delta))

        while not retval:
            # Check if the packages are published completely yet.
            found = s.bug.debs.delta_in_pocket(delta, pocket)
            if not found:
                # Confirm the packages remain available to copy.
                if not s.bug.debs.delta_built_pocket(delta, s.pocket_src):
                    s.task.reason = 'Alert -- packages no longer available'
                    if s.task.status != 'Incomplete':
                        s.task.status = 'Incomplete'
                        retval = True
                    break

                if s.task.status == 'Confirmed':
                    state = s.task.reason_state('Pending', timedelta(hours=12))
                    s.task.reason = '{} -- ready for review'.format(state)
                    break

                elif s.task.status == 'Incomplete':
                    s.task.reason = 'Stalled -- review FAILED'
                    break

                elif s.task.status == 'In Progress':
                    s.task.reason = '{} -- review in progress'.format(
                        s.task.reason_state('Ongoing', timedelta(hours=4)))
                    break

            elif s.task.status not in ('Fix Committed', 'Incomplete'):
                s.task.status = 'Fix Committed'
                retval = True

            # If we are marked broken report this and hold.
            if s.task.status == 'Incomplete':
                s.task.reason = 'Stalled -- copy FAILED'
                break

            # If they are not all built ...
            lcl_delta = s.bug.debs.delta_src_dst(s.pocket_src, s.pocket_dest)
            if not s.bug.debs.delta_built_pocket(lcl_delta, s.pocket_dest):
                for pocket in s.pockets_watch:
                    lcl_delta = s.bug.debs.delta_src_dst(s.pocket_src, pocket)
                    failures = s.bug.debs.delta_failures_in_pocket(lcl_delta, pocket)
                    interesting = False
                    for failure in failures:
                        if failure != 'missing':
                            interesting = True
                            break
                    if interesting:
                        break
                state = s.task.reason_state('Ongoing', timedelta(hours=4))
                for failure in failures:
                    if failure not in ('building', 'depwait', 'failwait'):
                        state = 'Pending'
                reason = '{} -- packages copying to {}'.format(state, pocket)
                failures_text = s.bug.debs.failures_to_text(failures)
                if failures_text != '':
                    reason += ' (' + failures_text + ')'
                s.task.reason = reason
                break

            if s.pocket_dest == 'Proposed':
                # Wait for the debs to be in Proposed long enough, or for promote-to-as-proposed to publish
                # adequately.
                ptap_status = s.bug.task_status(':promote-to-as-proposed')
                if ptap_status == 'Fix Released':
                    pass

                elif ptap_status != 'Invalid':
                    s.task.reason = 'Ongoing -- waiting for packages to publish to as-proposed'
                    break

                elif not s.bug.debs.ready_for_testing:
                    s.task.reason = 'Ongoing -- packages waiting in -proposed for mirror sync'
                    break

                # Check if packages were copied to the right pocket->component
                # Only do this if we have a main package, as we need a package
                # as a key.
                pp_status = s.bug.task_status('prepare-package')
                if pp_status != 'Invalid':
                    (good, mis_lst) = s.bug.debs.check_component_in_pocket('kernel-stable-Promote-to-proposed-end', s.pocket_dest)
                else:
                    good = True

                # Not ready to check...
                if good is None:
                    s.task.reason = 'Ongoing -- waiting for publication to complete to check components'
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

        # If we are a live task by here request monitoring for
        # all interesting routes.
        if s.task.status not in ('New', 'Confirmed', 'Fix Released', 'Invalid'):
            s.bug.debs.monitor_routes([s.pocket_src])
            s.bug.debs.monitor_routes(s.pockets_watch)

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval

    # _recind
    #
    def _recind(s):
        center(s.__class__.__name__ + '._recind')
        retval = False

        # XXX: TRANSITION
        clamp = s.bug.clamp('promote-to-proposed')
        if clamp is None:
            s.bug.clamp_assign('promote-to-proposed', s.bug.debs.prepare_id)

        clamp = s.bug.clamp('promote-to-proposed')
        if clamp is not None and str(clamp) != str(s.bug.debs.prepare_id):
            cinfo("promote-to-proposed id has changed, recinding promote-to-proposed")
            s.task.status = 'New'
            retval = True

        cleave(s.__class__.__name__ + '._recind (%s)' % retval)
        return retval

    @property
    def via_signing(s):
        has_signables = False
        for task_name in s.bug.tasks_by_name:
            if task_name.startswith('prepare-package-'):
                pkg = task_name.replace('prepare-package-', '')
                if (s.bug.debs.signing_package_for(pkg) and
                        s.bug.tasks_by_name[task_name].status != 'Invalid'):
                    has_signables = True

        cinfo("via_signing: routing={} has_signables={}".format(
            s.bug.debs.routing('Signing') is not None, has_signables))

        return s.bug.debs.routing('Signing') is not None and has_signables

    @property
    def signing_bot(s):
        return 'kernel-signing-bot' in s.bug.tags


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

        s.task_srcs = ['boot-testing', 'sru-review']
        s.pocket_src = 'ppa'
        s.pockets_clear = []
        s.pockets_watch = []
        if s.signing_bot and s.via_signing:
            cinfo("mode=canonical-signing-bot")
            s.pocket_dest = 'Proposed'
            s.pockets_clear.append(('Signing', ['Proposed', 'Release/Updates']))
            s.pockets_watch.append('Proposed')
            s.pockets_watch.append('Signing')
        elif s.via_signing:
            cinfo("mode=indirect-via-signing")
            s.pocket_dest = 'Signing'
            s.pockets_clear.append(('Signing', ['Proposed', 'Release/Updates']))
            s.pockets_watch.append('Signing')
        else:
            cinfo("mode=direct")
            s.pocket_dest = 'Proposed'
            s.pockets_watch.append('Proposed')
        s.pockets_clear.append(('Proposed', ['Release/Updates']))

        # If we have no source pocket, then there can be nothing to copy.
        if s.bug.debs.routing(s.pocket_src) is None:
            cinfo("prepare-package invalid with no source routing")
            s.pocket_src = None

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

        s.task_srcs = ['promote-to-proposed']
        s.pockets_clear = []
        s.pockets_watch = []
        if not s.signing_bot and s.via_signing:
            s.pocket_src = 'Signing'
            s.pocket_dest = 'Proposed'
            s.pockets_clear.append(('Proposed', ['Release/Updates']))
            s.pockets_watch.append('Proposed')
        else:
            s.pocket_src = None
            s.pocket_dest = None
            s.pockets_after = None

        cleave(s.__class__.__name__ + '.__init__')

# vi: set ts=4 sw=4 expandtab syntax=python
