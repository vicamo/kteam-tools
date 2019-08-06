#!/usr/bin/env python3
'''
Abstraction class to work with Launchpad bugs which represent kernels
being processed through the kernel-team SRU workflow.
'''

# Option
import os
import sys
LIBDIR=os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'libs'))
if LIBDIR not in sys.path:
    sys.path.append(LIBDIR)

from ktl.workflow                       import Workflow, DefaultAssigneeMissing
from ktl.kernel_series                  import KernelSeries
from lpltk.LaunchpadService             import LaunchpadService
from lpltk.bug                          import Bug
import re
import yaml

from ktl.log                            import cdebug, cinfo, cerror, cwarn, center, cleave
from logging                            import basicConfig

'''
The launchpad projects which are used on launchpad to represent the
SRU workflow. (FIXME: This probably should be inherited from the
ktl.workflow module).
'''
TRACKINGBUG_PROJECTS = [
    'kernel-sru-workflow',
    'kernel-development-workflow',
]
TRACKINGBUG_DEFAULT_PROJECT = TRACKINGBUG_PROJECTS[0]

class TrackingBugError(Exception):
    '''
    An exception which is thrown on failures when creating TrackingBug
    objects.
    '''
    def __init__(self, error):
        self.msg = error

class TrackingBugDefines(object):
    '''
    Data which is needed by TrackingBug() and TrackingBugs() objects.
    '''
    desc_tmpl = 'This bug will contain status and test results related to ' \
                'a kernel source (or snap) as stated in the title.\n\n' \
                'For an explanation of the tasks and the associated ' \
                'workflow see:\n  ' \
                'https://wiki.ubuntu.com/Kernel/kernel-sru-workflow\n'
    no_version = '<version to be filled>'
    # FIXME: Maybe better change into one dict with valid and valid-test
    # as keys.
    tag_names = {
        'default': {
            'valid':        'kernel-release-tracking-bug-live',
            'cycle':        'kernel-sru-cycle-',
            'derivative':   'kernel-sru-derivative-of-',
            'backport':     'kernel-sru-backport-of-',
        },
        'testing': {
            'valid':        'kernel-release-tracking-bug-test',
            'cycle':        'kernel-sru-cycle-',
            'derivative':   'kernel-sru-derivative-of-',
            'backport':     'kernel-sru-backport-of-',
        },
    }

