
from wfl.log                                    import center, cleave, cinfo, cdebug
from .base                                      import TaskHandler
from ktl.tracking_bug                           import TrackingBug

class PromoteToProposed(TaskHandler):
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

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._verify_promotion
        s.jumper['Triaged']       = s._verify_promotion
        s.jumper['In Progress']   = s._verify_promotion
        s.jumper['Fix Committed'] = s._verify_promotion

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        if s.bug.all_dependent_packages_fully_built:
            s.task.status = 'Confirmed'
            s.task.timestamp('started')
            retval = True

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _verify_promotion
    #
    def _verify_promotion(s):
        center(s.__class__.__name__ + '._verify_promotion')
        retval = False

        while True:

            # Check if packages were copied to the right pocket->component
            #
            if not s.bug.check_component_in_pocket('kernel-stable-Promote-to-proposed-end', 'proposed'):
                cinfo('            packages are not in -proposed', 'yellow')
                break

            # If there are derivative kernel packages based on this kernel package, create
            # the tracking bugs for them.
            #
            s._handle_derivatives()

            # If we've already been through here and already sent out the announcement
            # don't go through it again.
            #
            if 'proposed-announcement-sent' not in s.bug.bprops:
                s.bug.send_upload_announcement('proposed')
                s.bug.bprops['proposed-announcement-sent'] = True

            cinfo('    All components are now in -proposed', 'magenta')
            s.task.status = 'Fix Released'
            s.task.timestamp('finished')
            s.bug.phase = 'Promoted to proposed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._verify_promotion')
        return retval

    def _handle_derivatives(s):
        center(s.__class__.__name__ + '._handle_derivatives')
        return False

        derivative_packages = []
        record = s.ubuntu.lookup(s.bug.series)
        if 'derivative-packages' in record:
            if s.bug.pkg_name in record['derivative-packages']:
                derivative_packages = record['derivative-packages'][s.bug.pkg_name]

        backport_packages = []
        for entry in s.ubuntu.db.values():
            if 'backport-packages' in entry:
                bp_entries = entry['backport-packages']
                for bp_entry in iter(bp_entries):
                    if (bp_entries[bp_entry][0] == s.bug.pkg_name and bp_entries[bp_entry][1] == record['series_version']):
                        # For trusty and future backports we are changing the naming convention to
                        # be ~<series_version> instead of ~<series_name>.
                        #
                        if entry['name'] == 'precise':
                            backport_packages.append([bp_entry, "%s1" % entry['name']])             # precise backports are versioned <kernel-version>~precise1
                        else:
                            backport_packages.append([bp_entry, "%s.1" % entry['series_version']])  # post-precise lts backports are versioned <kernel-version>~<series-version>.1

        derivative_tracking_bugs = []
        backport_tracking_bugs   = []
        manual_tracking_bugs     = []

        tb = TrackingBug(s.lp.default_service, s.args.staging)
        for package in derivative_packages:
            cdebug('derivative package: %s' % package)
            if s.bug.dryrun:
                cinfo('Dryrun - Would open tracking bug for derivative package %s' % (package))
                continue

            bug = tb.open(package, '<version to be filled>', True, s.task.bug.id, s.bug.series)
            if bug:
                # Friendly comment on the bug stating that this is a derivative
                #
                msgder  = "This tracking bug was opened to be worked from "
                msgder += "%s-%s update (bug %s)" % (s.bug.pkg_name, s.bug.pkg_version, s.task.bug.id)
                subder  = "Derivative package tracking bug"
                bug.add_comment(msgder, subder)
                cinfo('        Action: Opened tracking bug %s for derivative package %s' % (bug.id, package))
                derivative_tracking_bugs.append([package, bug.id])
            else:
                manual_tracking_bugs  .append('%s' % (package))

        for package in backport_packages:
            cdebug('backport package: %s' % package)
            if s.bug.dryrun:
                cinfo('Dryrun - Would open tracking bug for backport package %s' % (package[0]))
                continue

            bug = tb.open(package[0], '%s~%s' % (s.bug.pkg_version, package[1]), s.has_new_abi(), s.task.bug.id)
            if bug:
                cinfo('        Action: Opened tracking bug %s for backport package %s (%s)' % (bug.id, package[0], package[1]))
                backport_tracking_bugs .append([package[0], package[1], bug.id])
            else:
                manual_tracking_bugs  .append('%s (%s)' % (package[0], package[1]))

        # comment about publishing and possible new tracking bugs opened
        #
        msgbody  = ''
        if derivative_tracking_bugs:
            msgbody += '\n\nDerivative packages from packages here can be worked on,'
            msgbody += ' the following tracking bugs were opened for them:'
            for pkg_bug in derivative_tracking_bugs:
                msgbody += '\n%s - bug %s' % (pkg_bug[0], pkg_bug[1])
        if backport_tracking_bugs :
            msgbody += '\n\nBackport packages from packages here can be worked on,'
            msgbody += ' the following tracking bugs were opened for them:'
            for pkg_bug in backport_tracking_bugs :
                msgbody += '\n%s (%s) - bug %s' % (pkg_bug[0], pkg_bug[1], pkg_bug[2])
        if manual_tracking_bugs  :
            msgbody += '\n\nIt was not possible to create or handle the'
            msgbody += ' tracking bugs for the following packages'
            msgbody += ' (their tracking bugs based on this update'
            msgbody += ' must be handled manually):'
            for ln in manual_tracking_bugs  :
                msgbody += '\n%s' % (ln)
        task = s.bug.tasks_by_name[s.projectname]
        s.bug.add_comment(task, 'Packages available', msgbody)

        cleave(s.__class__.__name__ + '._handle_derivatives')


# vi: set ts=4 sw=4 expandtab syntax=python
