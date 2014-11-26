#!/usr/bin/env python
#

import re

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

# Sources
#
class Sources(object):
    # __init__
    #
    def __init__(s, package):
        cdebug('                    Sources::__init__ enter', 'blue')

        s.package = package
        s.__cache = None

        cdebug('                    Sources::__init__ leave', 'blue')

    # __determine_build_status
    #
    def __determine_build_status(s):
        cdebug('                        Sources::__determine_build_status enter', 'blue')

        s.__cache = {}
        for dep in iter(s.package.pkgs):
            cinfo('')
            cinfo('                            %s:' % dep, 'yellow')

            if dep in s.__cache:
                cinfo('                                Done that already', 'yellow')
                break

            cinfo('                                That\'s new this time.', 'yellow')

            # For the linux and linux-signed packages the versions must be an exact match for the other
            # packages only the abi needs to match the linux packages abi number.
            #
            if dep in [ 'lbm', 'meta', 'ports-meta' ] and s.package.abi:
                abi = s.package.abi
                version = s.package.kernel
            else:
                abi = None
                version = s.package.version

            if dep in s.__cache:
                cinfo('                                Done that already', 'yellow')
                break

            s.__cache[dep] = {}
            if s.package.is_stable_package:
                cinfo('                                Stable Package', 'cyan')
                cinfo('')

                s.__cache[dep]['ppa'] = {}
                info = s.__is_fully_built(s.package.pkgs[dep], abi, s.package.ckt_ppa, version, None)
                s.__cache[dep]['ppa']['built']   = info[0]
                s.__cache[dep]['ppa']['creator'] = info[1]
                s.__cache[dep]['ppa']['signer']  = info[2]
                for pocket in ['Proposed', 'Security', 'Updates']:
                    s.__cache[dep][pocket] = {}
                    info = s.__is_fully_built(s.package.pkgs[dep], abi, s.package.main_archive, version, pocket)
                    s.__cache[dep][pocket]['built']   = info[0]
                    s.__cache[dep][pocket]['creator'] = info[1]
                    s.__cache[dep][pocket]['signer']  = info[2]
            else:
                s.__cache[dep]['ppa'] = {}
                info = s.__is_fully_built(s.package.pkgs[dep], abi, s.package.ckt_ppa, version, None)
                s.__cache[dep]['ppa']['built']   = info[0]
                s.__cache[dep]['ppa']['creator'] = info[1]
                s.__cache[dep]['ppa']['signer']  = info[2]
                for pocket in ['Release', 'Proposed']:
                    s.__cache[dep][pocket] = {}
                    info = s.__is_fully_built(s.package.pkgs[dep], abi, s.package.main_archive, version, pocket)
                    s.__cache[dep][pocket]['built']   = info[0]
                    s.__cache[dep][pocket]['creator'] = info[1]
                    s.__cache[dep][pocket]['signer']  = info[2]

        for d in s.__cache:
            cwarn('                    %s' % d, 'cyan')
            for p in s.__cache[d]:
                cwarn('                                %-8s : %s' % (p, s.__cache[d][p]['built']), 'cyan')

        cdebug('                    Sources::__determine_build_status leave', 'blue')
        return None

    # __is_fully_built
    #
    def __is_fully_built(s, package, abi, archive, release=None, pocket=''):
        '''
        Have the source package specified been fully built?
        '''
        cdebug('')
        cdebug('                            Sources::__is_fully_built enter', 'blue')
        retval = False

        ps = s.__get_published_sources(package, abi, archive, release, pocket)
        matches = s.__find_matches(ps, abi, release)
        if matches is not None:
            cdebug('                                match: %s (%s)' % (release, abi), 'green')
            built, creator, signer = s.__sources_built(matches, archive, package, release, pocket)

        cdebug('                            Sources::__is_fully_built leave (%s)' % retval, 'blue')
        return built, creator, signer

    # __get_published_sources
    #
    def __get_published_sources(s, package, abi, archive, release=None, pocket=''):
        """
        The parameters are:
          package   - the package name
          release   - the version or version-abi number to match
          abi       - if provided, indicates that release is not an exact version number,
                      and we must do an ABI check
          archive   - launchpad archive to look into
          pocket    - optional, if we want only results of the archive from
                      the specified pocket
        """

        cdebug('                                Sources::__get_published_sources enter', 'blue')
        cdebug('                                    package: %s' % package, 'yellow')
        cdebug('                                        abi: %s' % abi,     'yellow')
        cdebug('                                    archive: %s' % archive, 'yellow')
        cdebug('                                    release: %s' % release, 'yellow')
        if pocket == '':
            cdebug('                                     pocket: ppa', 'yellow')
        else:
            cdebug('                                     pocket: %s' % pocket, 'yellow')
        cdebug('')

        if pocket and not abi:
            # If the abi is not specified then we are looking for an explicit release in a specific
            # pocket.
            #
            cdebug('                                    getPublishedSources: rule 1', 'blue')
            ps = archive.getPublishedSources(distro_series=s.package.distro_series, exact_match=True, source_name=package, status='Published', version=release, pocket=pocket)
        elif not pocket and not abi:
            cdebug('                                    getPublishedSources: rule 2', 'blue')
            ps = archive.getPublishedSources(distro_series=s.package.distro_series, exact_match=True, source_name=package, status='Published', version=release)
        elif pocket and abi:
            cdebug('                                    getPublishedSources: rule 3', 'blue')
            ps = archive.getPublishedSources(distro_series=s.package.distro_series, exact_match=True, source_name=package, status='Published', pocket=pocket)
        else:
            cdebug('                                    getPublishedSources: rule 4', 'blue')
            ps = archive.getPublishedSources(distro_series=s.package.distro_series, exact_match=True, source_name=package, status='Published')

        cdebug('                                Sources::__get_published_sources leave', 'blue')
        return ps

    # __find_matches
    #
    def __find_matches(s, ps, abi, release):
        cdebug('                                Sources::__find_matches enter', 'blue')
        cdebug('                                        abi: %s' % abi,     'yellow')
        cdebug('                                    release: %s' % release, 'yellow')

        match = False
        matches = []
        if abi:
            cdebug('                                abi match only', 'blue')
            dep_ver1 = '%s-%s' % (release, abi)
            dep_ver2 = '%s.%s' % (release, abi)
            for p in ps:
                src_ver = p.source_package_version
                cdebug('                                examining: %s' % src_ver)
                if ((src_ver.startswith(dep_ver1 + '.') or src_ver.startswith(dep_ver2 + '.'))):
                    cdebug('                                    adding: %s' % src_ver, 'green')
                    matches.append(p)
                    match = True
        else:
            cdebug('                                    exact version match required', 'blue')
            for p in ps:
                src_ver = p.source_package_version
                cdebug('                                    adding: %s' % src_ver, 'green')
                matches.append(p)
                match = True

        cdebug('                                Sources::__find_matches leave (%s)' % match, 'blue')
        return matches

    # __sources_built
    #
    def __sources_built(s, matches, archive, package, release, pocket):
        cdebug('                                Sources::__sources_built enter', 'blue')
        retval = False
        lst_date = None
        status = False
        creator = ''
        signer  = ''
        for pkg in matches:
            src_id = str(pkg.self).rsplit('/', 1)[1]
            try:
                build_summaries = archive.getBuildSummariesForSourceIds(source_ids=[src_id])[src_id]
                if build_summaries['status'] == 'FULLYBUILT':
                    cinfo('                                    "%s" %s built (pocket:%s)' % (package, release, pocket), 'green')
                    retval = True
                    status = True
                    creator = pkg.package_creator
                    signer  = pkg.package_signer
                else:
                    cinfo('                                    "%s" %s not fully built yet, skipping (pocket:%s)' % (package, release, pocket), 'green')
                # prefer newer published items...
                if lst_date:
                    if lst_date > pkg.date_published:
                        continue
                lst_date = pkg.date_published
            except:
                cerror("Exception thrown geting the build summaries ... (is this keystone?)")
                pass # Added when I started getting "UTTP Error 401: Unauthorized" for keystone kernels
        cdebug('                                Sources::__sources_built leave (%s)' % retval, 'blue')
        return status, creator, signer

    # fully_built
    #
    def fully_built(s, pkg):
        cdebug('                        Sources::fully_built enter')
        retval = False

        if s.__cache is None:
            s.__determine_build_status()

        try:
            for pocket in s.__cache[pkg]:
                if s.__cache[pkg][pocket]['built']:
                    retval = True
                    break
        except KeyError:
            pass # Eat the KeyError and return False

        cdebug('                        Sources::fully_built leave (%s)' % retval)
        return retval

    # all_dependent_packages_fully_built
    #
    def all_dependent_packages_fully_built(s):
        cdebug('                        Sources::all_dependent_packages_fully_built enter')
        retval = True

        if s.__cache is None:
            s.__determine_build_status()

        for pkg in s.__cache:
            pkg_built = False
            try:
                for pocket in s.__cache[pkg]:
                    if s.__cache[pkg][pocket]['built']:
                        pkg_built = True
                        break
            except KeyError:
                pass # Eat the KeyError and return False

            if not pkg_built:
                cdebug('                            %s is not fully built yet.' % pkg, 'red')
                retval = False
                break

        cdebug('                        Sources::all_dependent_packages_fully_built leave (%s)' % retval)
        return retval

    # creator
    #
    def creator(s, pkg, pocket=None):
        cdebug('                        Sources::creator enter')
        cdebug('                            pkg: %s' % pkg)
        retval = None

        if s.__cache is None:
            s.__determine_build_status()

        if pocket is None:
            for pocket in s.__cache[pkg]:
                if s.__cache[pkg][pocket]['built']:
                    retval = s.__cache[pkg][pocket]['creator']
                    break
        else:
            retval = s.__cache[pkg][pocket]['creator']
        cdebug('                        Sources::creator leave')
        return retval

    # signer
    #
    def signer(s, pkg, pocket=None):
        cdebug('                        Sources::signer enter')
        cdebug('                            pkg: %s' % pkg)
        retval = None

        if s.__cache is None:
            s.__determine_build_status()

        if pocket is None:
            for pocket in s.__cache[pkg]:
                if s.__cache[pkg][pocket]['built']:
                    retval = s.__cache[pkg][pocket]['signer']
                    break
        else:
            retval = s.__cache[pkg][pocket]['signer']
        cdebug('                        Sources::signer leave')
        return retval

# Package
#
class Package():

    # __init__
    #
    def __init__(s, lp, shankbug):
        cdebug('                package::__init__ enter', 'blue')
        s.lp = lp
        s.bug = shankbug

        s.ubuntu = Ubuntu()
        s.__distro_series = None
        #  s.__is_new_abi = None

        ckt = s.lp.launchpad.people['canonical-kernel-team']
        s.ckt_ppa = ckt.getPPAByName(name='ppa')

        s.main_archive = s.lp.launchpad.distributions["ubuntu"].main_archive

        #  s.props = Properties(s.bug.lpbug)

        # Determine some properties of the package we are looking at based on the
        # bug title. This information is used further on.
        #
        s.package = s.__title_decode(s.bug.lpbug.title)
        if not s.valid:
            cwarn('        Unable to check package builds for this bug: either the package name or')
            cwarn('        the version are not properly indicated in the bug title.')
            raise PackageError(['Unable to check package builds for this bug: either the package name or',
                                'the version is not properly indicated in the bug title.'])

        setattr(s, 'series', s.ubuntu.series_name(s.name, s.version))

        s.pkgs = s.dependent_packages

        if s.bug.targeted_project == 'kernel-sru-workflow':
            s.is_stable_package = True
        else:
            s.is_stable_package = False

        #  s.package_version_not_found  = 0
        #  s.package_version_building   = 1
        #  s.package_version_in_archive = 2

        #  s.ignore_promotions = False

        s.__sources = Sources(s)
        cdebug('                package::__init__ leave', 'blue')

    def __title_decode(s, txt):
        matched = False
        #                              .- package name (group(1))
        #                             /           .- kernel version (group(2))
        #                            /           /          .- version/abi separator (group(3))
        #                           /           /          /
        ver_rc     = re.compile("(\S+): (\d+\.\d+\.\d+)([-\.])(\d+)\.(\d+)([~a-z\d.]*)")
        #                                                       /      /       /
        #                                                      /      /       .- backport extra (m.group(6))
        #                                                     /      .- upload number (m.group(5))
        #                                                    .- abi (group(4))

        #info('     Extract package info\n')
        setattr(s, 'valid', False)
        m = ver_rc.search(txt)
        if m is not None:
            matched = True
            cinfo('         package: %s\n' % m.group(1))
            cinfo('         version: %s%s%s.%s%s\n' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
            cinfo('          kernel: %s\n' % m.group(2))
            cinfo('             abi: %s\n' % m.group(4))

            setattr(s, 'name', m.group(1))
            setattr(s, 'version', '%s%s%s.%s%s' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
            setattr(s, 'kernel', m.group(2))
            setattr(s, 'abi', m.group(4))

            s.valid = True

        if not matched:
            cwarn(' ** None of the regular expressions matched the title (%s)' % txt)

    # dependent_packages
    #
    @property
    def dependent_packages(s):
        '''
        Put together a list of all the packages that depend on this package.
        '''
        pkgs = {}
        series = s.ubuntu.series_name(s.name, s.version)
        entry = s.ubuntu.lookup(series)
        if entry:
            if 'dependent-packages' in entry:
                if s.name in entry['dependent-packages']:
                    pkgs.update(entry['dependent-packages'][s.name])

        # The package depends upon itself
        #
        pkgs['main'] = s.name

        return pkgs

    # distro_series
    #
    @property
    def distro_series(s):
        '''
        Return the LP distro series link to the series associated with this version
        of this package.
        '''
        if s.__distro_series is None:
            if s.series:
                sc = s.lp.launchpad.distributions["ubuntu"].series_collection
                for ds in sc:
                    if ds.name == s.series:
                        s.__distro_series = ds
                        break

            if s.__distro_series is None:
                emsg = "        ERROR: can't figure out the distro series for %s-%s\n" % (s.name, s.version)
                cerror(emsg)
                raise ErrorExit(emsg)

        return s.__distro_series

    # fully_built
    #
    def fully_built(s, pkg):
        cdebug('                    Package::fully_built enter')
        retval = s.__sources.fully_built(pkg)
        cdebug('                    Package::fully_built leave (%s)' % retval)
        return retval

    # all_dependent_packages_fully_built
    #
    def all_dependent_packages_fully_built(s):
        cdebug('                    Package::all_dependent_packages_fully_built enter')
        retval = s.__sources.all_dependent_packages_fully_built()
        cdebug('                    Package::all_dependent_packages_fully_built leave (%s)' % retval)
        return retval

    # creator
    #
    def creator(s, pkg, pocket=None):
        cdebug('                    Package::creator enter')
        cdebug('                        pkg: %s' % pkg)
        retval = s.__sources.creator(pkg, pocket)
        cdebug('                    Package::creator leave (%s)' % retval)
        return retval

    # signer
    #
    def signer(s, pkg, pocket=None):
        cdebug('                    Package::signer enter')
        cdebug('                        pkg: %s' % pkg)
        retval = s.__sources.signer(pkg, pocket)
        cdebug('                    Package::signer leave (%s)' % retval)
        return retval