class TrackingBug(object):
    '''
    A single TrackingBug represents the SRU status of a set of packages for
    one kernel (currently this would be kernel, signed, and meta).
    Each task of the tracking bug represents a phase of the workflow and its
    current state.
    '''
    # Shared between all instances
    __bp_re = re.compile('^backports: (.+)$', re.M)
    __dv_re = re.compile('^derivatives: (.+)$', re.M)
    __comsep_re = re.compile(', *')
    __tbd = TrackingBugDefines()

    def __replace_pfx_tag(s, prefix, new_tag):
        '''
        Internal helper to replace a tag that starts with <prefix> with
        a <new_tag>.
        '''
        for tag in s.__bug.tags:
            if tag.startswith(prefix):
                s.__bug.tags.remove(tag)
                # Not stopping here so duplicates get removed, too
        s.__bug.tags.append(new_tag)

    def __parse_reflist(s, reflist, sameseries=True):
        '''
        Internal helper to parse a (comma seperated) list of
        bug references from either the backport or the derivatives
        section.

        With sameseries being True, the format is:
          bug <number> (<name>)[, ...]
        otherwise it is:
          bug <number> (<series>/<name>)[, ...]
        '''
        for bug_ref in reflist:
            if bug_ref == '':
                continue

            # The bug number and the human readable source label are
            # the last 2 elements separated by spaces.
            ref_id, ref_name = bug_ref.split(' ')[-2:]
            ref_name = ref_name[1:-1]

            # For backport lists, expect the first element separated
            # by '/' to be the series.
            if sameseries is False:
                if '/' in ref_name:
                    ref_series, ref_name = ref_name.split('/', 1)
                else:
                    ref_series = '<unknown>'
            else:
                ref_series = ''

            # Whatever remains in ref_name is the name for the object
            # which the tracking bug follows, intended for human con-
            # sumption only.

            s._derivative_bug_ids[int(ref_id)] = [ ref_series, ref_name ]

    def __parse_lpbug(s):
        '''
        Internal helper to set/refresh tracking bug properties from
        the information contained in the launchpad bug.
        '''
        bug = s.__bug
        lp  = bug.service.launchpad

        # The embedded bug title encodes <package>: <version> -proposed tracker
        #   <version> initially is the string "<version to be filled>"
        s._target_series = None
        package, remainder = bug.title.split(' ', 1)
        if '/' in package:
            (s._target_series, package) = package.split('/')
        if not package.endswith(':'):
            msg = 'invalid title string ({})'.format(bug.title)
            raise TrackingBugError(msg)
        s._target_package = package[:-1]
        if remainder.startswith(s.__tbd.no_version):
            magic = remainder[len(s.__tbd.no_version)+1:]
        else:
            s._target_version, magic = remainder.split(' ', 1)

        #
        # If the launchpad bug already has tracking bug related info
        # 
        for tag in bug.tags:
            # The series is primarily encoded in the tags.
            if s.__kernel_series.lookup_series(codename=tag) is not None:
                s._target_series = tag
                continue

            # Check for cycle tag
            prefix = s.__tbd.tag_names['default']['cycle']
            if tag.startswith(prefix):
                cycletag = tag[len(prefix):]
                if not '-' in cycletag:
                    s._cycle = cycletag
                else:
                    s._cycle, spin_str = cycletag.rsplit('-', maxsplit=1)
                    s._spin_nr = int(spin_str)
                    if s._spin_nr < 1:
                        s._spin_nr = 1

            # Check for master bug reference tag:
            #   "kernel-sru-derivative-of-<master bug id>"
            prefix = s.__tbd.tag_names['default']['derivative']
            if tag.startswith(prefix):
                s._master_bug_id = int(tag[len(prefix):])
                s.__type = 'derivative'

            # FIXME: Right now there is a differentiation between derivatives
            # (variant of the master kernel) and backports (variant of some
            # kernel in a different series). Long-term I believe this should
            # all become the same and a derivative is just a relation to
            # some <series>/<kernel>.
            prefix = s.__tbd.tag_names['default']['backport']
            if tag.startswith(prefix):
                s._master_bug_id = int(tag[len(prefix):])
                s.__type = 'backport'

        # The target series name is encoded as a nomination for it on
        # a source package task (either real name or linux if new.
        # The target_link of interest contains the string 'ubuntu' and
        # then not immediately followed by '+source'.
        # FIXME: If this gets encoded either in the title or in the
        #        SWM properties, the whole package related tasks could
        #        probably be avoided.
        if s._target_series is None:
            for task in bug.tasks:
                tgt_link = task.lp_bug_task.target_link

                if '/ubuntu/' in tgt_link:
                    if '/ubuntu/+source/' not in tgt_link:
                        part = tgt_link.partition('/+source/')
                        package = part[2]
                        series_name = part[0].rsplit('/', 1)[1]
                        s._target_series = series_name

        # Everything beyond "-- swm properties --" is supposed to be yaml
        # format. However Launchpad will convert leading spaces after manual
        # updates into non-breaking spaces (0xa0) which breaks yaml parsing.
        desc = bug.description
        ys   = desc.partition('\n-- swm properties --\n')[2]
        if ys != '':
            ys = ys.replace('\xa0', ' ')
            try:
                s.__wf_properties = yaml.safe_load(ys)
            except:
                pass

        # The information in the SWM properties is supposed to be authorative
        # so if certain tag information differs it needs to be updated.
        if 'kernel-stable-master-bug' in s.__wf_properties:
            p_master = int(s.__wf_properties['kernel-stable-master-bug'])
            if s._master_bug_id is None:
                # It is possible that at some point we stop using tags for
                # the bug linking completely. So this would be "normal".
                s._master_bug_id = p_master
            elif s._master_bug_id != p_master:
                cwarn('Mismatch between tag and properties: master bug')
                cwarn('tag: %s / property: %s' % (s._master_bug_id, p_master))
                s._master_bug_id = p_master
                #prefix = 'kernel-sru-%s-of-' % s.__type
                #s.__update_pfx_tag(prefix, '%s%s' % (prefix, p_master))
        # Target series might be in properties
        p_key = 'target-series'
        if p_key in s.__wf_properties:
            if s._target_series is None:
                s._target_series = s.__wf_properties[p_key]
            elif s._target_series != s.__wf_properties[p_key]:
                cwarn('Mismatch between target series in task and properties')
                cwarn('P[target-series]: {}'.format(s.__wf_properties[p_key]))
                cwarn('T: {}'.format(s._target_series))

        # Evaluate the bug description and fill the various caching
        # elements. Though the lists for derivatives comes before
        # SWM properties, evaluation must be after those to pick up
        # the target series.
        # FIXME: Derivative and backport should become the same.
        s._derivative_bug_ids = {}
        ks_series = s.__kernel_series.lookup_series(codename=s._target_series)

        # Currently the backports list refers to sources to which the source
        # of this tracking bug is backported, but without any info about the
        # backport target series.
        tbmatch = s.__bp_re.search(desc)
        if tbmatch is not None:
            s.__parse_reflist(s.__comsep_re.split(tbmatch.group(1)), sameseries=False)

        tbmatch = s.__dv_re.search(desc)
        if tbmatch is not None:
            s.__parse_reflist(s.__comsep_re.split(tbmatch.group(1)))

    def __init__(s, bug, wf_project_name=TRACKINGBUG_DEFAULT_PROJECT):
        '''
        Create a new tracking bug object from an existing launchpad bug
        which is passed in as bug number reference.

        :param bug: The launchpad bug which is used as a backing store
            for the tracking bug info.
        :type  bug: lpltk.Bug()
            
        :param wf_project_name: Name of the launchpad project to use for
            workflow tasks.
        :type  wf_project_name: str
        '''
        lp = bug.service.launchpad
        # Init class data
        s.__bug                     = bug
        s.__wf                      = Workflow()
        s.__wf_project              = lp.projects[wf_project_name]
        s.__wf_properties           = {}
        s.__kernel_series           = KernelSeries()
        s.__modified                = False
        s.__type                    = 'master'

        # Cached properties which are stored somewhere in the bug
        # report and will be initialiazed through the accessor functions.
        s._target_series            = None
        s._target_package           = None
        s._target_version           = None
        s._isdev                    = None
        s._cycle                    = None
        s._spin_nr                  = 1
        s._master_bug_id            = None
        s._derivative_bug_ids       = {}

        s.__parse_lpbug()

    def __update_desc(s):
        '''
        Internal helper to update the description of the embedded launchpad
        bug with the workflow content.
        '''
        new_desc = s.__tbd.desc_tmpl

        dv_str = ''
        bp_str = ''
        for dbug_id in s._derivative_bug_ids:
            series, name = s._derivative_bug_ids[dbug_id]
            if series == '':
                if dv_str != '':
                    dv_str += ', '
                dv_str += 'bug {} ({})'.format(dbug_id, name)
            else:
                if bp_str != '':
                    bp_str += ', '
                if series != '<unknown>':
                    bp_str += 'bug {} ({}/{})'.format(dbug_id, series, name)
                else:
                    bp_str += 'bug {} ({})'.format(dbug_id, name)

        if bp_str != '':
            new_desc += '\nbackports: ' + bp_str
        if dv_str != '':
            new_desc += '\nderivatives: ' + dv_str
        if dv_str != '' or bp_str != '':
            new_desc += '\n'

        # For the properties just do a yaml dump
        if len(s.__wf_properties) == 0:
            new_props = ''
        else:
            new_props = yaml.safe_dump(s.__wf_properties, default_flow_style=False)
        new_desc += '\n-- swm properties --\n' + new_props.strip()

        s.__bug.description = new_desc
        s.__modified = False

    def __update_cycle_tag(s, new_cycle, new_spin):
        '''
        Internal helper to be called whenever new values are assigned to
        the cycle string or spin number.
        '''
        if s._cycle == new_cycle and s.spin_nr == new_spin:
            return
        s._cycle = new_cycle
        s._spin_nr = new_spin

        new_tag = 'kernel-sru-cycle-%s-%i' % (new_cycle, new_spin)
        s.__replace_pfx_tag('kernel-sru-cycle-', new_tag)

    @property
    def id(s):
        '''
        The bug ID of the underlying launchpad bug (read-only).

        :type: int
        '''
        return int(s.__bug.id)

    @property
    def title(s):
        '''
        The title of the underlying launchpad bug (read-only).

        :type:  str
        '''
        return s.__bug.title

    @property
    def cycle(s):
        '''
        The cycle tag (if set) for the tracking bug or None. This tag
        is without the spin number.

        :type: str
        '''
        return s._cycle

    @cycle.setter
    def cycle(s, cycle):
        if not isinstance(cycle, str):
            raise TrackingBugError('Must be a string')
        s.__update_cycle_tag(cycle, s._spin_nr)

    @property
    def spin_nr(s):
        '''
        The spin number (default 1) for the tracking bug.

        :type: int
        '''
        return s._spin_nr

    @spin_nr.setter
    def spin_nr(s, spin_nr):
        if not isinstance(spin_nr, int):
            raise TrackingBugError('Must be an integer')
        if spin_nr < 1:
            raise TrackingBugError('Must be at least 1')
        s.__update_cycle_tag(s._cycle, spin_nr)

    @property
    def target_package(s):
        '''
        The name of the source package with the tracking bug is
        targetting (read-only).

        :type: str
        '''
        return s._target_package

    @property
    def target_version(s):
        '''
        The version number of the source package which is tracked
        by this tracking bug (writeable).

        Assigning a new value will also update the title of the underlying
        launchpad bug.

        :type: str
        '''
        return s._target_version

    @target_version.setter
    def target_version(s, version):
        s._target_version = version
        s.__bug.title = '{}: {} -proposed tracker'.format(s._target_package, version)

    @property
    def target_series(s):
        '''
        The (code-) name of the release which the tracked source package
        is targetting (read-only).

        :type: str
        '''
        return s._target_series

    @property
    def master_bug_id(s):
        '''
        The launchpad bug ID of the tracking bug of which the current
        tracking bug is a derivative of. Or none if this is a master
        (read-only)
        '''
        return s._master_bug_id

    def __master_bug_id_set(s, ref_tb):
        '''
        Internal helper to set the master bug ID of a derivative tracking
        bug when it gets added to a master tracking bug. If the reference
        is None, then unset the master bug ID.
        '''
        if ref_tb is None:
            if s._master_bug_id is not None:
                tag2del = 'kernel-sru-{}-of-{}'.format(s.__type, str(s._master_bug_id))
                if tag2del in s.__bug.tags:
                    s.__bug.tags.remove(tag2del)
            s.__type = 'master'
            s._master_bug_id = None
            del(s.__wf_properties['kernel-stable-master-bug'])
            s.__update_desc()
            return

        if not isinstance(ref_tb, TrackingBug):
            raise TrackingBugError('reference must be a TrackingBug object')

        if s._target_series == ref_tb.target_series:
            s.__type = 'derivative'
        else:
            s.__type = 'backport'
        s._master_bug_id = ref_tb.id
        s.__wf_properties['kernel-stable-master-bug'] = s._master_bug_id
        s.__update_desc()
        prefix = 'kernel-sru-{}-of-'.format(s.__type)
        s.__replace_pfx_tag(prefix, prefix + str(s._master_bug_id))
        
    @property
    def derivative_bug_ids(s):
        '''
        A list of tracking bug IDs which track a derivative source of
        this tacking bug (read-only).

        :type: [ int ... ]
        '''
        return s._derivative_bug_ids.keys()

    @property
    def isdev(s):
        '''
        Indicates whether the tracking bug is targetting a development
        series or not (read-only).

        :type: Bool()
        '''
        if s._isdev is not None:
            return s._isdev

        if s._target_series is not None:
            series = s.__kernel_series.lookup_series(codename=s._target_series)
            if series and series.development:
                s._isdev = True
            else:
                s._isdev = False
        else:
            return False

        return s._isdev

    @property
    def wf_properties(s):
        '''
        A list of SWM properties (keys) defined for this tracking bug
        (read-only). The values can be fetched/set via wf_get_property
        and wf_set_property.

        :type: [ str ... ]
        '''
        return s.__wf_properties.keys()

    @property
    def wf_tasks(s):
        '''
        :return: A list of all defined workflow tasks.
        :rtype: [ str ... ]
        '''
        wf_name   = s.__wf_project.display_name
        wf_tasks  = []

        for task in s.__bug.tasks:
            task_name = task.bug_target_display_name
            parts = task_name.partition(wf_name)

            if parts[1] == wf_name:
                # Skip the main workflow task
                if parts[0] == '' and parts[2] == '':
                    continue
                wf_tasks.append(parts[2].strip())

        return wf_tasks

    def tags_reset(s, testing=False):
        '''
        Set the bug up with it's initial set of tags. If this is an existing
        tracking bug and we are resetting it to the default then we should
        remove any/all existing tags.
        '''
        center(s.__class__.__name__ + '.tags_reset')
        tags_to_set = []

        # Target series tag
        if s._target_series is not None:
            tags_to_set.append(s._target_series)

        # Query the workflow for the base set of tags
        for itag in s.__wf.initial_tags(s._target_package, s.isdev):
            if itag == s.__tbd.tag_names['default']['valid'] and testing:
                itag = s.__tbd.tag_names['testing']['valid']
            tags_to_set.append(itag)

        # If there is a cycle set, also create the cycle tag.
        if s._cycle is not None:
            itag  = s.__tbd.tag_names['default']['cycle'] + s._cycle
            itag += '-' + str(s._spin_nr)
            tags_to_set.append(itag)

        # If master bug ID is set ...
        if s._master_bug_id is not None:
            itag  = s.__tbd.tag_names[tagset_key][s.__type]
            itab += str(s._master_bug_id)
            tags_to_set.append(itag)

        # Now run through all existing tags and remove all those which
        # are not in the set to be added, but if they are, drop them
        # from the set to be added instead.
        for itag in s.__bug.tags:
            if itag in tags_to_set:
                tags_to_set.remove(itag)
            else:
                s.__bug.tags.remove(itag)

        # And finally add those which remain.
        for itag in tags_to_set:
            s.__bug.tags.append(itag)

        cleave(s.__class__.__name__ + '.tags_reset')

    def subscribers_add(s):
        '''
        Subscribe teams/individuals based on the target package name to the
        tracking bug.
        '''
        center(s.__class__.__name__ + '.subscribers_add')
        for subscriber in s.__wf.subscribers(s._target_package, s.isdev):
            try:
                lp_subscriber = s.__bug.service.launchpad.people[subscriber]
            except KeyError:
                cinfo('Cannot subscribe "{}", name not found in Launchpad!'.format(subscriber))
                continue
            s.__bug.lpbug.subscribe(person=lp_subscriber)
        cleave(s.__class__.__name__ + '.subscribers_add')

    def wf_status_get(s):
        '''
        Retrieves the status of the workflow project task.

        :rtype: str
        '''
        center(s.__class__.__name__ + '.wf_status_get')
        wf_name = s.__wf_project.display_name
        status = ''
        for task in s.__bug.tasks:
            task_name = task.bug_target_display_name
            parts = task_name.partition(wf_name)
            if parts[0] == '' and parts[1] == wf_name and parts[2] == '':
                status = task.status
                break
        cleave(s.__class__.__name__ + '.wf_status_get')
        return status

    def wf_status_set(s, status):
        '''
        Sets the status of the workflow project task to the given
        status.

        :param status: New status
        :type  status: Valid workflow status string
        '''
        center(s.__class__.__name__ + '.wf_status_set')
        wf_name = s.__wf_project.display_name
        for task in s.__bug.tasks:
            task_name = task.bug_target_display_name
            parts = task_name.partition(wf_name)
            if parts[0] == '' and parts[1] == wf_name and parts[2] == '':
                task.status = status
                task.importance = "Medium"
        cleave(s.__class__.__name__ + '.wf_status_set')

    def wf_task_get(s, task_name):
        '''
        Get the task of a workflow task which can then be modified
        directly.

        :param task_name: The task name as returned by wf_tasks
        :type  task_name: str

        :rtype: lptk.bug_task()
        '''
        center(s.__class__.__name__ + '.wf_task_get')
        wf_name = s.__wf_project.display_name
        for task in s.__bug.tasks:
            parts = task.bug_target_display_name.partition(wf_name)

            if parts[1] == wf_name and parts[2].strip() == task_name:
                    cleave(s.__class__.__name__ + '.wf_task_get')
                    return task

        cleave(s.__class__.__name__ + '.wf_task_get -> None')
        return None

    def derivative_add(s, ref_tb):
        '''
        Add the given tracking bug as a derivative/backport of the
        current tracking bug. This also will set the current tracking
        bug as the master of the derivative tracking bug

        :param ref_tb: The tracking bug which should become a derivative
            of the current tracking bug.
        :type  ref_tb: TrackingBug()
        '''
        if not isinstance(ref_tb, TrackingBug):
            raise TrackingBugError('reference must be a tracking bug')
        if ref_tb.id in s._derivative_bug_ids:
            return
        ref_series = ''
        ref_name   = ref_tb.target_package
        if ref_tb.target_series != s._target_series:
            ref_series = ref_tb.target_series
        if 'variant' in ref_tb.__wf_properties.keys():
            if ref_tb.__wf_properties['variant'] == 'snap-debs':
                ref_name = ref_tb.__wf_properties['snap-name']
        s._derivative_bug_ids[ref_tb.id] = [ ref_series, ref_name ]
        s.__modified = True
        ref_tb.__master_bug_id_set(s)
        s.save()

    def derivative_remove(s, ref_tb):
        '''
        Remove the given tracking bug from being a derivative/backport
        of the current tracking bug. This also unsets the master bug
        reference in the givven tracking bug.

        :param ref_tb: The tracking bug to be removed. Must be a valid
                       derivative tracking bug object linked to the
                       current tracking bug or will raise an exception.
        :type  ref_tb: TrackingBug()
        '''
        if not isinstance(ref_tb, TrackingBug):
            raise TrackingBugError('reference must be a tracking bug')
        if ref_tb.id not in s._derivative_bug_ids:
            raise TrackingBugError('reference is not a derivative')
        del(s._derivative_bug_ids[ref_tb.id])
        s.__modified = True
        ref_tb.__master_bug_id_set(None)
        s.save()

    def make_duplicate_of(s, ref_tb):
        '''
        Mark the current tracking bug as a duplicate of the given one.
        This does not update any master or derivative references.

        :param ref_tb: The tracking bug which the current one should
                       be a duplicate of.
        :type  ref_tb: TrackingBug()
        '''
        if not isinstance(ref_tb, TrackingBug):
            raise TrackingBugError('reference must be a tracking bug')
        if ref_tb.target_series != s._target_series:
            raise TrackingBugError('reference series mismatch')
        if ref_tb.target_package != s._target_package:
            raise TrackingBugError('reference source mismatch')
        s.__bug.lpbug.duplicate_of = ref_tb.__bug.lpbug
        s.__bug.lpbug.lp_save()

    def invalidate(s, hard=False):
        '''
        Invalidate all tasks of the tracking bug and remove all
        search tags.

        :param hard: Invalidate and also remove any cycle tag(s). This will prevent
                     finding the bug again while looking for closed tracking bugs
                     of a certain cycle.
        :type  hard: Boolean
        '''
        center(s.__class__.__name__ + '.invalidate({}, {})'.format(s.id, hard))
        current_tags = s.__bug.tags
        for tag in current_tags:
            if tag == s.__tbd.tag_names['default']['valid']:
                s.__bug.tags.remove(tag)
            elif tag == s.__tbd.tag_names['testing']['valid']:
                s.__bug.tags.remove(tag)
            elif tag.startswith('kernel-sru-cycle-') and hard == True:
                s.__bug.tags.remove(tag)

        for task in s.__bug.tasks:
            task.status = 'Invalid'
        cleave(s.__class__.__name__ + '.invalidate')

    def tasks_reset(s):
        '''
        Reset all tasks of the tracking bug to their default values
        (assignee, status).
        '''
        center(s.__class__.__name__ + '.tasks_reset')
        wf_name   = s.__wf_project.display_name
        ct_series = s._target_series.capitalize()

        # Fetch the list of invalid tasks according to the kernel-series
        # information.
        try:
            ks = s.__kernel_series
            ks_series = ks.lookup_series(codename=s._target_series)
            ks_source = ks_series.lookup_source(s._target_package)
            ks_invalid_tasks = ks_source.invalid_tasks
        except:
            ks_invalid_tasks = []

        # Set task assignments and importance. Main project task must be
        # set to In Progress for the bot to do its processing.
        cdebug('')
        cdebug('Setting status and importance', 'blue')
        cdebug('* series: {}'.format(ct_series))
        for task in s.__bug.tasks:
            task_name = task.bug_target_display_name
            cdebug('* {}'.format(task_name), 'cyan')
            parts = task_name.partition(wf_name)

            if not s.isdev and 'linux' in parts[0] and ct_series not in parts[0]:
                # The main linux task? [linux (Ubuntu)]
                task.status = 'Invalid'
                cdebug('  - is main linux task', 'white')
                cdebug('  - status: {}; importance: {}'.format(task.status, task.importance), 'green')
            elif parts[0] == '' and parts[1] == wf_name and parts[2] == '':
                # This is the main SRU Workflow task
                continue
            elif parts[0] != '':
                # The series nomination of the package (linux) task?
                cdebug('  - is the target series of the linux task', 'white')
                try:
                    task.importance = 'Medium'
                except:
                    if ct_series not in parts[0]:
                        cwarn('Failed to set the task ({}) importance to "Medium".'.format(task_name))
                cdebug('  - status: {}; importance: {}'.format(task.status, task.importance))
                continue
            else:
                # Else, it must be one of the SRU Workflow tasks.
                cdebug('  - is a SRU workflow task', 'white')

                # All workflow tasks are "Medium" importance
                task.importance = 'Medium'
                task.status = 'New'

                # Determine and set the assignee.
                task_name = parts[2].strip()
                try:
                    assignee = s.__wf.assignee_ex(s._target_series, s._target_package, task_name, s.isdev)
                except DefaultAssigneeMissing as e:
                    cwarn('  ! {}'.format(str(e)))
                    continue
                if assignee is None:
                    cinfo('Found workflow task ({}) with no default assignee'.format(task_name))
                    cinfo('Leaving unassigned and setting to invalid')
                    task.status = 'Invalid'
                    cdebug('  - status: Invalid')
                else:
                    lp = s.__bug.service.launchpad
                    try:

                        task.assignee = lp.people[assignee]
                        cdebug('  - assigning: {}'.format(task.assignee.display_name))
                    except:
                        cinfo('Cannot assign "{}", not found in Launchpad!'.format(assignee))

                # Determine and mark appropriate tasks Invalid
                if s._target_version is not None:
                    lin_ver = re.findall('([0-9]+\.[^-]+)', s._target_version)
                    if lin_ver:
                        lin_ver = lin_ver[0]
                        if not s.isdev and s.__wf.is_task_invalid(s._target_package, task_name, lin_ver):
                            task.status = 'Invalid'
                            cdebug('  - status: Invalid')
                            continue

                if task_name in ks_invalid_tasks:
                    task.status = 'Invalid'
                    cdebug('  - status: Invalid')
                    continue
#
#                if not self.new_abi and task_name.startswith('prepare-package-') and task_name != 'prepare-package-signed':
#                    task.status = "Invalid"
#                    cdebug('        status: Invalid')
#
        cleave(s.__class__.__name__ + '.tasks_reset')

    def save(s):
        '''
        Try to write out any pending changes. At this time this would
        be changes to the description section of the underlying Launchpad
        bug (like derivatives/backports list and SWM properties.
        '''
        center(s.__class__.__name__ + '.save')
        if s.__modified:
            try:
                s.__update_desc()
                s.__modified = False
            except:
                raise
        cleave(s.__class__.__name__ + '.save')

    def set_cycle_and_spin(s, cycle, spin_nr):
        '''
        Set a new cycle tag and spin number on the tracking bug.

        :param cycle: New cycle tag
        :type  cycle: str

        :param spin_nr: New spin number (>= 1)
        :type  spin_nr: int
        '''
        if not isinstance(cycle, str):
            raise TrackingBugError('Must be a string <cycle>')
        if not isinstance(spin_nr, int):
            raise TrackingBugError('Must be an integer <spin_nr>')
        if spin_nr < 1:
            raise TrackingBugError('Must be at least 1 <spin_nr>')
        s.__update_cycle_tag(cycle, spin_nr)

    def wf_get_property(s, key):
        '''
        Fetch the value of a SWM property (or None if not found).

        :param key: Name of the SWM property to get.
        :type  key: str

        :type: opaque
        '''
        center(s.__class__.__name__ + '.wf_get_property')
        value = None
        if key in s.__wf_properties:
            value = s.__wf_properties[key]

        cleave(s.__class__.__name__ + '.wf_get_property')
        return value

    def wf_set_property(s, key, value):
        '''
        Set a SWM property named <key> to <value>. Does not immediately
        update the underlying Launchpad bug, use save() to do that.

        :param key: Name of the SWM property to set.
        :type  key: str

        :param value: Content of the SWM property
        :type  value: opaque
        '''
        s.__wf_properties[key] = value
        s.__modified = True

class TrackingBugs():
    '''
    This class represents a collection of tracking bugs. It should be
    the primary interface for every application.

    The main interface should resemble a dictionary with the launchpad
    bug ID as its key. But additional methods are provided to allow
    other forms of searches.
    '''
    __tbd = TrackingBugDefines()

    def __add_to_set(s, new_tb):
        '''
        Internal helper to add a tracking bug object into the set and update
        indexes.
        '''
        if not isinstance(new_tb, TrackingBug):
            raise TrackingBugError('not a tracking bug object')
        s.__tbs[int(new_tb.id)] = new_tb
        sd = s.__idx_pkg_by_series.setdefault(new_tb.target_series, {})

        sourcename = new_tb.target_package
        snapname = new_tb.wf_get_property('snap-name')
        if snapname is not None:
            sourcename = '{}/{}'.format(sourcename, snapname)
        sd.setdefault(sourcename, set()).add(int(new_tb.id))

    def __init__(s, wf_project_name=TRACKINGBUG_DEFAULT_PROJECT, testing=False, quiet=False, private=False):
        '''
        Create a new empty set of tracking bugs.

        :param wf_project_name:
            The name of the launchpad project which is used to hold the
            workflow tasks (tasks are mapped to series in launchpad).
            MAYBE DROP
        :type: str

        :param testing:
            Run in test or production mode (default). When running in
            testing mode creation and lookup of tracking bugs will be
            made using a special tag.
        :type: Bool

        :param quiet:
            Produce output (default) or be quiet about what is going on
            internally.
            MAYBE DROP
        :type: Bool

        :param private:
            All tracking bugs in the set should be private bugs
        :type: Bool
        '''
        # Get a new instance of LaunchpadService for each new instance
        # of TrackingBugs().
        try:
            defaults = {
                'launchpad_client_name' : 'trackingbugs-library',
            }
            s.__lps = LaunchpadService(defaults)
        except LaunchpadServiceError as e:
            print(e.msg)
            raise

        s.__ks = KernelSeries()
        s.__wf = Workflow()
        s.__idx_pkg_by_series = {}
        s.__tbs = {}
        s.project = wf_project_name
        s.testing = testing
        s.quiet   = quiet
        s.private = private

    def __len__(s):
        '''
        :return: Number of tracking bugs defined in this collection.
        :rtype: int
        '''
        return len(s.__tbs)

    def __getitem__(s, bug_id):
        '''
        TrackingBugs[bug_id] -> TrackingBug() | None

        :return: The tracking bug defined under the given launchpad bug ID.
        :rtype: TrackingBug()
        '''
        return s.__tbs[bug_id]

    def __delitem__(s, bug_id):
        '''
        del(TrackingBugs[bug_id])

        Removes a tracking bug from the collection of tracking bugs and
        updates all indices. NOTE: Does not invalidate the embedded LP
        bug.

        :param bug_id: The LP bug ID to be removed
        :type  bug_id: int
        '''
        tb = s.__tbs[bug_id]
        sd = s.__idx_pkg_by_series[tb.target_series]
        pd = sd[tb.target_package]
        pd.remove(bug_id)
        if len(pd) == 0:
            pd = None
            del(sd[tb.target_package])
            if len(sd) == 0:
                sd = None
                del(s.__idx_pkg_by_series[tb.target_series])
        del(s.__tbs[bug_id])

    def __iter__(s):
        for tb in s.__tbs:
            yield tb

    @property
    def bug_ids(s):
        '''
        A list of Launchpad bugs (IDs) which are currently part of the
        TrackingBugs() set (read-only).

        :type: list()
        '''
        return list(s.__tbs)

    @property
    def series_names(s):
        '''
        A list of series names (codenames of releases) for which
        tracking bugs exist in the current collection (read-only).

        :type: list()
        '''
        sl = []

        for series in sorted(s.__ks.series, key=lambda k: k.name, reverse=True):
            if series.codename in s.__idx_pkg_by_series:
                sl.append(series.codename)

        return sl

    @property
    def cycle_tags(s):
        '''
        A set of unique cycle tags which are defined in the current
        collection of tracking bugs (read-only).

        :type: set()
        '''
        cl = set()

        for tbid in s.__tbs:
            if s.__tbs[tbid].cycle is not None:
                cl.add(s.__tbs[tbid].cycle)

        return cl

    def add(s, bug_id):
        '''
        Adds a single tracking bug from an existing launchpad bug and
        refreshes internal indexes. Can throw an exception.

        :param bug_id: A Launchpad bug ID pointing to the bug to be
            imported.
        :type: int

        :returns: New tracking bug object
        :rtype: TrackingBug()
        '''
        center(s.__class__.__name__ + '.add({})'.format(bug_id))
        if bug_id not in s.__tbs:
            try:
                tb = TrackingBug(Bug(s.__lps, bug_id))
                s.__add_to_set(tb)
            except TrackingBugError as e:
                msg = 'failed to add bug ({})'.format(e.msg)
                raise TrackingBugError(msg)

        cleave(s.__class__.__name__ + '.add')
        return tb

    def load(s, series_filter=[], tag_filter=[], debug=False):
        '''
        Load a set of tracking bugs from Launchpad which match
        the given filters (default all live tracking bugs).

        :param series_filter: List of series (codenames of releases)
            for which tracking bug data should get loaded.
        :type  series_filter: []

        :param tag_filter: List of tags to be used in the Launchpad
            task search (instead of the live tracking bug tag).
        :type  tag_filter: []

        :param debug: Print status info while working on the task.
        :type  debug: Bool()
        '''
        center(s.__class__.__name__ + '.load')

        valid_states = [
            'New',
            'Confirmed',
            'Triaged',
            'In Progress',
            'Incomplete',
            'Fix Committed',
            'Fix Released',
            'Invalid',
        ]

        if len(tag_filter) > 0:
            search_tag = tag_filter
        else:
            if s.testing:
                search_tag = s.__tbd.tag_names['testing']['valid']
            else:
                search_tag = s.__tbd.tag_names['default']['valid']

        #tasks = s.__lps.launchpad.projects[s.project].searchTasks(
        tasks = s.__lps.launchpad.bugs.searchTasks(
                    tags=search_tag,
                    order_by='id',
                    status=valid_states)

        bug_ids = []
        for task in tasks:
            tlink = task.target_link
            # Is this a snap-debs task in that case the series is part of the title.
            # To make things not that easy the tasks.title is something in the form:
            #  'Bug #[0-9]+ in Kernel SRU Workflow: "<series>/<source>: ..."'
            if 'snap-debs' in task.title and tlink.endswith('kernel-sru-workflow'):
                series = task.title.split('"')[1].split(':')[0].split('/')[0]
                if len(series_filter) > 0 and series not in series_filter:
                    continue
                bug_ids.append(task.self_link.split('/')[-1])
                continue

            # Only interested in the <package> tasks in the ubuntu project
            # because that has info about the target series codename.
            if '/ubuntu/' not in tlink:
                continue
            if '/ubuntu/+source/' in tlink:
                continue
            series = tlink.partition('/+source/')[0].split('/')[-1]
            if len(series_filter) > 0:
                if series not in series_filter:
                    continue
            bug_ids.append(task.self_link.split('/')[-1])

        if debug:
            print('Gathering details for %i tracking bugs' % len(bug_ids))

        cnt = 0
        for bug_id in bug_ids:
            try:
                s.add(bug_id)
                cnt = cnt + 1
                if debug:
                    print('\rInstantinating bugs... %i' % cnt, end='', flush=True)
            except TrackingBugError as e:
                cerror('LP: #%i: %s (skipped)' % (bug_id, e.msg))
                pass
        if debug:
            print('')

        cleave(s.__class__.__name__ + '.load')
        return s

    def get_series_package(s, series_name, package_name):
        center(s.__class__.__name__ + '.get_series_package')
        bug_list = []
        if series_name in s.__idx_pkg_by_series:
            sidx = s.__idx_pkg_by_series[series_name]
            if package_name in sidx:
                for bug_id in sidx[package_name]:
                    bug_list.append(bug_id)

        cleave(s.__class__.__name__ + '.get_series_package')
        return bug_list

    def __wf_task_valid(s, wf_series, ks_source, variant):
        '''
        Internal helper to decide whether a certain workflow task should be
        added to a launchpad bug.

        Returns: True (task is valid) or False (otherwise)
        '''
        retval = False
        ks_series = ks_source.series

        #
        # FIXME: This probably should be taken from workflow
        #   s.__wf.devel_workflow['default']['task_assignment'].keys()
        #
        # There is one difference stakeholder-signoff is not there and
        # prepare-package-lbm is not here.
        valid_dev_tasks = [
            'automated-testing',
            'prepare-package',
            'prepare-package-meta',
            'prepare-package-signed',
            'promote-to-proposed',
            'promote-to-release',
            'regression-testing',
            'stakeholder-signoff',
        ]

        while True:
            if not wf_series.active:
                break
            if wf_series.name in ['trunk', 'latest']:
                break
            if wf_series.name.endswith('-dnu'):
                cdebug('    {} marked "do not use"'.format(wf_series.name[:-4]), 'yellow')
                break

            if ks_series.development and wf_series.name not in valid_dev_tasks:
                break

            # SELECT: drop any series for a different variant.
            if variant in ("debs"):
                if wf_series.name.startswith('snap-'):
                    cdebug('    off-variant no {} '.format(wf_series.name), 'yellow')
                    break
            elif variant in ("snap-debs"):
                if not wf_series.name.startswith('snap-'):
                    cdebug('    off-variant no {}'.format(wf_series.name), 'yellow')
                    break

            # DEBS: exclusions related to debs.
            if wf_series.name.startswith('prepare-package-'):
                pkg_type = wf_series.name.replace('prepare-package-', '')
                ks_pkg = None
                for entry in ks_source.packages:
                    if entry.type == pkg_type:
                        ks_pkg = entry
                        break
                if ks_pkg is None:
                    cdebug('    no {}'.format(wf_series.name), 'yellow')
                    break
            if wf_series.name == 'stakeholder-signoff':
                if ks_source.stakeholder is None:
                    cdebug('    no stakeholder-signoff', 'yellow')
                    break
            elif wf_series.name == 'promote-signing-to-proposed':
                ks_route = ks_source.routing
                if ks_route is not None:
                    ks_dst = ks_route.lookup_destination('signing')
                else:
                    ks_dst = None

                if ks_dst is None:
                    cdebug('    no promote-signing-to-proposed', 'yellow')
                    break

            if wf_series.name == 'promote-to-release' and ks_series.development is False:
                break

            # SNAPS: exclusions related to snaps.
            if wf_series.name.startswith('snap-'):
                snap = None
                for entry in ks_source.snaps:
                    if entry.primary:
                        snap = entry
                        break
                if snap is None:
                    cdebug('    no {}'.format(wf_series.name), 'yellow')
                    break
                if wf_series.name == 'snap-certification-testing':
                    if not snap.hw_cert:
                        cdebug('    no {}'.format(wf_series.name), 'yellow')
                        break
                elif wf_series.name == 'snap-qa-testing':
                    if not snap.qa:
                        cdebug('    no {}'.format(wf_series.name), 'yellow')
                        break
                elif wf_series.name == 'snap-publish':
                    if not snap.gated:
                        cdebug('    no {}'.format(wf_series.name), 'yellow')
                        break

            retval = True
            break

        return retval

    def create(s, series_name, pkg_name, name=None, variant='combo'):
        '''
        Create a new tracking bug (and a launchpad bug which backs it). The
        new tracking bug wil not have any of those elements set:
          - cycle tag       -> tb.cycle = <tag without spin_nr>
          - spin_nr         -> tb.spin_nr = <nr>
          - workflow status -> tb.wf_status_set(<status>)

        :param series_name: Codename of the distro series for which the
            tracking bug is for.
        :type: str

        :param pkg_name: The name of the package/snap
        :type: str

        :param variant: What kind of package is tracked by this tracking
            bug. Currently there are 'combo', 'debs', and 'snap-debs'
            tracker.

        :type: str

        :returns: New tracking bug object (added to the set as well).
        :rtype: TrackingBug()
        '''
        center(s.__class__.__name__ + '.create')
        new_tb = None

        cdebug('Series:        %s' % series_name)
        cdebug('Package:       %s' % pkg_name)
        cdebug('Variant:       %s' % variant)
        cdebug('Testing:       %s' % s.testing)

        #
        # Figure out whether the package name is known
        #
        lps     = s.__lps
        lp      = lps.launchpad
        ubuntu  = lp.distributions['ubuntu']

        for distro_series in ubuntu.series_collection:
            # cdebug('ubuntu.series: %s' % distro_series.name)
            if distro_series.name == series_name:
                break
        if distro_series is None or distro_series.name != series_name:
            err = '{} is no valid series name'.format(series_name)
            raise TrackingBugError(err)

        ks_series = s.__ks.lookup_series(codename=series_name)
        if ks_series is None:
            err = '{} is not defined in KernelSeries'.format(series_name)
            raise TrackingBugError(err)
        else:
            ks_source = ks_series.lookup_source(pkg_name)
        if ks_source is None:
            err = '{} is no defined source in {}'.format(pkg_name, series_name)
            raise TrackingBugError(err)

        # Title string for launchpad bug
        if variant in ('debs', 'combo'):
            description = '-proposed tracker'
        else:
            description = variant
        title = '{}: {} {}'.format(pkg_name, s.__tbd.no_version, description)
        # Initial description
        desc  = s.__tbd.desc_tmpl

        cdebug('Creating bug for {}'.format(s.project), 'blue')

        wf_project = lps.projects[s.project]
        target = lp.load(wf_project.self_link)
        try:
            lp_bug = lp.bugs.createBug(target=target, title=title,
                           description=desc, tags=[], private=s.private)
            cdebug('LP: #{} was created'.format(lp_bug.id))
        except:
            raise TrackingBugError('failed to create embedded LP bug')

        # First add all of the workflow tasks
        for wf_task in wf_project.lp_project.series_collection:
            if s.__wf_task_valid(wf_task, ks_source, variant):
                cdebug('    adding: %s' % wf_task.display_name)
                nomination = lp_bug.addNomination(target=wf_task)
                if nomination.canApprove():
                    nomination.approve()

        # Add the series marker.
        tags = lp_bug.tags
        # This tag prevents the Ubuntu kernel bot from asking for logs.
        # We want that to be set as soon as possible (or at least before
        # there is a linux package task.
        tags.append('kernel-release-tracking-bug')
        tags.append(series_name)
        lp_bug.tags = tags
        lp_bug.lp_save()

        # Then add a package task for the ubuntu project
        lptk_bug = None
        if variant in ('debs', 'combo'):
            ubuntu_project = lps.projects['ubuntu']
            lp_package     = pkg_name
            target         = lp.load(ubuntu_project.self_link + '/+source/' + lp_package)

            # Try to add an Ubuntu task for the source (to be nominated for
            # the target series). This can fail if the source was never published.
            try:
                cdebug('Adding {} task.'.format(lp_package), 'blue')
                task = lp_bug.addTask(target=target)
                task.status = 'Confirmed'
            except:
                cwarn('The {} source was not published. Re-trying with "linux"'.format(lp_package))
                lp_package = 'linux'
                target     = lp.load(ubuntu_project.self_link + '/+source/' + lp_package)

                try:
                    cdebug('Adding fallback "linux" task.', 'blue')
                    task = lp_bug.addTask(target=target)
                    task.status = 'Invalid'
                except:
                    # Invalidate all tasks added so far
                    for task in lp_bug.tasks:
                        task.status = 'Invalid'
                    raise TrackingBugError('failed adding the source package task')

            nomination = lp_bug.addNomination(target=distro_series)
            if nomination.canApprove():
                nomination.approve()

                # Clone the package task status into the now approved nomination task
                # (while we still have the info).
                saved_status = task.status
                cseries      = series_name.capitalize()
                lptk_bug     = lps.get_bug(lp_bug.id)
                for task in lptk_bug.tasks:
                    if cseries in task.bug_target_display_name:
                        task.status = saved_status

        # Finally build a real tracking bug.
        cdebug('Creating new TrackingBug() object')
        # Convert raw LP bug into LPTK bug for tracking bug creation
        # (if not already done)
        if lptk_bug is None:
            lptk_bug = lps.get_bug(lp_bug.id)
        try:
            new_tb = TrackingBug(lptk_bug, wf_project_name=s.project)
        except:
            # Invalidate all tasks added so far
            for task in lptk_bug.tasks:
                task.status = 'Invalid'
            raise TrackingBugError('failed to instantinate tracking bug')
        new_tb.tasks_reset()
        new_tb.tags_reset(testing=s.testing)
        if s.testing is False and s.private is False:
            new_tb.subscribers_add()

        # Add the variant tag.
        if variant != 'combo':
            new_tb.wf_set_property('variant', variant)
        if variant == 'snap-debs':
            new_tb.wf_set_property('snap-name', name)

        # Ensure any changes are sync'd to the bug.
        new_tb.save()

        s.__add_to_set(new_tb)
        cleave(s.__class__.__name__ + '.create')

        return new_tb


