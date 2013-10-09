#!/usr/bin/env python
#

from argparse                           import ArgumentParser, RawDescriptionHelpFormatter
import re

from datetime                           import datetime

from ktl.bugs                           import DeltaTime
from ktl.ubuntu                         import Ubuntu

from sb.exceptions                      import GeneralError, ErrorExit
from sb.log                             import cinfo, cdebug, cerror, cwarn

# PackageError
#
class PackageError(GeneralError):
    '''
    Thrown when some basic information about the package that is associated with the
    shankbug could not be determined.
    '''
    def __init__(s, emsg):
        GeneralError(emsg)

class PackageInfo():
    def __init__(s, txt):
        matched = False
        #                              .- package name (group(1))
        #                             /           .- kernel version (group(2))
        #                            /           /          .- version/abi separator (group(3))
        #                           /           /          /
        ver_rc     = re.compile("(\S+): (\d+\.\d+\.\d+)([-\.])(\d+)\.(\d+)([~a-z\d]*)")
        #                                                       /      /       /
        #                                                      /      /       .- backport extra (m.group(6))
        #                                                     /      .- upload number (m.group(5))
        #                                                    .- abi (group(4))

        #info('     Extract package info\n')
        setattr(s, 'valid', False)
        m = ver_rc.search(txt)
        if m is not None:
            matched = True
            #info('         package: %s\n' % m.group(1))
            #info('         version: %s%s%s.%s%s\n' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
            #info('          kernel: %s\n' % m.group(2))
            #info('             abi: %s\n' % m.group(4))

            setattr(s, 'name', m.group(1))
            setattr(s, 'version', '%s%s%s.%s%s' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
            setattr(s, 'kernel', m.group(2))
            setattr(s, 'abi', m.group(4))
            s.valid = True

        if not matched:
            cwarn(' ** None of the regular expressions matched the title (%s)' % txt)

# WorkflowBugTask
#
class WorkflowBugTask(object):
    # __init__
    #
    def __init__(s, lp_task, task_name):
        setattr(s, 'name', task_name)
        setattr(s, 'status', lp_task.status)
        setattr(s, 'importance', lp_task.importance)
        setattr(s, 'lp_task', lp_task)

        assignee    = lp_task.assignee
        if assignee is None:
            setattr(s, 'assignee', '*Unassigned')
        else:
            setattr(s, 'assignee', assignee.display_name)

# WorkflowBug
#
class WorkflowBug():
    # __init__
    #
    def __init__(s, lp, projects, bugid):
        s.lp = lp
        s.lpbug = s.lp.get_bug(bugid)
        s.projects = projects

        s.__package_name = None

        # If a bug isn't to be processed, detect this as early as possible.
        #
        s.is_valid = s.check_is_valid(s.lpbug)

        if s.is_valid:
            cinfo('    Targeted Project:')
            cinfo('        %s' % s.targeted_project)
            cinfo('')
            s.properties = s.lpbug.properties
            if len(s.properties) > 0:
                cinfo('    Properties:')
                for prop in s.properties:
                    cinfo('        %s: %s' % (prop, s.properties[prop]))

            s.tasks_by_name = s.create_tasks_by_name()

    # check_is_valid
    #
    def check_is_valid(s, bug):
        '''
        '''
        retval = True
        for t in s.lpbug.tasks:
            task_name       = t.bug_target_name

            if task_name in s.projects:
                s.targeted_project = task_name
                if t.status == 'In Progress':
                    continue
                else:
                    cinfo('        Not processing this bug because master task state is set to %s' % (t.status))
                    cinfo('        Quitting this bug')
                    retval = False

        return retval

    # create_tasks_by_name
    #
    def create_tasks_by_name(s):
        '''
        We are only interested in the tasks that are specific to the workflow project. Others
        are ignored.
        '''
        taskbyname = {}

        cinfo('')
        cinfo('    Scanning bug tasks:')

        for t in s.lpbug.tasks:
            task_name       = t.bug_target_name

            if task_name.startswith(s.targeted_project):
                if '/' in task_name:
                    task_name = task_name[len(s.targeted_project)+1:].strip()
                taskbyname[task_name] = WorkflowBugTask(t, task_name)
            else:
                cinfo('')
                cinfo('        %-25s' % (task_name))
                cinfo('            Action: Skipping non-workflow task')

        return taskbyname

# BS
#
class BS(object):
    '''
    Build Status
    '''
    # __init__
    #
    def __init__(s, status, package):
        '''
        0 - if the package-version wasn't found/published. In this case
            the package creator and assignee returned is always None
        1 - if the package-version is available (published), but still
            didn't finish building
        2 - package-version is available in the archive
        '''
        s.status = status
        s.package = package

    @property
    def is_built_and_published(s):
        return s.status == 2

# Package
#
class Package():

    # __init__
    #
    def __init__(s, lp, shankbug):
        s.ubuntu = Ubuntu()
        s.lp = lp
        s.__distro_series = None
        s.__is_new_abi = None

        ckt = s.lp.launchpad.people['canonical-kernel-team']
        s.ckt_ppa = ckt.getPPAByName(name='ppa')

        s.main_archive = s.lp.launchpad.distributions["ubuntu"].main_archive

        s.bug = shankbug

        # Determine some properties of the package we are looking at based on the
        # bug title. This information is used further on.
        #
        s.package = PackageInfo(s.bug.lpbug.title)
        if not s.package.valid:
            cwarn('        Unable to check package builds for this bug: either the package name or')
            cwarn('        the version are not properly indicated in the bug title.')
            raise PackageError(['Unable to check package builds for this bug: either the package name or',
                                'the version are not properly indicated in the bug title.'])

        s.pkgs = s.dependent_packages

        if s.bug.targeted_project == 'kernel-sru-workflow':
            s.is_stable_package = True
        else:
            s.is_stable_package = False

        s.package_version_not_found  = 0
        s.package_version_building   = 1
        s.package_version_in_archive = 2

        s.ignore_promotions = False

    # distro_series
    #
    @property
    def distro_series(s):
        '''
        Return the LP distro series link to the series associated with this version
        of this package.
        '''
        if s.__distro_series is None:
            series = s.ubuntu.series_name(s.package.name, s.package.version)
            if series:
                sc = s.lp.launchpad.distributions["ubuntu"].series_collection
                for ds in sc:
                    if ds.name == series:
                        s.__distro_series = ds
                        break

            if s.__distro_series is None:
                emsg = "        ERROR: can't figure out the distro series for %s-%s\n" % (s.package.name, s.package.version)
                cerror(emsg)
                raise ErrorExit(emsg)

        return s.__distro_series

    # is_new_abi
    #
    @property
    def is_new_abi(s):
        '''
        Try to determine if there was an abi change in this release. We
        guess this by looking if there is already a package with same
        abi in the updates/release pocket.
        '''
        cdebug('package::is_new_abi enter')
        if s.__is_new_abi is None:
            s.__is_new_abi = True
            if s.package.kernel and s.package.abi:
                st_abi_rel, _ = s.build_status(s.package.name, s.package.abi, s.main_archive, s.package.kernel, 'Release')
                st_abi_upd, _ = s.build_status(s.package.name, s.package.abi, s.main_archive, s.package.kernel, 'Updates')
                if st_abi_rel == 2 or st_abi_upd == 2:
                    s.__is_new_abi = False

        cdebug('package::is_new_abi leave (%s)' % s.__is_new_abi)
        return s.__is_new_abi

    # dependent_packages
    #
    @property
    def dependent_packages(s):
        '''
        Put together a list of all the packages that depend on this package.
        '''
        pkgs = {}
        series = s.ubuntu.series_name(s.package.name, s.package.version)
        entry = s.ubuntu.lookup(series)
        if entry:
            if 'dependent-packages' in entry:
                if s.package.name in entry['dependent-packages']:
                    pkgs.update(entry['dependent-packages'][s.package.name])

        # The package depends upon itself
        #
        pkgs['main'] = s.package.name

        return pkgs

    # determine_build_status
    #
    def determine_build_status(s):
        """
        Verify the required packages for this update, and determine its
        build status
        """
        # Check build status. This is really convoluted... due to number
        # of tasks and we wanting the better behaviour as possible
        promoted_to_updates = True
        promoted_to_security = True
        promoted_to_release = True
        pkg_security = None
        pkg_updates = None
        pkg_release = None
        changes = None
        s.updates = None

        cinfo('')
        cinfo('    Determining Build Status', 'cyan')
        deps = []
        for dep in iter(s.pkgs):
            deps.append(dep)

        cinfo('        Dependent packages:')
        cinfo('')
        cinfo('            %s' % ' '.join(deps))
        cinfo('')


        cinfo('        Processing depedent packages:')
        for dep in iter(s.pkgs):
            cinfo('')
            cinfo('            %s:' % dep, 'yellow')

            abi_num = None
            pkg_rel = s.package.version
            if dep in [ 'lbm', 'lrm', 'lum', 'meta', 'ports-meta' ] and s.package.abi:
                abi_num = s.package.abi
                pkg_rel = s.package.kernel

            status_updates = 0
            status_release = 0
            prepare_status = 0
            prepare_assignee = None
            prepare_uploader = None

            if s.is_stable_package:
                cinfo('                Stable Package', 'cyan')
                cinfo('')
                promoted_to_release = False
                status_ckt,      pkg_ckt      = s.build_status(s.pkgs[dep], abi_num, s.ckt_ppa,    pkg_rel)
                status_proposed, pkg_proposed = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Proposed')

                status_security, pkg_security = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Security')
                if status_security != s.package_version_in_archive:
                    promoted_to_security = False # Not in the Security pocket

                status_updates,  pkg_updates  = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Updates')
                if status_updates != s.package_version_in_archive:
                    promoted_to_updates = False  # Not in the Updates pocket

                for st in [ status_ckt, status_proposed, status_updates ]:
                    if st > prepare_status:
                        prepare_status = st

                for c in [ pkg_ckt, pkg_proposed, pkg_updates, pkg_security ]:
                    if c:
                        prepare_assignee = c.package_creator
                        prepare_uploader = c.package_signer
                        break
            else:
                cinfo('                Development Package', 'cyan')
                cinfo('')
                promoted_to_updates = False
                promoted_to_security = False

                status_release,  pkg_release  = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Release')
                if status_release != s.package_version_in_archive:
                    promoted_to_release = False
                if pkg_release:
                    prepare_assignee = pkg_release.package_creator
                    prepare_uploader = pkg_release.package_signer

                status_proposed, pkg_proposed = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Proposed')
                prepare_status = status_proposed
                if status_release > prepare_status:
                    prepare_status = status_release
                if pkg_proposed:
                    prepare_assignee = pkg_proposed.package_creator
                    prepare_uploader = pkg_proposed.package_signer

            task_status = [ 'New', 'In Progress', 'Fix Released' ]  # FIXME bjf - should probably just be a class variable

            if s.pkgs[dep] == s.package.name:  # if 'linux' == 'linux'
                prep_task_name = 'prepare-package'
            else:
                prep_task_name = 'prepare-package-%s' % (dep)

            try:
                prep_task_status = s.bug.tasks_by_name[prep_task_name].status
            except KeyError:
                for key in s.bug.tasks_by_name:
                    cdebug(key)
                    raise

            cdebug('prep_task_name: %s' % prep_task_name)
            cdebug('prep_task_status: %s' % prep_task_status)

            # When things are moved from one pocket to another, things
            # may be unavailable for some time, and we may think no
            # packages were built. Thus we add a tagged timestamp,
            # marking the time when we detect that the builds are
            # missing. If after 1 hour the builds are still unavailable,
            # then we allow to reset the tasks.
            prop = 'kernel-%s-build-unavailable' % (dep)
            if (s.bug.tasks_by_name[prep_task_name].status == 'Fix Released' and prepare_status != s.package_version_in_archive):
                s.set_tagged_timestamp(s.bug.tasks_by_name[prep_task_name], prop)
                if not prop in s.bug.lpbug.properties:
                    cwarn('Fix Released bug not fully built?!?')
                    continue # Nothing further to do, process the next dependent package.

                date_str = s.bug.lpbug.properties[prop]
                timestamp = datetime.strptime(date_str, '%A, %d. %B %Y %H:%M UTC')
                delta = DeltaTime(timestamp, datetime.utcnow())
                if delta.hours < 1:
                    cinfo('            Builds gone for %s, waiting 1 hour to reset tasks' % (prep_task_name))
                    cwarn('Fix Released bug not fully built?!? (waiting)')
                    continue # Nothing further to do, process the next dependent package.

            # Clear the timestamp property if it was set. We just clean it up so it doesn't
            # confuse anyone looking at the bug.
            #
            if prop in s.bug.lpbug.properties:
                cdebug('clearing the timestamp')
                s.props.set({prop:None})

            new_status = s.bug.tasks_by_name[prep_task_name].status
            if abi_num:
                if s.is_new_abi:
                    new_status = task_status[prepare_status]
                else:
                    if new_status not in ['Invalid', 'Fix Released']:
                        new_status = 'Invalid'
            else:
                new_status = task_status[prepare_status]
            cdebug('new_status: %s' % new_status)

            if prep_task_status != new_status:
                if changes is None:
                    changes = {}
                changes[prep_task_name] = {}
                if prepare_assignee and new_status != 'Invalid':
                    changes[prep_task_name]['assignee'] = prepare_uploader

                changes[prep_task_name]['status'] = new_status

                # Take care of the upload-to-ppa task if needed
                if dep == 'main' and 'upload-to-ppa' in s.bug.tasks_by_name:
                    changes['upload-to-ppa'] = {}
                    if prepare_uploader:
                        changes['upload-to-ppa']['assignee'] = prepare_uploader
                    if (prepare_status == s.package_version_building) or (prepare_status == s.package_version_in_archive):
                        changes['upload-to-ppa']['status'] = 'Fix Released'
                    elif s.bug.tasks_by_name['upload-to-ppa'].status != 'Confirmed':
                        changes['upload-to-ppa']['status'] = 'New'

        # Set promotion bug tasks
        if not s.ignore_promotions:
            if promoted_to_security:
                if changes is None:
                    changes = {}
                changes['promote-to-security'] = {}
                if pkg_security:
                    changes['promote-to-security']['assignee'] = pkg_security.creator
                changes['promote-to-security']['status'] = 'Fix Released'

            if promoted_to_updates:
                if changes is None:
                    changes = {}
                changes['promote-to-updates'] = {}
                if pkg_updates:
                    changes['promote-to-updates']['assignee'] = pkg_updates.creator
                changes['promote-to-updates']['status'] = 'Fix Released'

            if promoted_to_release:
                if changes is None:
                    changes = {}
                changes['promote-to-release'] = {}
                if pkg_release:
                    changes['promote-to-release']['assignee'] = pkg_release.creator
                changes['promote-to-release']['status'] = 'Fix Released'

        if changes is not None:
            cdebug('')
            for key in changes:
                try:
                    cdebug('                %25s - status: %s  assignee: %s' % (key, changes[key]['status'], changes[key]['assignee']), 'magenta')
                except KeyError:
                    cdebug('                %25s - status: %s' % (key, changes[key]['status']), 'magenta')

        s.updates = changes

    # is_released
    #
    @property
    def is_released(s):
        '''
        Determine if the 'promote' tasks have all been set to 'Fix Released'.
        '''
        retval = False

        if s.is_stable_package:
            if ((s.bug.tasks_by_name['promote-to-security'].status == 'Fix Released') and
                (s.bug.tasks_by_name['promote-to-updates'].status == 'Fix Released')):
                retval = True
        else:
            if s.bug.tasks_by_name['promote-to-release'].status == 'Fix Released':
                retval = True

        return retval

    # is_prepd
    #
    @property
    def is_prepd(s):
        '''
        Determine if the main package and all it's dependents have been prepared.
        '''
        retval = True
        cinfo('    Prep\'d Check:', 'cyan')
        for dep in iter(s.pkgs):
            if s.pkgs[dep] == s.package.name:  # if 'linux' == 'linux'
                prep_task_name = 'prepare-package'
            else:
                prep_task_name = 'prepare-package-%s' % (dep)

            prep_task_status = s.bug.tasks_by_name[prep_task_name].status
            if prep_task_status != 'Fix Released':
                cinfo('        %s: not fully prep\'d' % dep)
                retval = False
                break
            else:
                cinfo('        %s: fully prep\'d' % dep)

        return retval

    def get_sources(s, archive, package, release=None, pocket=''):
        if release is not None:
            if pocket != '':
                ps = archive.getPublishedSources(distro_series=s.distro_series, exact_match=True, source_name=package, status='Published', version=release, pocket=pocket)
            else:
                ps = archive.getPublishedSources(distro_series=s.distro_series, exact_match=True, source_name=package, status='Published', version=release)
        else:
            if pocket != '':
                ps = archive.getPublishedSources(distro_series=s.distro_series, exact_match=True, source_name=package, status='Published', pocket=pocket)
            else:
                ps = archive.getPublishedSources(distro_series=s.distro_series, exact_match=True, source_name=package, status='Published')
        return ps

    def build_status(s, package, abi, archive, release=None, pocket=''):
        """
        Return an status code, the possible assignee responsible and the
        package creator related to the publishing of the package in the
        given archive on the optionally specified pocket (if we want the
        check to be restricted on a specific pocket). The following
        values are returned as the status code:
        0 - if the package-version wasn't found/published. In this case
            the package creator and assignee returned is always None
        1 - if the package-version is available (published), but still
            didn't finish building
        2 - package-version is available in the archive

        The parameters are:
          package   - the package name
          release   - the version or version-abi number to match
          abi_match - if provided, indicates that release is not an exact
                      version number, and we must do an ABI check
          archive   - launchpad archive to look into
          pocket    - optional, if we want only results of the archive from
                      the specified pocket
        """

        cinfo('                ---------------------------------------------------------------------------')
        cinfo('                Build Status')
        cinfo('')
        cinfo('                    package: %s' % package)
        cinfo('                        abi: %s' % abi)
        cinfo('                    archive: %s' % archive)
        cinfo('                    release: %s' % release)
        if pocket == '':
            cinfo('                     pocket: ppa')
        else:
            cinfo('                     pocket: %s' % pocket)
        cinfo('')

        if pocket and not abi:
            ps = s.get_sources(archive, package, release, pocket)
        elif not pocket and not abi:
            ps = s.get_sources(archive, package, release)
        elif pocket and abi:
            ps = s.get_sources(archive, package, pocket=pocket)
        else:
            ps = s.get_sources(archive, package)

        matches = []
        if abi:
            dep_ver1 = '%s-%s' % (release, abi)
            dep_ver2 = '%s.%s' % (release, abi)
            rel_match = '<%s> or <%s>' % (dep_ver1, dep_ver2)
            for p in ps:
                src_ver = p.source_package_version
                cinfo('                    src_ver: %s' % src_ver)
                if ((src_ver.startswith(dep_ver1 + '.') or src_ver.startswith(dep_ver2 + '.'))):
                    matches.append(p)
        else:
            rel_match = '<%s>' % (release)
            for p in ps:
                matches.append(p)

        retval = s.package_version_not_found, None
        status = 'missing'
        if not matches:
            cinfo('                    Can\'t find "%s" (%s) build on %s (pocket:%s)' % (package, rel_match, archive.displayname, pocket))
        else:
            lst_date = None
            for pkg in matches:
                src_id = str(pkg.self).rsplit('/', 1)[1]
                build_summaries = archive.getBuildSummariesForSourceIds(source_ids=[src_id])[src_id]
                if build_summaries['status'] == 'FULLYBUILT':
                    cinfo('                    "%s" %s built (pocket:%s)' % (package, rel_match, pocket))
                    bs = s.package_version_in_archive
                    status = 'built'
                else:
                    cinfo('                    "%s" %s not fully built yet, skipping (pocket:%s)' % (package, rel_match, pocket))
                    bs = s.package_version_building
                    status = 'building'
                # prefer newer published items...
                if lst_date:
                    if lst_date > pkg.date_published:
                        continue
                lst_date = pkg.date_published
                retval = bs, pkg

        cinfo('                    result: %s, %s' % (status, retval[1]), 'red')
        return retval

