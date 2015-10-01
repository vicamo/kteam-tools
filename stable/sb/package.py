#!/usr/bin/env python
#

import re

from ktl.ubuntu                         import Ubuntu

from sb.errors                          import ShankError, ErrorExit
from log                                import cdebug, cerror, cwarn, center, cleave, Clog

# PackageError
#
class PackageError(ShankError):
    '''
    Thrown when some basic information about the package that is associated with the
    shankbug could not be determined.
    '''
    def __init__(s, emsg):
        super(ShankError, s).__init__(emsg)

# Package
#
class Package():

    # __init__
    #
    def __init__(s, lp, shankbug):
        center('package::__init__')
        s.lp = lp
        s.bug = shankbug

        s.ubuntu = Ubuntu()
        s.__distro_series = None

        ckt = s.lp.launchpad.people['canonical-kernel-team']
        s.ckt_ppa = ckt.getPPAByName(name='ppa')

        s.main_archive = s.lp.launchpad.distributions["ubuntu"].main_archive

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

        s._cache = None
        cleave('package::__init__')

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
            cdebug('package: %s' % m.group(1))
            cdebug('version: %s%s%s.%s%s' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
            cdebug(' kernel: %s' % m.group(2))
            cdebug('    abi: %s' % m.group(4))

            setattr(s, 'name', m.group(1))
            setattr(s, 'version', '%s%s%s.%s%s' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
            setattr(s, 'kernel', m.group(2))
            setattr(s, 'abi', m.group(4))

            s.valid = True

        if not matched:
            cwarn(' ** None of the regular expressions matched the title (%s)' % txt)

    # __determine_build_status
    #
    def __determine_build_status(s):
        center('Sources::__determine_build_status')

        s._cache = {}
        for dep in iter(s.pkgs):
            cdebug('')
            cdebug('%s: ' % dep, 'blue')
            if dep in s._cache:
                break
            Clog.indent += 4

            # For the linux and linux-signed packages the versions must be an exact match for the other
            # packages only the abi needs to match the linux packages abi number.
            #
            if dep in [ 'lbm', 'meta', 'ports-meta' ] and s.abi:
                abi = s.abi
                version = s.kernel
            else:
                abi = None
                version = s.version

            s._cache[dep] = {}
            s._cache[dep]['ppa'] = {}
            info = s.__is_fully_built(s.pkgs[dep], abi, s.ckt_ppa, version, None)
            s._cache[dep]['ppa']['built']   = info[0]
            s._cache[dep]['ppa']['creator'] = info[1]
            s._cache[dep]['ppa']['signer']  = info[2]
            if s.is_stable_package:
                cdebug('Stable Package', 'cyan')
                cdebug('')

                for pocket in ['Proposed', 'Security', 'Updates']:
                    s._cache[dep][pocket] = {}
                    info = s.__is_fully_built(s.pkgs[dep], abi, s.main_archive, version, pocket)
                    s._cache[dep][pocket]['built']   = info[0]
                    s._cache[dep][pocket]['creator'] = info[1]
                    s._cache[dep][pocket]['signer']  = info[2]
            else:
                for pocket in ['Release', 'Proposed']:
                    s._cache[dep][pocket] = {}
                    info = s.__is_fully_built(s.pkgs[dep], abi, s.main_archive, version, pocket)
                    s._cache[dep][pocket]['built']   = info[0]
                    s._cache[dep][pocket]['creator'] = info[1]
                    s._cache[dep][pocket]['signer']  = info[2]
            Clog.indent -= 4

        cdebug('')
        cdebug('The Cache:', 'cyan')
        for d in s._cache:
            cdebug('    %s' % d, 'cyan')
            for p in s._cache[d]:
                cdebug('        %-8s : %s' % (p, s._cache[d][p]['built']), 'cyan')

        cleave('Sources::__determine_build_status')
        return None

    # __is_fully_built
    #
    def __is_fully_built(s, package, abi, archive, release=None, pocket=''):
        '''
        Have the source package specified been fully built?
        '''
        cdebug('')
        center('Sources::__is_fully_built')
        cdebug('package: %s' % package, 'yellow')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('archive: %s' % archive, 'yellow')
        cdebug('release: %s' % release, 'yellow')
        if pocket == None:
            cdebug(' pocket: ppa', 'yellow')
        else:
            cdebug(' pocket: %s' % pocket, 'yellow')
        cdebug('')

        retval = False

        ps = s.__get_published_sources(package, abi, archive, release, pocket)
        matches = s.__find_matches(ps, abi, release)
        if len(matches) > 0:
            cdebug('    match: %s (%s)' % (release, abi), 'green')
            built, creator, signer = s.__sources_built(matches, archive, package, release, pocket)
        else:
            built   = False
            creator = None
            signer  = None

        cleave('Sources::__is_fully_built (%s)' % retval)
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

        center('Sources::__get_published_sources')

        if pocket and not abi:
            # If the abi is not specified then we are looking for an explicit release in a specific
            # pocket.
            #
            cdebug('getPublishedSources: rule 1')
            ps = archive.getPublishedSources(distro_series=s.distro_series, exact_match=True, source_name=package, status='Published', version=release, pocket=pocket)
        elif not pocket and not abi:
            cdebug('getPublishedSources: rule 2')
            ps = archive.getPublishedSources(distro_series=s.distro_series, exact_match=True, source_name=package, status='Published', version=release)
        elif pocket and abi:
            cdebug('getPublishedSources: rule 3')
            ps = archive.getPublishedSources(distro_series=s.distro_series, exact_match=True, source_name=package, status='Published', pocket=pocket)
        else:
            cdebug('getPublishedSources: rule 4')
            ps = archive.getPublishedSources(distro_series=s.distro_series, exact_match=True, source_name=package, status='Published')

        cleave('Sources::__get_published_sources')
        return ps

    # __find_matches
    #
    def __find_matches(s, ps, abi, release):
        center('Sources::__find_matches')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('release: %s' % release, 'yellow')

        match = False
        matches = []
        if abi:
            cdebug('abi match only')
            dep_ver1 = '%s-%s' % (release, abi)
            dep_ver2 = '%s.%s' % (release, abi)
            for p in ps:
                src_ver = p.source_package_version
                cdebug('examining: %s' % src_ver)
                if ((src_ver.startswith(dep_ver1 + '.') or src_ver.startswith(dep_ver2 + '.'))):
                    cdebug('adding: %s' % src_ver, 'green')
                    matches.append(p)
                    match = True
        else:
            cdebug('exact version match required')
            for p in ps:
                src_ver = p.source_package_version
                cdebug('adding: %s' % src_ver, 'green')
                matches.append(p)
                match = True

        cleave('Sources::__find_matches (%s)' % match)
        return matches

    # __sources_built
    #
    def __sources_built(s, matches, archive, package, release, pocket):
        center('Sources::__sources_built')
        cdebug('matches: %s' % matches, 'yellow')
        cdebug('archive: %s' % archive, 'yellow')
        cdebug('package: %s' % package, 'yellow')
        cdebug('release: %s' % release, 'yellow')
        cdebug(' pocket: %s' % pocket, 'yellow')
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
                    cdebug('"%s" %s built (pocket:%s)' % (package, release, pocket), 'green')
                    retval = True
                    status = True
                    creator = pkg.package_creator
                    signer  = pkg.package_signer
                else:
                    cdebug('"%s" %s not fully built yet, skipping (pocket:%s)' % (package, release, pocket), 'green')
                # prefer newer published items...
                if lst_date:
                    if lst_date > pkg.date_published:
                        continue
                lst_date = pkg.date_published
            except:
                cerror("Exception thrown geting the build summaries ... (is this keystone?)")
                pass # Added when I started getting "UTTP Error 401: Unauthorized" for keystone kernels
        cleave('Sources::__sources_built (%s)' % retval)
        return status, creator, signer

    # srcs
    #
    @property
    def srcs(s):
        if s._cache is None:
            s.__determine_build_status()
        return s._cache

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
        center('Package::fully_built')
        cdebug('   pkg: %s' % pkg)
        retval = False

        try:
            for pocket in s.srcs[pkg]:
                if s.srcs[pkg][pocket]['built']:
                    retval = True
                    break
        except KeyError:
            pass # Eat the KeyError and return False

        cleave('Package::fully_built (%s : %s)' % (pkg, retval))
        return retval

    # all_dependent_packages_fully_built
    #
    @property
    def all_dependent_packages_fully_built(s):
        center('Package::all_dependent_packages_fully_built')
        retval = True

        for pkg in s.srcs:
            pkg_built = False
            try:
                for pocket in s.srcs[pkg]:
                    if s.srcs[pkg][pocket]['built']:
                        pkg_built = True
                        break
            except KeyError:
                pass # Eat the KeyError and return False

            if not pkg_built:
                cdebug('%s is not fully built yet.' % pkg, 'red')
                retval = False
                break

        cleave('Package::all_dependent_packages_fully_built (%s)' % retval)
        return retval

    # creator
    #
    def creator(s, pkg, pocket=None):
        center('Packages::creator')
        cdebug('   pkg: %s' % pkg)
        cdebug('pocket: %s' % pocket)
        retval = None

        if pocket is None:
            for pocket in s.srcs[pkg]:
                if s.srcs[pkg][pocket]['built']:
                    retval = s.srcs[pkg][pocket]['creator']
                    break
        else:
            retval = s.srcs[pkg][pocket]['creator']
        cleave('Packages::creator')
        return retval

    # signer
    #
    def signer(s, pkg, pocket=None):
        center('Packages::signer')
        cdebug('   pkg: %s' % pkg)
        cdebug('pocket: %s' % pocket)
        retval = None

        if pocket is None:
            for pocket in s.srcs[pkg]:
                if s.srcs[pkg][pocket]['built']:
                    retval = s.srcs[pkg][pocket]['signer']
                    break
        else:
            retval = s.srcs[pkg][pocket]['signer']
        cleave('Packages::signer')
        return retval

    # ready_for_testing
    #
    @property
    def ready_for_testing(s):
        '''
        It's ready for testing if all dependent package are fully built and if all the
        packages are in the proposed pocket.
        '''
        center('Packages::ready_for_testing')
        retval = False
        if s.all_dependent_packages_fully_built:
            retval = True
            for package in s._cache:
                if not s.srcs[package]['Proposed']['built']:
                    retval = False
                    break

        cleave('Packages::ready_for_testing (%s)' % retval)
        return retval