if __name__ == '__main__':
    print('Begin %s selftests...' % (__file__))
    pass_count = 0
    fail_count = 0
    basicConfig(level='DEBUG')

    #tbs = TrackingBugs(testing=True).load()
    #if len(tbs) > 0:
    #    print('WW: Expected 0 test tracking bugs bug got %i' % len(tbs))
    #    fail_count += 1
    #else:
    #    print('II: PASS: 0 test tracking bugs found.')
    #    pass_count += 1

    print('II: Test loading the complete set of live tracking bugs...')
    try:
        tbs = TrackingBugs().load(debug=True)
        print('II: PASS')
        pass_count += 1
    except:
        print('EE: FAIL')
        fail_count += 1
        raise

    #print(tbs.cycle_tags)

    #if len(tbs.series_names) > 0:
    #    sfilter = [ tbs.series_names[0] ]
    #else:
    #    sfilter = [ 'bionic' ]

    
    #sfilter = [ 'bionic' ]
    #print('II: Test loading filtered %s set...' % sfilter)
    #try:
    #    tbs = TrackingBugs().load(series_filter=sfilter, debug=True)
    #    for tbid in tbs:
    #        tb = tbs[tbid]
    #        print('* %i: %s' % (tb.id, tb.title))
    #        print('  Cycle: %s / Spin: %s' % (tb.cycle, tb.spin_nr))
    #        print('  Pkgname: %s' % tb.target_package)
    #        print('  Pkgvers: %s' % tb.target_version)
    #        print('  Pkgseries: %s' % tb.target_series)
    #        print('  Master: %s' % tb.master_bug_id)
    #        print('  Derivatives: %s' % tb.derivative_bug_ids)
    #        print('  Properties: %s' % tb.wf_properties)

    #    tb_list = tbs.get_series_package('bionic', 'linux')
    #    if tb_list is not None:
    #        print('Derivatives of this bug:')
    #        for tb_id in tbs[tb_list[0]].derivative_bug_ids:
    #            if tb_id not in tbs:
    #                print('  + Fetching LP: #%i' % tb_id)
    #                tbs.add(tb_id)
    #            tb = tbs[tb_id]
    #            print('  - LP: #%i: %s/%s' % (tb_id, tb.target_series, tb.title))

    #    print('II: PASS')
    #    pass_count += 1
    #except:
    #    raise

    #if fail_count == 0:
    #    print('PASS: %i tests passed' % (pass_count))
    #else:
    #    print('FAIL: %i of %i tests failed' (fail_count, fail_count + pass_count))
    tbs = TrackingBugs(testing=True, private=True)
    #master = tbs.create('bionic', 'linux')
    master = tbs.add(1808511)
    #master.reset_tasks()
    #master.cycle = 't2018.12.14'
    #master.wf_set_property('target-series', 'bionic')
    #master.save()
    #master.tags_reset(testing=True)
    #derivative = tbs.create('bionic', 'linux-raspi2')
    derivative = tbs.add(1808545)
    #derivative.tags_reset(testing=tbs.testing)
    #backport = tbs.create('xenial', 'linux-hwe')
    backport = tbs.add(1808548)
    #master.derivative_add(derivative)
    #master.derivative_add(backport)
    print(master.wf_tasks)
    print(master.derivative_bug_ids)
    print(master.wf_task_get('upload-to-ppa').status)

    sys.exit(fail_count)

# vi:set ts=4 sw=4 expandtab:
