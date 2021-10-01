#!/usr/bin/env python
#
from datetime                           import datetime, timedelta, timezone
from textwrap                           import fill
import yaml
import re
from ktl.utils                          import date_to_string, string_to_date
from .log                               import cdebug, center, cleave, cinfo, cerror
from .package                           import Package, PackageError
from ktl.shanky                         import send_to_shankbot
from .errors                            import ShankError, WorkflowCrankError, WorkflowCorruptError
from .deltatime                         import DeltaTime
from .snap                              import SnapDebs, SnapError
from .task                              import WorkflowBugTask, WorkflowBugTaskSynPersistent, WorkflowBugTaskSynPreparePackages
from .swm_config                        import SwmConfig
from .git_tag                           import GitTag, GitTagError
from .context                           import ctx


# WorkflowBugError
#
class WorkflowBugError(ShankError):
    '''
    Thrown when some goes wrong with the WorkflowBug (e.g. when trying to
    process a non-existing bug).
    '''
    pass


# WorkflowBug
#
class WorkflowBug():
    '''
    A helper class. Tries to encapsulate most of the common methods for working with the
    workflow bug.
    '''
    projects_tracked  = ['kernel-development-workflow', 'kernel-sru-workflow']
    dryrun            = False
    no_assignments    = False
    no_announcements  = False
    sauron            = False
    no_timestamps     = False
    no_status_changes = False
    no_phase_changes  = False
    local_msgqueue_port = None

    # __init__
    #
    def __init__(s, lp, bugid=None, bug=None, manager=None):
        '''
        When instantiated the bug's title is processed to find out information about the
        related package. This information is cached.
        '''
        s.lp = lp
        if bug is not None:
            s.lpbug = bug

        elif bugid is not None:
            try:
                s.lpbug = s.lp.get_bug(bugid)
            except KeyError:
                s.is_valid = False
                cdebug('Failed to get bug #%s' % bugid, 'red')
                raise WorkflowBugError('Invalid bug number %s' % bugid)

        else:
                raise WorkflowBugError('bug or bugid required')

        s.tracker_modified = False
        s.tracker_instantiated = datetime.utcnow()

        # Pass along any "global" settings to the WorkflowBugTask.
        #
        WorkflowBugTask.dryrun = WorkflowBug.dryrun
        WorkflowBugTask.no_status_changes = WorkflowBug.no_status_changes
        WorkflowBugTask.no_assignments = WorkflowBug.no_assignments
        WorkflowBugTask.no_timestamps = WorkflowBug.no_timestamps

        s.manager = manager

        s.error = None
        s.title = s.lpbug.title
        s._tags = None
        s.bprops = s.load_bug_properties()
        s.reasons = {}
        s._refresh = [None, None]
        s._monitor = []
        s._maintenance = []
        s.interlocks = {}
        s.blockers = None
        s.stage = None
        s.is_development_series = False
        s._master_bug = False
        s._sru_spin = False
        s.is_valid = True
        s._target_trackers = None
        s.debs = None
        s.snap = None
        s.tasks_by_name = {}

        # If a bug isn't to be processed, detect this as early as possible.
        #
        s.check_is_valid()
        if not s.is_workflow:
            raise WorkflowBugError('Bug is not a workflow bug')
        s.properties = s.lpbug.properties

        # If this tracker is_closed drop out quietly and quickly.
        if s.is_gone:
            return

        # Early error, blow this joint.
        if s.error is not None:
            s.is_crankable = False
            return

        # Instantiate this variant.
        try:
            s.debs = None
            if s.variant in ('debs', 'combo'):
                s.debs = Package(s)
            s.snap = None
            if s.variant in ('snap-debs', 'combo'):
                s.snap = SnapDebs(s)
                # For a combo bug clear out the SnapDebs object if we have
                # no primary snap defined.
                if s.variant == 'combo' and s.snap.snap_info is None:
                    s.snap = None
        # XXX: should be a VariantError or something.
        except (PackageError, SnapError) as e:
            s.debs = None
            s.error = WorkflowCrankError(e.args[0])

        # If we have no series/package/source by now we are dead in the
        # water kill this bug hard.
        if s.name is None:
            s.error = WorkflowCrankError('Package not identified from title')
        elif s.series is None:
            s.error = WorkflowCrankError('Series not identified from tags')
        elif s.source is None:
            s.error = WorkflowCrankError('Source not found in kernel-series')

        # Primary data consistency issue, out of here; caller will raise
        # error when it is convienient.
        if s.error is not None:
            s.is_crankable = False
            return

        s.is_development_series = s.source.series.development
        s.is_development = s.source.development or s.sru_cycle[0] == 'd'

        # If we have no version after instantiation of the variant,
        # this is not generally crankable.
        if s.version is None:
            s.is_valid = False

        cinfo('                    variant: "{}"'.format(s.variant), 'blue')
        cinfo('                      title: "{}"'.format(s.title), 'blue')
        cinfo('                   is_valid: {}'.format(s.is_valid), 'blue')
        cinfo('                is_workflow: {}'.format(s.is_workflow), 'blue')
        cinfo('                       name: "{}"'.format(s.name), 'blue')
        cinfo('                    version: "{}"'.format(s.version), 'blue')
        cinfo('                     series: "{}"'.format(s.series), 'blue')
        cinfo('      is development series: {}'.format(s.is_development_series), 'blue')

        if s.debs is not None:
            for p in s.debs.pkgs:
                cinfo('                        package: "{}"'.format(p), 'blue')

        if s.is_derivative_package:
            cinfo('                 derivative: yes ({})'.format(s.master_bug_id), 'blue')
        else:
            cinfo('                 derivative: no', 'blue')
        cinfo('')

        cinfo('    Targeted Project:', 'cyan')
        cinfo('        {}'.format(s.workflow_project), 'magenta')
        cinfo('')
        props_dump = yaml.safe_dump(s.bprops, default_flow_style=False).strip().split('\n')
        if len(props_dump) > 0:
            cinfo('    SWM Properties:', 'cyan')
            for prop in props_dump:
                cinfo('        {}'.format(prop), 'magenta')

        s.tasks_by_name = s._create_tasks_by_name_mapping()

        if 'versions' in s.bprops and 'source' in s.bprops['versions'] and s.bprops['versions']['source'] != s.version:
            cinfo("tracker version has changed dropping package version data")
            del s.bprops['versions']

            # XXX: task reset should be a task thing.  But we have no "old" version
            #      at the package level.
            for taskname, task in s.tasks_by_name.items():
                if (taskname.startswith('prepare-package') or 
                        taskname == 'sru-review'):
                    task.status = 'New'

    @property
    def sc(self):
        return ctx.sc

    @property
    def kernel_series(self):
        return ctx.ks

    def version_from_title(s):
        (s.series, s.name, s.version, s.source, s.kernel, s.abi) = (None, None, None, None, None, None)

        # XXX: when the data moved to swm-properties this is where we would
        #      pick those out.

        s.__title_decode()

    def version_from_master(s):
        # XXX: when the data moved to swm-properties this is where we would
        #      pick those out.

        master_bug = s.master_bug
        if master_bug is None:
            raise WorkflowBugError("Master bug required")
        s.series = master_bug.series
        s.name = master_bug.name
        s.version = master_bug.version
        s.source = master_bug.source
        s.kernel = master_bug.kernel
        s.abi = master_bug.abi

    def update_title(s, suffix='-proposed tracker'):
        # We must not modify the bug unless it is crankable.
        if not s.is_crankable:
            return
        if s.version is None:
            version = '<version to be filled>'
        else:
            version = s.version
        title = "{}/{}: {} {}".format(s.series, s.name, version, suffix)
        if s.title != title:
            s.lpbug.title = title
            s.tracker_modified = True
            s.title = title

    def __title_decode(s):
        title = s.title

        # Title: [<series>/]<package>: <version> <junk>
        #
        # If the series is absent it will report None, if the version is
        # unspecified it will report as None.
        #
        #                                 .- optional series (group(1))
        #                                 |       .- package (group(2))
        #                                 |       |             .- version (group(3))
        #                                 |       |             |
        title2spv_rc = re.compile(r'^(?:(\S+)/)?(\S+): (?:(\d+\.\d+\.\S+)|<version to be filled>)')

        match = title2spv_rc.search(title)
        if not match:
            cdebug('title invalid: <{}>'.format(title))
            s.is_valid = False
            return False

        (series, name, version) = match.groups()
        # If we have no series specified fall back to looking at the
        # bug tags looking for a series specific tag.
        if series is None:
            series_ent = None
            for tag in s.lpbug.tags:
                series_ent = s.kernel_series.lookup_series(codename=tag)
                if series_ent is not None:
                    series = tag
                    break
        s.series = series
        s.name = name
        s.version = version

        # We will want to use the kernel and ABI components so split
        # those out here.
        (kernel, abi) = (None, None)
        if s.version is not None:
            version2ka_rc = re.compile(r'^(\d+\.\d+\.\d+)[\.-](\d+)')
            match = version2ka_rc.search(s.version)
            if match:
                (kernel, abi) = match.groups()
        s.kernel = kernel
        s.abi = abi

        # Lookup the kernel-series object for this package.
        # XXX: why is this not a property?!?
        source = None
        if s.series is not None:
            series_ent = s.kernel_series.lookup_series(codename=series)
            if series_ent is not None:
                source = series_ent.lookup_source(s.name)
        s.source = source

        cdebug(' series: {}'.format(series))
        cdebug('package: {}'.format(name))
        cdebug('version: {}'.format(version))
        return True

    # _remove_live_tag
    #
    def _remove_live_tag(s):
        # If this task is now closed, also drop the live tag.
        if s.is_valid and s.is_closed:
            if s._dryrun:
                cinfo('    dryrun - workflow task is closed -- removing -live tag', 'red')
            else:
                cinfo('    action - workflow task is closed -- removing -live tag', 'red')

                # Drop the "-live" tag as this one is moving dead.
                if 'kernel-release-tracking-bug-live' in s.lpbug.tags:
                    s.lpbug.tags.remove('kernel-release-tracking-bug-live')
                    s.tracker_modified = True

    # save
    #
    def save(s):
        s.save_bug_properties()
        s._remove_live_tag()
        if s.tracker_modified:
            cinfo("Tracker modified, saving")
            s.lpbug.lpbug.lp_save()
            s.tracker_modified = False

    @property
    def _dryrun(s):
        return WorkflowBug.dryrun

    @property
    def _no_announcements(s):
        return WorkflowBug.no_announcements

    @property
    def _sauron(s):
        return WorkflowBug.sauron

    # variant
    #
    @property
    def variant(s):
        return s.bprops.get('variant', 'combo')

    # master_bug_property_name
    #
    @property
    def master_bug_property_name(s):
        for prop_name in (
            'master-bug',
            'kernel-stable-master-bug',
            'kernel-master-bug',
            ):
            if prop_name in s.bprops:
                return prop_name
        return 'master-bug'

    # is_derivative_package
    #
    @property
    def is_derivative_package(s):
        return s.master_bug_property_name in s.bprops

    # master_bug
    #
    @property
    def master_bug_id(s):
        '''
        '''
        return s.bprops[s.master_bug_property_name]

    @master_bug_id.setter
    def master_bug_id(s, bugid):
        '''
        '''
        s.bprops[s.master_bug_property_name] = bugid
        s._master_bug = False

    # master_bug
    #
    @property
    def master_bug(s):
        '''
        Find the 'master' bug of which this is a derivative and return that bug.
        '''
        if s._master_bug is False:
            if s.is_derivative_package:
                try:
                    master = WorkflowBug(s.lp, s.master_bug_id)
                    error = None
                    if master.is_gone:
                        error = WorkflowCrankError("master tracker link points to invalidated tracker")
                    if not master.is_crankable and not master.is_closed:
                        error = WorkflowCrankError("master tracker link points to uninstantiated tracker")

                    if error is not None:
                        # check if our master is a duplicte, and if so follow the chain.
                        duplicate_of = master.lpbug.lpbug.duplicate_of
                        if duplicate_of is not None:
                            cinfo("master-bug link points to a duplicated bug, following {} -> {}".format(s.master_bug_id, master.lpbug.lpbug.id))
                            master = WorkflowBug(s.lp, bug=duplicate_of)
                        else:
                            raise error
                except WorkflowBugError as e:
                    # Mark this as known to fail.
                    raise WorkflowCrankError("invalid master bug link -- {}".format(e.args[0]))
                s._master_bug = master
            else:
                s._master_bug = None

        if isinstance(s._master_bug, WorkflowBugError):
            raise s._master_bug

        return s._master_bug

    # master_bug_swmstatus
    #
    @property
    def master_bug_swmstatus(self):
        if not self.is_derivative_package:
            return None
        return self.manager.status_get(str(self.master_bug_id))

    # dup_replaces
    #
    def dup_replaces(s, inactive_only=False):
        '''
        If we have a pending replaces bug pointer duplicate that bug now against ourselves.
        '''
        center(s.__class__.__name__ + '.dup_replaces')

        dup_pointer = s.bprops.get('replaces')
        if dup_pointer is None:
            cleave(s.__class__.__name__ + '.dup_replaces')
            return
        dup_id = dup_pointer.split()[1]
        try:
            dup_wb = WorkflowBug(s.lp, dup_id)
        except WorkflowBugError:
            raise WorkflowBugError("invalid replaces pointer {}".dup_id)

        # If we have no testing tasks active then there is is no value in
        # holding the duplication till later.  For variant debs we also trigger
        # duplication when we are ready to to promote the replacement tracker.
        keep = False
        if inactive_only:
            cinfo("replaces={} detected checking target inactive".format(dup_pointer))
            for taskname, task in dup_wb.tasks_by_name.items():
                if (taskname.endswith('-testing') and task.status in
                        ['Confirmed', 'Triaged', 'In Progress',
                        'Fix Committed']):
                    keep = True
                elif (taskname == 'promote-to-proposed' and task.status in
                        ['Confirmed', 'Triaged', 'In Progress',
                        'Fix Committed']):
                    keep = True
                elif (taskname == 'promote-to-updates' and task.status in
                        ['Confirmed', 'Triaged', 'In Progress',
                        'Fix Committed', 'Fix Released']):
                    keep = True

        # If we deem this ready for duplication wack it.
        if not keep:
            cinfo("replaces={} detected duplicating {} to {}".format(dup_pointer, dup_wb.lpbug.id, s.lpbug.id))
            # XXX: lpltk does not a allow access to the duplicates.
            dup_wb.lpbug.lpbug.duplicate_of = s.lpbug.lpbug
            dup_wb.lpbug.lpbug.lp_save()

            del s.bprops['replaces']

            # Now we are duplicated to that bug consider any replaces it
            # also expresses.
            if 'replaces' in dup_wb.bprops:
                s.bprops['replaces'] = dup_wb.bprops['replaces']
                s.dup_replaces(inactive_only)

        cleave(s.__class__.__name__ + '.dup_replaces')

    # load_bug_properties
    #
    def load_bug_properties(s):
        center(s.__class__.__name__ + '.load_bug_properties')
        retval = {}
        started = False
        buf = ''

        description = s.lpbug.description
        for l in description.split('\n'):
            if started:
                buf += l + '\n'
            if l.startswith('-- swm properties --'):
                started = True

        if started and buf is not None:
            # Launchpad will convert leading spaces into utf-8 non-breaking spaces
            # when you manually edit the description in the web interface.
            buf = buf.replace('\xa0', ' ')
            try:
                retval = yaml.safe_load(buf)
                if retval is None:
                    retval = {}
            except Exception as e:
                retval = {}
                error = str(e).split('\n')[0]
                s.error = WorkflowCorruptError('failed to load swm-properties -- {}'.format(error))

        cleave(s.__class__.__name__ + '.load_bug_properties')
        return retval

    # properties_for_description
    #
    # Turn the properties into a valid yaml representation but formatted at a
    # pleasant width so it will not be wrapped further by launchpad.  We have
    # to do this ourselves because width restrtictions are soft in the
    # yaml.safe_dump() call.  We attempt to build the representation and parse
    # it back, if that fails for any reason fall back to the native form rather
    # than corrupt the contents.
    #
    def properties_for_description(s, props):
        lines = yaml.safe_dump(props, default_flow_style=False, width=10000).split('\n')
        props_bits = []
        for line in lines:
            prefix = (len(line) - len(line.lstrip()) + 2) * ' '
            line = fill(line, subsequent_indent=prefix, break_on_hyphens=False)
            props_bits.append(line)
        props_wrapped = '\n'.join(props_bits)

        for line in props_wrapped.split('\n'):
            cinfo('        ' + line, 'magenta')
        props_new = yaml.safe_load(props_wrapped)
        if props != props_new:
            cinfo("properties_for_description: falling back to default")
            props_wrapped = yaml.safe_dump(props, default_flow_style=False, width=65)

        return props_wrapped.strip()

    # save_bug_properties
    #
    def save_bug_properties(s):
        center(s.__class__.__name__ + '.save_bug_properties')

        # Mirror some of our tracker tag information over to property
        # flags so that we can get to it quickly, and also tell if
        # a scan of the tracker has happened.
        block = 'kernel-jira-preparation-blocked' in s.tags
        s._flag_assign('jira-preparation-block', block)
        block = ('kernel-trello-blocked-debs-prepare' in s.tags or
            'kernel-trello-blocked-prepare-packages' in s.tags or
            'kernel-trello-blocked-snap-prepare' in s.tags)
        s._flag_assign('trello-preparation-block', block)

        retval = None
        newd = ''

        if len(s.bprops) > 0:
            status = s.bprops
            status.setdefault('reason', {}).update(s.reasons)
            new_props = s.properties_for_description(status)

            description = s.lpbug.description
            for l in description.split('\n'):
                if l.startswith('-- swm properties --'):
                    break
                newd += l + '\n'

            newd += '-- swm properties --\n'
            newd += new_props

            if s.lpbug.description != newd:
                if s._dryrun:
                    cinfo('    dryrun - updating SWM properties', 'red')
                else:
                    cinfo('    action - updating SWM properties', 'red')
                    s.lpbug.description = newd
                    s.tracker_modified = True
            else:
                cinfo('    noop - SWM properties unchanged', 'yellow')
            for line in new_props.split('\n'):
                cinfo('        ' + line, 'magenta')

        cleave(s.__class__.__name__ + '.save_bug_properties')
        return retval

    # transient_reset_all
    #
    def transient_reset_all(s):
        '''
        Reset all existing transient data (reasons etc) for this bug.
        '''
        if 'reason' in s.bprops:
            del s.bprops['reason']
        s._refresh = [None, None]
        s._monitor = []
        s.interlocks = {}

    @property
    def refresh(s):
        return s._refresh

    def refresh_at(s, when, why):
        if when.tzinfo is None:
            raise ValueError("refresh_at needs an offset-aware datetime")
        (current_when, _) = s._refresh
        if current_when is None or when < current_when:
            cinfo("refresh_at {} {}".format(when, why))
            s._refresh = [when, why]

    @property
    def monitor(s):
        return s._monitor

    def monitor_add(s, what):
        if what not in s._monitor:
            cdebug("new monitor: {}".format(what))
            s._monitor.append(what)

    @property
    def maintenance(s):
        return s._maintenance

    def maintenance_add(s, what):
        s._maintenance.append(what)

    def add_live_children(s, children):
        blockers = {}
        new_children = {}
        for (series, source, target, child_id, child_data) in children:
            key = "{}/{}".format(series, source)
            if source != target:
                key += "/{}".format(target)
            new_children.setdefault(key, []).append("bug " + child_id)
            # Accumulate any interlock data from our children.
            blockers.update(child_data.get('interlocks', {}))
        for key, key_ids in new_children.items():
            s.bprops.setdefault('trackers', {})[key] = ", ".join(key_ids)

        s.blockers = blockers

    def block_present(s, block):
        if block not in s.blockers:
            return None

        if 'kernel-override-' + block in s.tags:
            cinfo("blocker {} present but hinted unblock".format(block))
            return None

        return s.blockers[block]

    def _flag_assign(s, flag, value):
        flags = s.bprops.setdefault('flag', {})
        if value is not False:
            flags[flag] = value

        elif flag in flags:
            del flags[flag]

        if len(flags) == 0:
            del s.bprops['flag']

    def _source_block_present(s):
        if 'kernel-block-source' in s.tags:
            return "Manual tag kernel-block-source"
        if 'kernel-block' in s.tags:
            return "Manual tag kernel-block"

        block = 'kernel-jira-preparation-blocked' in s.tags
        if block:
            return "SRU Board (jira)"

        if s.debs is not None:
            block = 'kernel-trello-blocked-debs-prepare' in s.tags or 'kernel-trello-blocked-prepare-packages' in s.tags
            if block:
                return "SRU Board (trello)"

        if s.snap is not None:
            block = 'kernel-trello-blocked-snap-prepare' in s.tags
            if block:
                return "SRU Board (trello)"

        return None

    def source_block_present(s):
        block = s._source_block_present()
        cinfo("source_block_present: " + str(block), "yellow")
        return block

    def status_summary(s):
        '''
        Return the current reason set for this bug.
        '''
        status = s.bprops
        status.setdefault('reason', {}).update(s.reasons)

        # Ensure we do not modify the bug when adding the
        # remainder of the status data.
        status = dict(status)

        # Check if we are actually fully complete, if so then
        # we can delete this entry from status.
        if ('kernel-sru-workflow' in s.tasks_by_name and
                s.tasks_by_name['kernel-sru-workflow'].status in
                ('Fix Released', 'Invalid')):
            return None

        # Add the current tasks status information.
        owner = None
        owner_pp = None
        task = status.setdefault('task', {})
        for taskname in s.tasks_by_name:
            task[taskname] = {
                'status': s.tasks_by_name[taskname].status,
                }
            assignee = s.tasks_by_name[taskname].assignee
            if assignee is not None:
                task[taskname]['assignee'] = assignee.username
                # Record the overall owner if we have one.
                if taskname == 'kernel-sru-workflow':
                    owner = assignee.username
                # XXX: lpltk does not expose `is_team` so just bodge it.
                elif taskname == 'prepare-package' and assignee.username != 'canonical-kernel-team':
                    owner_pp = assignee.username

            # XXX: ownership of tasks should be more obvious, but this is
            # only needed while we have combo bugs in reality.
            if (taskname.startswith('snap-') and s.snap is not None and
                s.snap.name != s.name):
                task[taskname]['target'] = s.snap.name

        # If the workflow task is assigned assume that as owner.  If not
        # and the kernel-series object has an owner use that.  If neither
        # of those is valid, use the prepare-package owner.
        if owner is None and s.source is not None and s.source.owner is not None:
            owner = s.source.owner
        elif owner is None and owner_pp is not None:
            owner = owner_pp

        # If we still have no owner and we are a snap-debs tracker
        # pull the owner from our parent.
        if owner is None and s.variant == 'snap-debs':
            master_status = s.master_bug_swmstatus
            if master_status is not None:
                owner = master_status.get('owner')

        if owner is not None:
            status['owner'] = owner

        if s.refresh[0] is not None:
            status['refresh'] = s.refresh

        if len(s.monitor) > 0:
            status['monitor'] = s.monitor

        if len(s.maintenance) > 0:
            status['maintenance'] = s.maintenance

        if len(s.interlocks) > 0:
            status['interlocks'] = s.interlocks

        if s.stage is not None:
            status['stage'] = s.stage

        try:
            status['cycle'] = s.sru_cycle
            status['series'] = s.series
            status['source'] = s.name
            status['package'] = s.name # XXX: legacy
            if s.version is not None:
                status['version'] = s.version
            # Identify the target of this bug.
            target = s.target
            if target is not None:
                status['target'] = target
        except Exception as e:
            cerror("status failed {}".format(e))

        # Do not expose this API error.
        master_bug = s.master_bug_property_name
        if master_bug != 'master-bug' and master_bug in status:
            status['master-bug'] = status[master_bug]
            del status[master_bug]

        return status

    # check_is_valid
    #
    def check_is_valid(s):
        '''
        Determine if this bug is one that we want to be processing. Bugs that we
        should not be processing are ones that are not currently "In Progress".
        '''
        s.is_workflow = False
        s.is_new = False
        s.is_crankable = False
        s.is_closed = False
        s.is_gone = False
        for t in s.lpbug.tasks:
            task_name       = t.bug_target_name

            if task_name in WorkflowBug.projects_tracked:
                s.is_workflow = True
                s.workflow_project = task_name
                if t.status == 'Triaged':
                    s.is_new = True
                    s.is_crankable = True
                elif t.status == 'In Progress':
                    s.is_crankable = True
                elif t.status == 'Fix Released':
                    s.is_closed = True
                elif t.status == 'Invalid':
                    s.is_gone = True
                break

    # accept_new
    #
    def accept_new(self):
        if not self.is_new:
            return

        for t in self.lpbug.tasks:
            task_name       = t.bug_target_name

            if task_name in WorkflowBug.projects_tracked:
                cinfo("accept_new: Triaged tracker now tracked flipping In Progress")
                t.status = 'In Progress'
                break

        self.check_is_valid()

    # _create_tasks_by_name_mapping
    #
    def _create_tasks_by_name_mapping(s):
        '''
        We are only interested in the tasks that are specific to the workflow project. Others
        are ignored.
        '''
        tasks_by_name = {}

        cinfo('')
        cinfo('    Scanning bug tasks:', 'cyan')

        synthesise = set()

        for t in s.lpbug.tasks:
            task_name       = t.bug_target_name

            if task_name.startswith(s.workflow_project):
                if '/' in task_name:
                    task_name = task_name[len(s.workflow_project) + 1:].strip()
                tasks_by_name[task_name] = WorkflowBugTask(t, task_name, s.debs, s)

                # Synthetic tasks.
                if task_name.startswith('prepare-package'):
                    synthesise.add(':prepare-packages')

            else:
                cinfo('        %-25s' % (task_name), 'magenta')
                cinfo('            Action: Skipping non-workflow task', 'magenta')

        # Add our synthetic tasks.
        if ':prepare-packages' in synthesise:
            task = WorkflowBugTaskSynPreparePackages(':prepare-packages', s)
            tasks_by_name[task.name] = task

        if s.debs is not None:
            task = WorkflowBugTaskSynPersistent(':promote-to-as-proposed', s)
            tasks_by_name[task.name] = task

        return tasks_by_name

    # valid_package
    #
    def valid_package(s, pkg):
        center(s.__class__.__name__ + '.valid_package')

        # XXX: this is not deb related.
        retval = pkg in s.debs.pkgs

        cleave(s.__class__.__name__ + '.valid_package')
        return retval

    def published_tag(s, pkg):
        published = True

        # Adjunct packages are wholy contained in their parent package.  That
        # package will check its own tag.  No tag is expected.
        if s.debs.ancillary_package_for(pkg) is not None:
            return published

        package_package = None
        for package in s.source.packages:
            if (package.type == pkg or (
                package.type is None and pkg == 'main')
                ):
                package_package = package
                break
        if package_package is not None:
            version = s.debs.package_version(pkg)
            if version is None:
                published = False
            else:
                try:
                    git_tag = GitTag(package_package, version)
                    if git_tag.verifiable and not git_tag.present:
                        published = False
                except GitTagError as e:
                    cerror("{} {}: Tag lookup failed -- {}".format(
                        package_package, version, e))
                    published = False
                if published is False:
                    cinfo("tag missing refresh_at triggered")
                    s.refresh_at(datetime.now(timezone.utc) + timedelta(minutes=20),
                        '{} {} polling for tag'.format(
                        package_package, version))

        return published

    # all_dependent_packages_published_tag
    #
    @property
    def all_dependent_packages_published_tag(s):
        '''
        For the kernel package associated with this bug, the status of whether or
        not all of the dependent packages (meta, signed, lbm, etc.) have published
        tags is returned.
        '''
        retval = True

        bi = s.debs.build_info
        for pkg in bi:
            if not s.published_tag(pkg):
                cinfo('        %s missing tag.' % (pkg), 'yellow')
                retval = False
                break

        return retval

    @property
    def swm_config(s):
        '''
        Flag information from kernel-series.
        '''
        if s.source is None:
            return None
        return SwmConfig(s.source.swm_data)

    @property
    def tags(s):
        '''
        Returns a list of the tags on the bug.
        '''
        if s._tags is None:
            s._tags = []
            for t in s.lpbug.tags:
                s._tags.append(t)
        return s._tags

    # modified
    #
    @property
    def modified(s):
        '''
        Have any of the tasks statuses been changed?
        '''
        retval = False
        for t in s.tasks_by_name:
            if s.tasks_by_name[t].modified:
                retval = True
                break
        return retval

    # _has_prep_task
    #
    def _has_prep_task(s, taskname):
        if taskname in s.tasks_by_name:
            if s.tasks_by_name[taskname].status != "Invalid":
                return True
        return False

    # task_status
    #
    def task_status(s, taskname):
        if taskname in s.tasks_by_name:
            return s.tasks_by_name[taskname].status
        return "Invalid"

    # phase
    #
    @property
    def phase(s):
        return s.bprops.get('phase')

    @phase.setter
    def phase(s, phasetext):
        """
        Add the phase we're entering as a 'property', along with a time stamp.
        """
        center(s.__class__.__name__ + '.set_phase')

        # We have to check here to see whether the same status is already set,
        # or we will overwrite the timestamp needlessly
        if s.phase == phasetext:
            # we already have this one
            cdebug('Not overwriting identical phase property (%s)' % phasetext)
            cleave(s.__class__.__name__ + '.set_phase')
            return
        # Handle dryrun mode
        if s._dryrun or WorkflowBug.no_phase_changes:
            cinfo('    dryrun - Changing bug phase to <%s>' % phasetext, 'red')
            cleave(s.__class__.__name__ + '.set_phase')
            return

        # Add phase and time stamp
        cdebug('Changing bug phase to <%s>' % phasetext)
        now = datetime.utcnow()
        now.replace(tzinfo=None)
        tstamp = date_to_string(now)

        s.bprops['phase'] = phasetext
        s.bprops['phase-changed'] = tstamp
        cleave(s.__class__.__name__ + '.set_phase')

    @property
    def phase_changed(s):
        stamp = s.bprops.get('phase-changed')
        if stamp is None:
            return None
        return string_to_date(stamp)

    # has_new_abi
    #
    def has_new_abi(s):
        tasks_abi = ['prepare-package-lbm', 'prepare-package-meta', 'prepare-package-ports-meta']
        retval = False
        for taskname in tasks_abi:
            if taskname in s.tasks_by_name:
                if s.tasks_by_name[taskname].status != "Invalid":
                    return True
        return retval

    # sru_spin
    #
    @property
    def sru_spin(s):
        if s._sru_spin is False:
            spin = None
            for t in s.tags:
                if t.startswith('kernel-sru-cycle-'):
                    spin = t.replace('kernel-sru-cycle-', '')
            if spin is not None:
                spin = s.sc.lookup_spin(spin, allow_missing=True)
            s._sru_spin = spin

        return s._sru_spin

    # sru_cycle
    #
    @property
    def sru_cycle(s):
        spin = s.sru_spin
        if spin is not None:
            spin = spin.name
        else:
            spin = '1962.11.02-00'
        return spin

    def send_email(s, subject, body, to):
        from .bugmail import BugMail
        BugMail.load_config('email.yaml')
        BugMail.to_address = to
        BugMail.send(subject, body)

    def announce(s, key, subject=None, summary=None, body=None):
        from ktl.announce import Announce
        announce = Announce()
        announce.send(key, subject=subject, summary=summary, body=body)

    # send_upload_announcement
    #
    def send_upload_announcement(s, pocket):
        """
        Send email with upload announcement
        """
        center(s.__class__.__name__ + '.send_upload_announcement')

        # -------------------------------------------------------------------------------------------------------------
        # Email Notice
        # -------------------------------------------------------------------------------------------------------------

        cdebug('Sending upload announcement')

        to_address  = "kernel-team@lists.ubuntu.com"

        abi_bump = s.has_new_abi()

        subject = "[" + s.series + "] " + s.name + " " + s.version + " uploaded"
        if abi_bump:
            subject += " (ABI bump)"

        if s._dryrun or s._no_announcements:
            cinfo('    dryrun - Sending announcement to shankbot', 'red')
        else:
            send_to_shankbot(subject + '\n')

        body  = "A new " + s.series + " kernel has been uploaded into "
        body += pocket + ". "
        if abi_bump:
            body += "Note the ABI bump. "
        body += "\nThe full changelog about all bug fixes contained in this "
        body += "upload can be found at:\n\n"
        body += "https://launchpad.net/ubuntu/" + s.series + "/+source/"
        body += s.name + "/" + s.version + "\n\n"
        body += "-- \nThis message was created by an automated script,"
        body += " maintained by the\nUbuntu Kernel Team."

        if s._dryrun or s._no_announcements:
            cinfo('    dryrun - Sending email announcement', 'red')
        else:
            s.send_email(subject, body, to_address)

        cleave(s.__class__.__name__ + '.send_upload_announcement')
        return

    def add_comment(s, subject, body):
        """
        Add comment to tracking bug
        """
        center(s.__class__.__name__ + '.add_comment')
        if s._dryrun:
            cinfo('    dryrun - Adding comment to tracking bug', 'red')
            cdebug('')
            cdebug('subject: %s' % (subject))
            for l in body.split('\n'):
                cdebug('comment: %s' % (l))
            cdebug('')
        else:
            cdebug('Adding comment to tracking bug')
            s.lpbug.add_comment(body, subject)
        cleave(s.__class__.__name__ + '.add_comment')

    # timestamp
    #
    def timestamp(s, keyvalue):
        '''
        Add the supplied key with a timestamp. We do not replace existing keys
        '''
        center(s.__class__.__name__ + '.timestamp')

        # if s._dryrun or s.no_timestamps:
        #     cinfo('    dryrun - Adding timestamp for \'%s\'' % keyvalue, 'red')
        # else:
        #     if keyvalue not in s.bprops:
        #         cinfo('    Adding timestamp for \'%s\'' % keyvalue)
        #         now = datetime.utcnow().replace(tzinfo=None)
        #         s.bprops[keyvalue] = date_to_string(now)

        cleave(s.__class__.__name__ + '.timestamp')

    # has_package
    #
    @property
    def has_package(s):
        return s.debs is not None

    # is_proposed_only
    #
    @property
    def is_proposed_only(s):
        return False

    # workflow_duplicates
    #
    @property
    def workflow_duplicates(s):
        retval = []

        # XXX: XXX: lpltk does NOT let me get to the duplicate list!?!?!?!
        duplicates = s.lpbug.lpbug.duplicates
        #duplicates = [ s.lp.get_bug('1703532') ]
        for dup in duplicates:
            cdebug("workflow_duplicates: checking {}".format(dup.id))
            try:
                dup_wb = WorkflowBug(s.lp, dup.id)
            except WorkflowBugError as e:
                cinfo("workflow_duplicates: duplicate {} threw a {} exception, ignored".format(dup.id, e.__class__.__name__))
                for l in e.args:
                    cinfo(l, 'red')
                continue

            if not dup_wb.is_workflow or not dup_wb.is_valid or dup_wb.is_gone:
                continue
            retval.append(dup_wb)

        return retval

    # target
    #
    @property
    def target(s):
        target = None
        for variant_obj in (s.debs, s.snap):
            if variant_obj is not None:
                target = variant_obj.name
                break
        return target

    # target_trackers
    #
    @property
    def target_trackers(s):
        if s._target_trackers is None:
            cinfo("APW lookup target_trackers")
            s._target_trackers = s.manager.live_trackers_for_target(s.series, s.name, s.target)
        return s._target_trackers

# vi:set ts=4 sw=4 expandtab:
