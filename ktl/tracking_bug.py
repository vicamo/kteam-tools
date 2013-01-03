#!/usr/bin/env python
#

from ktl.workflow                       import Workflow
from ktl.ubuntu                         import Ubuntu
from ktl.utils                          import date_to_string
from datetime                           import datetime
import re

class TrackingBug:

    def __init__(self, lp, staging):
        self.lp = lp
        self.staging = staging

    def open(self, package, version, new_abi, master_bug, der_series = None):
        wf = Workflow()
        ub = Ubuntu()

        # For the given version, figure out the series.
        # If we can't find the series, don't continue.
        #
        series_target = None
        series = der_series
        if not der_series:
            series = ub.series_name(package, version)
        if series:
            lp = self.lp.launchpad
            ubuntu = lp.distributions["ubuntu"]
            sc = ubuntu.series_collection
            for s in sc:
                if s.name == series:
                    series_target = s
                    break
        if not series_target:
            raise Exception("%s-%s: can't figure out the distro series for it."
                            % (package, version))
        devel_series = ub.is_development_series(series)

        # Title: <package>: <version> -proposed tracker
        title = "%s: %s -proposed tracker" % (package, version)

        # Description:
        #    This bug is for tracking the <version> upload package. This bug will
        #    contain status and testing results related to that upload.
        #
        description  = "This bug is for tracking the %s upload package. " % (version)
        description += "This bug will contain status and testing results related to "
        description += "that upload."
        description += "\n\n"
        description += "For an explanation of the tasks and the associated workflow see:"
        description += " https://wiki.ubuntu.com/Kernel/kernel-sru-workflow\n"

        # Add new properties to the description
        now = datetime.utcnow()
        now.replace(tzinfo=None)
        tstamp = date_to_string(now)
        ourprops = {}
        prop_pfx = 'kernel'
        if not devel_series:
            prop_pfx += '-stable'
        ourprops['%s-Prepare-package-start' % (prop_pfx)] = tstamp
        ourprops['%s-phase' % (prop_pfx)] = 'Prepare'
        ourprops['%s-phase-changed' % (prop_pfx)] = tstamp
        if master_bug:
            ourprops['%s-master-bug' % (prop_pfx)] = master_bug
        for k in ourprops:
            description = description + '%s:%s\n' % (k, ourprops[k])

        bug = self.lp.create_bug(project='ubuntu', package=package, title=title, description=description)

        id = bug.id
        if self.staging:
            print("https://bugs.qastaging.launchpad.net/bugs/%s" % (id))
        else:
            print("https://bugs.launchpad.net/bugs/%s" % (id))

        # Tags:
        #    add all tags for this package name
        taglist = wf.initial_tags(package, devel_series)
        for itag in taglist:
            bug.tags.append(itag)

        # Get the one task and modify the status and importance.
        #
        for task in bug.tasks:
            task.status = "In Progress"
            task.importance = "Medium"
            break

        # Teams / individuals to be automatically subscribed to the tracking bugs
        #   These vary per package
        #
        teams = wf.subscribers(package, devel_series)
        for team in teams:
            try:
                lp_team = self.lp.launchpad.people[team]
            except KeyError:
                print("Can't subscribe '%s', team not found in Launchpad!" % (team))
                continue
            bug.lpbug.subscribe(person=lp_team)

        # Nominate the series for this package.
        #
        nomination = bug.lpbug.addNomination(target=series_target)
        if nomination.canApprove():
            nomination.approve()
        bug.tags.append(series)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Add a task for kernel-sru-workflow and then nominate all the series that belong
        # to that project.
        #

        lp = self.lp.launchpad
        ubuntu = lp.distributions["ubuntu"]
        if devel_series:
            project = 'kernel-development-workflow'
        else:
            project = 'kernel-sru-workflow'
        proj = lp.projects[project]
        bug.lpbug.addTask(target=proj)

        # check the need for dependent packages tasks
        has_lbm = False
        has_lrm = False
        has_lum = False
        has_meta = False
        has_ports_meta = False
        has_signed = False
        try:
            found = ub.lookup(series)
        except KeyError:
            found = {}
        if found:
            if 'dependent-packages' in found:
                for dep in iter(found['dependent-packages']):
                    if dep == package:
                        has_lbm = 'lbm' in found['dependent-packages'][dep]
                        has_lrm = 'lrm' in found['dependent-packages'][dep]
                        has_lum = 'lum' in found['dependent-packages'][dep]
                        has_meta = 'meta' in found['dependent-packages'][dep]
                        has_ports_meta = 'ports-meta' in found['dependent-packages'][dep]
                        has_signed = 'signed' in found['dependent-packages'][dep]
                        break

        sc = proj.series_collection
        for s in sc:
            if s.active and s.name not in ['trunk', 'latest']:
                if s.name == 'upload-to-ppa' and not der_series:
                    continue
                if s.name == 'prepare-package-lbm' and not has_lbm:
                    continue
                if s.name == 'prepare-package-lrm' and not has_lrm:
                    continue
                if s.name == 'prepare-package-lum' and not has_lum:
                    continue
                if s.name == 'prepare-package-meta' and not has_meta:
                    continue
                if s.name == 'prepare-package-ports-meta' and not has_ports_meta:
                    continue
                if s.name == 'prepare-package-signed' and not has_signed:
                    continue
                nomination = bug.lpbug.addNomination(target=s)
                if nomination.canApprove():
                    nomination.approve()

        # Task assignments
        # Set status of the master task so the bot will start processing
        #
        for t in bug.tasks:
            task       = t.bug_target_display_name
            parts = task.partition(proj.display_name)
            if parts[0] == '' and parts[1] == proj.display_name and parts[2] == '':
                t.status = "In Progress"
            else:
                if parts[0] != '':
                    continue
                task = parts[2].strip()
                assignee = wf.assignee(package, task, devel_series)
                if assignee is None:
                    print 'Note: Found a workflow task named %s with no automatic assignee, leaving unassigned and setting to invalid' % task
                    t.status = "Invalid"
                else:
                    try:
                        t.assignee = self.lp.launchpad.people[assignee]
                    except KeyError:
                        print("Can't assign '%s', team not found in Launchpad!" % (assignee))
                    lin_ver = re.findall('([0-9]+\.[^-]+)', version)
                    if lin_ver:
                        lin_ver = lin_ver[0]
                        if not devel_series and wf.is_task_invalid(package, task, lin_ver):
                            t.status = "Invalid"
                            continue
                    if not new_abi and task.startswith('prepare-package-'):
                        t.status = "Invalid"

        return bug

# vi:set ts=4 sw=4 expandtab:
