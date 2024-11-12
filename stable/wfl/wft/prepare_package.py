from datetime                           import datetime, timedelta, timezone

from wfl.log                                    import center, cleave, cdebug, cinfo
from .base                                      import TaskHandler


class PreparePackage(TaskHandler):
    '''
    A Task Handler for the prepare-package task.

    States:

        - New
            Just move straight to Confirmed.

        - Confirmed / Triaged / In Progress / Fix Committed
            Keep checking for when all the packages are fully built. When
            they are, move this task to Fix Released

        - Fix Released
            We don't process when in this state. We're done.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(PreparePackage, s).__init__(lp, task, bug)

        # The tracking bug should start this task out as 'Confirmed'
        # for primary packages.  Derivatives should flip to 'Confirmed'
        # as soon as their primary is uploaded.
        #
        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._common
        s.jumper['Triaged']       = s._common
        s.jumper['In Progress']   = s._common
        s.jumper['Fix Committed'] = s._common
        s.jumper['Fix Released']  = s._complete

        cleave(s.__class__.__name__ + '.__init__')

    # evaluate_state
    #
    def evaluate_status(s, state):
        # We ARE aware of invalid bugs ... but need a valid package.
        if not s.bug.has_package:
            return False
        return s.jumper[state]()

    # _package_name
    #
    def _package_name(s):
        pkg = s.task.name.replace('prepare-package', '').replace('-', '')
        if pkg == '':
            pkg = 'main'
        return pkg

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')

        retval = False
        while True:
            # Since all the Prepare-package* packagestasks use this same method
            # we need to determine which one we are working this time.
            pkg = s._package_name()

            # Confirm whether this package is actually valid.
            if not s.bug.valid_package(pkg):
                s.task.status = 'Invalid'
                cdebug("prepare: mark invalid")
                retval = True
                break

            # Are we blocked.
            block = s.bug.source_block_present()
            if block is not None:
                cdebug("prepare: blocked")
                break

            # For derivative bugs we wait until the parent has at least got its
            # primary package uploaded.  Then we must have something we _could_
            # rebase on.
            if not s.bug.debs.ready_to_prepare():
                if pkg == 'main' or not s.bug.valid_package('main'):
                    s.task.reason = 'Holding -- waiting for parent tracker'
                cdebug("prepare: not read to prepare")
                break

            # Check for blocking trackers in a previous cycle.
            if s.bug.debs.older_tracker_in_ppa:
                cdebug("prepare: older tracker in PPA")
                break
            if s.bug.master_bug is not None and s.bug.debs.older_tracker_unprepared:
                cdebug("prepare: older tracker unprepared")
                break

            # If we are not the primary-package and there is a primary package
            # If we are not the primary-package and there is a primary package
            # hold us until the primary is handled, this keeps the todo list
            # short and sweet.  The very first thing we need to do is to set
            # the kernel version, so hold secondary packages pending that.
            if (pkg != 'main' and s.bug.valid_package('main') and
                not s.bug.is_valid
               ):
                cdebug("prepare primary: {} {} {}".format(pkg, s.bug.valid_package('main'), not s.bug.is_valid))
                retval = False
                break

            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _common
    #
    def _common(s):
        '''
        Look to see if the packages have been fully built. This is our indication that the
        packages have been prepared and we can close this task.
        '''
        center(s.__class__.__name__ + '._common')
        retval = False

        while not retval:
            if s.task.status not in ('Confirmed'):
                break

            # Announce (and reannounce) this every day.
            s.task.bug.announce_drip(
                "swm-transition-crankable",
                subject="@{owner} [LP#{id}](https://launchpad.net/bugs/{id}) {cycle} {series}:{source} crankable".format(
                    owner=s.bug.owner,
                    id=s.task.bug.lpbug.id,
                    cycle=s.task.bug.sru_spin_name,
                    series=s.task.bug.series,
                    source=s.task.bug.name,
                ),
                every=timedelta(hours=24),
                since=s.task.date_confirmed,
            )

            pull_back = False
            block = s.bug.source_block_present()
            if block is not None:
                cinfo('            Blocked via {} pulling back from Confirmed'.format(block), 'yellow')
                pull_back = True
            if not s.bug.debs.ready_to_prepare():
                cinfo('            Master kernel no longer ready pulling back from Confirmed', 'yellow')
                pull_back = True
            if s.bug.debs.older_tracker_in_ppa:
                cinfo('            A previous cycle tracker is in PPA pulling back from Confirmed', 'yellow')
                pull_back = True
            if s.bug.master_bug is not None and s.bug.debs.older_tracker_unprepared:
                cinfo('            A previous cycle tracker is unprepared pulling back from Confirmed', 'yellow')
                pull_back = True

            if pull_back:
                s.task.status = 'New'
                retval = True

            break

        while not retval:

            # If we do not have a version then whine about that.
            if not s.bug.is_valid:
                s.task.reason = 'Pending -- version not specified'
                break

            # Since all the Prepare-package* packagestasks use this same method
            # we need to determine which one we are working this time.
            #
            pkg = s._package_name()

            # Confirm whether this package is actually valid
            if not s.bug.valid_package(pkg):
                s.task.status = 'Invalid'
                retval = True
                break

            # We have a version so we are at least In Progress.
            # NOTE: we do not break so we can upgrade to later states.
            if s.task.status not in ('In Progress', 'Fix Committed'):
                s.task.status = 'In Progress'
                retval = True

            creator = None

            # Keep track of whether we had any versions before we started.
            versions_present = 'versions' in s.bug.bprops

            # Check the package tag has been published -- this may populate versions.
            tag_present = s.bug.published_tag(pkg)

            # If we have a ppa route, then we should check these packages were
            # uploaded.  Default to present when we are source-only.
            upload_present = True
            if s.bug.debs.routing('ppa'):
                # Confirm that this package is uploaded.
                upload_present = s.bug.debs.uploaded(pkg)
                if not upload_present:
                    pkg_for = s.bug.debs.generate_package_for(pkg)
                    if pkg_for:
                        upload_present = s.bug.debs.signed(pkg_for)
                if upload_present:
                    # If we have any uploads create an empty versions dictionary
                    # which will escalate all miss messages.
                    if 'versions' not in s.bug.bprops and s.bug.debs.uploaded(pkg):
                        s.bug.bprops['versions'] = {}

                    # If we have uploaded packages we have a creator.
                    creator = s.bug.debs.creator(pkg)

            if tag_present and upload_present:
                # We have uploads and tags so we are at least Fix Committed.
                # NOTE: we do not break so we can upgrade to later states.
                if s.task.status != 'Fix Committed':
                    s.task.status = 'Fix Committed'
                    try:
                        s.task.assignee = creator
                    except KeyError:
                        # It doesn't matter if we set the assignee, that's just a nice
                        # to have.
                        #
                        pass
                    retval = True

            # If we created the versions dictionary then we need to trigger a recrank.
            if not versions_present and 'versions' in s.bug.bprops:
                retval = True

            # If we are missing tags or uploads report same.
            if not tag_present or not upload_present:
                reason_state = 'Stalled' if 'versions' in s.bug.bprops else 'Pending'
                missing = []
                if not tag_present:
                    missing.append('tag not published')
                if not upload_present:
                    missing.append('package not uploaded')
                s.task.reason = '{} -- {}'.format(reason_state, ' and '.join(missing))
                if s.task.status == 'Fix Committed':
                    s.task.status = 'In Progress'
                    retval = True
                break

            # If we have a ppa route, then we should check these packages were
            # uploaded.
            if s.bug.debs.routing('ppa'):
                # Hold prepare-package open until the package is built, or the packages
                # which would have depended on us are past signing (as we must have existed).
                if not s.bug.debs.built_and_in_pocket_or_after(pkg, 'ppa'):
                    pkg_for = s.bug.debs.generate_package_for(pkg)
                    for_present = False
                    if pkg_for:
                        for_present = s.bug.debs.signed(pkg_for)
                    if not for_present:
                        s.task.reason = 'Ongoing -- {} package not yet fully built'.format(pkg)
                        break

            # If we have a no ppa route, then we should consider duplicates now.
            if not s.bug.debs.routing('ppa'):
                s.bug.dup_replaces()

            # If we have ppa routing then we should check binaries.
            if pkg == "meta" and s.bug.debs.routing('ppa'):
                s.bug.debs.meta_check()

            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            try:
                if creator is not None:
                    s.task.assignee = creator
            except KeyError:
                # It doesn't matter if we set the assignee, that's just a nice
                # to have.
                #
                pass

            retval = True
            break

        cleave(s.__class__.__name__ + '._common (%s)' % (retval))
        return retval

    # _complete
    #
    def _complete(s):
        '''
        Until such time as promote-to-proposed reacts and moves out of
        New we should consider whether our package is still present.  If
        not move back to In Progress.
        '''
        center(s.__class__.__name__ + '._complete')
        retval = False

        while not retval:
            # If promote-to-proposed has not yet gone active there could be an
            # issue with this task.
            ptps = s.bug.task_status('promote-to-proposed')
            if ptps != 'New':
                break

            pkg = s._package_name()

            # Confirm that this package remains uploaded.
            upload_present = s.bug.debs.uploaded(pkg)
            if upload_present:
                break

            # If we are a generate package for another package then we may
            # consider the package as present (in absence) if our signing
            # result is so present.
            pkg_for = s.bug.debs.generate_package_for(pkg)
            if pkg_for:
                upload_present = s.bug.debs.signed(pkg_for)
                if upload_present:
                    break

            # The package is no longer found in the build route, this
            # means we cannot any longer claim to be prepared.  Pull
            # back to In Progress which will throw tag/upload missing
            # as appropriate into the status and onto the dashboard.
            s.task.status = 'In Progress'
            retval = True
            break

        cleave(s.__class__.__name__ + '._complete (%s)' % (retval))
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
