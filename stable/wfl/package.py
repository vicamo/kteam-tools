#!/usr/bin/env python
#

import re
from datetime                           import datetime, timedelta

from ktl.kernel_series                  import KernelSeries
from lib.utils                          import date_to_string, dump

from .check_component                   import CheckComponent
from .errors                            import ShankError, ErrorExit
from .log                               import cdebug, cerror, cwarn, center, cleave, Clog, cinfo

# PackageError
#
class PackageError(ShankError):
    '''
    Thrown when some basic information about the package that is associated with the
    shankbug could not be determined.
    '''
    pass


# SeriesLookupFailure
#
class SeriesLookupFailure(ShankError):
    '''
    Thrown when the series lookup throws a KeyError exception.
    '''
    pass

# Package
#
class Package():

    # __init__
    #
    def __init__(s, lp, shankbug, ks=None):
        center('package::__init__')
        s.lp = lp
        s.bug = shankbug

        s.kernel_series = KernelSeries() if ks is None else ks
        s.__distro_series = None

        # Determine some properties of the package we are looking at based on the
        # bug title. This information is used further on.
        #
        if not s.__title_decode(s.bug.lpbug):
            raise PackageError('Package not identified from title')
        if s.series is None:
            raise PackageError('Series not identified from tags')
        if s.source is None:
            raise PackageError('Source not found in kernel-series')

        # Look the package routing destinations up in kernel-series, convert the
        # archives to real archive objects.
        s._routing = {}
        s.routing_mode = 'None'
        if s.source.routing:
            for (key, destination) in (
                ('ppa', 'build'),
                ('Proposed', 'proposed'),
                ('Updates', 'updates'),
                ('Security', 'security'),
                ('Release', 'release'),
                ):
                route = s.source.routing.lookup_destination(destination, primary=True)
                if route is None:
                    continue
                archive = s.lp.launchpad.archives.getByReference(reference=route[0])
                if archive is None:
                    continue
                s._routing[key] = (archive, route[1])
            s.routing_mode = s.source.routing.name

        cinfo('    Routing mode: {}'.format(s.routing_mode), 'blue')
        cinfo('    Routing table:', 'blue')
        for pocket, pocket_data in s._routing.items():
            cinfo('        {}: {} {}'.format(pocket, pocket_data[0], pocket_data[1]), 'blue')

        s.pkgs = s.dependent_packages
        if s.pkgs == None:
            raise PackageError('Unable to check package builds for this bug: the package/series combination is invalid')

        s._cache = None
        cleave('package::__init__')

    def routing(self, pocket):
        center(self.__class__.__name__ + '.routing')
        routes = self._routing[pocket]
        cleave(self.__class__.__name__ + '.routing')
        return routes

    def __title_decode(s, lpbug):
        txt = lpbug.title

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
        s.valid = False
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

            # XXX: neither of these is (currently) specified in the
            # KernelSeries format; luckily neither is currently in use.
            # proposed_only is normally only used for the first couple of
            # kernels in a series and we have been using kernel-block-proposed
            # tags for that so it appears redundant.  test_flavours is a
            # layering violation, the backends are learning to handle flavours
            # so the bodge we have in the bug.test_flavours is good enough.

            # Work out if this is a proposed only entry.
            s.proposed_only = False

            # Determine testing flavours.
            s.test_flavours = None

            s.valid = True

        # Try just a package match.
        if not matched:
            #                            .- package name (group(1))
            #                           /
            pkg_rc     = re.compile("(\S+):")
            m = pkg_rc.search(txt)
            if m is not None:
                matched = True
                cdebug('package: %s' % m.group(1))
                cdebug('version: INVALID')

                s.name = m.group(1)
                s.version = None

                # Determine testing flavours.
                s.test_flavours = None

        # Work out what series this package is published in...
        series_tag_entry = None
        for tag in lpbug.tags:
            series_tag_entry = s.kernel_series.lookup_series(codename=tag)
            if series_tag_entry:
                break

        if not matched:
            cwarn(' ** None of the regular expressions matched the title (%s)' % txt)
            return False

        # Set the series attribute
        cdebug(' series: %s' % series_tag_entry.codename)
        setattr(s, 'series', series_tag_entry.codename)

        # Lookup the KernelSeries package and attach that.
        source = None
        if series_tag_entry:
            source = series_tag_entry.lookup_source(s.name)
        setattr(s, 'source', source)

        return True

    # __determine_build_status
    #
    def __determine_build_status(s):
        center('Sources::__determine_build_status')

        s._cache = {}

        cinfo('')
        cinfo('Build Status:', 'cyan')

        for dep in iter(s.pkgs):
            cdebug('')
            cinfo('%s: ' % dep, 'blue')
            cinfo('--------------------------------------------------------------------------------', 'blue')
            if dep in s._cache:
                break
            Clog.indent += 4

            # For the linux and linux-signed packages the versions must be an exact match for the other
            # packages only the abi needs to match the linux packages abi number.
            #
            if dep in ['lbm', 'meta', 'ports-meta'] and s.abi:
                abi = s.abi
                version = s.kernel
            else:
                abi = None
                version = s.version

            s._cache[dep] = {}
            if not s.bug.is_development_series:
                cdebug('Stable Package', 'cyan')
                cdebug('')
                scan_pockets = ('ppa', 'Proposed', 'Security', 'Updates')
            else:
                cdebug('Development Package', 'cyan')
                cdebug('')
                scan_pockets = ('ppa', 'Proposed', 'Release')

            for pocket in scan_pockets:
                (src_archive, src_pocket) = s._routing[pocket]

                s._cache[dep][pocket] = {}
                info = s.__is_fully_built(s.pkgs[dep], abi, src_archive, version, src_pocket)
                s._cache[dep][pocket]['built']   = info[0]
                s._cache[dep][pocket]['creator'] = info[1]
                s._cache[dep][pocket]['signer']  = info[2]
                s._cache[dep][pocket]['published'] = info[3]
                s._cache[dep][pocket]['most_recent_build'] = info[4]
                s._cache[dep][pocket]['status'] = info[5]
                s._cache[dep][pocket]['version'] = info[6]
                cinfo('%-8s : %-5s / %-10s    (%s : %s) %s [%s %s]' % (pocket, info[0], info[5], info[3], info[4], info[6], src_archive, src_pocket), 'cyan')
            Clog.indent -= 4

        cdebug('')
        cdebug('The Cache:', 'cyan')
        for d in sorted(s._cache):
            cdebug('    %s' % d, 'cyan')
            for p in sorted(s._cache[d]):
                cdebug('        %-8s : %-5s   (%s)' % (p, s._cache[d][p]['built'], date_to_string(s._cache[d][p]['published'])), 'cyan')

        cleave('Sources::__determine_build_status')
        return None

    def __all_arches_built(s, matches):
        '''
        Determine if all the builds that have been done for all of the arches. This helps
        us detect when a build has been canceled.
        '''
        center(s.__class__.__name__ + '__all_arches_built')
        retval = False
        if len(matches) > 0:
            for match in matches:
                binary_list = match.getPublishedBinaries()

                # Determine how many arches we have builds for.
                #
                sa = {} # series arches
                for binary in binary_list:
                    if binary.architecture_specific:
                        try:
                            sa[binary.distro_arch_series_link] += 1
                        except KeyError:
                            sa[binary.distro_arch_series_link] = 1
                for arch in sa:
                    cdebug('series/arch : %s' % arch)

                arches_to_build = len(sa)

                # Determine how many builds there actually are. This includes
                # canceled builds which are important to us.
                #
                builds = match.getBuilds()

                if arches_to_build == len(builds):
                    retval = True
                else:
                    cdebug('Only %s of %s arches were built' % (len(builds), arches_to_build))
        else:
            cdebug('No matches found')
        cleave(s.__class__.__name__ + '__all_arches_built (%s)' % retval)
        return retval

    # __is_fully_built
    #
    def __is_fully_built(s, package, abi, archive, release=None, pocket=''):
        '''
        Have the source package specified been fully built?
        '''
        center(s.__class__.__name__ + '.__is_fully_built')
        cdebug('package: %s' % package, 'yellow')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('archive: %s' % archive, 'yellow')
        cdebug('release: %s' % release, 'yellow')
        cdebug(' pocket: %s' % pocket, 'yellow')

        # Do a loose match, we will select for the specific version we wanted
        # in __find_matches but this way we have the published version for
        # pocket emptyness checks.
        ps = s.__get_published_sources(package, abi, archive, pocket=pocket)
        matches = s.__find_matches(ps, abi, release)
        if len(matches) > 0:
            cdebug('    match: %s (%s)' % (release, abi), 'green')
            fullybuilt, creator, signer, published, most_recent_build, status = s.__sources_built(matches, archive, package, release, pocket)
            fullybuilt = fullybuilt and s.__all_arches_built(matches)
            version = matches[0].source_package_version
        else:
            fullybuilt   = False
            status  = ''
            creator = None
            signer  = None
            published = None
            most_recent_build = None
            version = None
            if len(ps) > 0:
                version = ps[0].source_package_version

        cleave(s.__class__.__name__ + '.__is_fully_built')
        return fullybuilt, creator, signer, published, most_recent_build, status, version

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
        center(s.__class__.__name__ + '.__get_published_sources')
        cdebug('package: %s' % package, 'yellow')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('archive: %s' % archive, 'yellow')
        cdebug(' series: %s' % s.distro_series, 'yellow')
        cdebug('release: %s' % release, 'yellow')
        if pocket == '':
            cdebug(' pocket: ppa', 'yellow')
        else:
            cdebug(' pocket: %s' % pocket, 'yellow')
        cdebug('')

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

        cdebug('records: %d' % len(ps), 'yellow')
        cleave(s.__class__.__name__ + '.__get_published_sources')
        return ps

    # __find_matches
    #
    def __find_matches(s, ps, abi, release):
        center('Sources::__find_matches')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('release: %s' % release, 'yellow')
        cdebug('records: %d' % len(ps), 'yellow')

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
                # Exact match or exact prefix plus '+somethingN'
                if src_ver == release or src_ver.startswith(release + '+'):
                    cdebug('adding: %s' % src_ver, 'green')
                    matches.append(p)
                    match = True

        cleave('Sources::__find_matches (%s)' % match)
        return matches

    # __sources_built
    #
    def __sources_built(s, matches, archive, package, release, pocket):
        '''
        '''
        center('Sources::__sources_built')
        cdebug('matches: %s' % matches, 'yellow')
        cdebug('archive: %s' % archive, 'yellow')
        cdebug('package: %s' % package, 'yellow')
        cdebug('release: %s' % release, 'yellow')
        cdebug(' pocket: %s' % pocket, 'yellow')
        retval = False
        lst_date = None
        fullybuilt = False
        creator = ''
        signer  = ''
        published = None
        status = ''

        # built - The date/time of the last build of any of the arches built. We want
        #         the one that finished most recently.
        #
        most_recent_build = None
        for pkg in matches:
            src_id = str(pkg.self).rsplit('/', 1)[1]

            build_summaries = archive.getBuildSummariesForSourceIds(source_ids=[src_id])[src_id]
            status = build_summaries['status']
            try:
                creator = pkg.package_creator
                signer  = pkg.package_signer
            except:
                # Just eat the error
                pass

            if build_summaries['status'] == 'FULLYBUILT':
                cdebug('"%s" %s built (pocket:%s)' % (package, release, pocket), 'magenta')
                retval = True
                fullybuilt = True
                published = pkg.date_published.replace(tzinfo=None)

                for b in build_summaries['builds']:
                    built = datetime.strptime(b['datebuilt'], '%Y-%m-%dT%X.%f+00:00')
                    if most_recent_build is None:
                        most_recent_build = built
                    else:
                        if most_recent_build < built:
                            most_recent_build = built
            else:
                cdebug('"%s" %s not fully built yet, skipping (pocket:%s)' % (package, release, pocket), 'green')
            # prefer newer published items...
            if lst_date:
                if lst_date > pkg.date_published:
                    continue
            lst_date = pkg.date_published

        cleave('Sources::__sources_built (%s)' % retval)
        return fullybuilt, creator, signer, published, most_recent_build, status

    # build_info
    #
    @property
    def build_info(s):
        if s._cache is None:
            s.__determine_build_status()
        return s._cache

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
        series = s.kernel_series.lookup_series(codename=s.series)
        source = series.lookup_source(s.name)
        if source is None:
            return None
        for package in source.packages:
            pkgs[package.type if package.type else 'main'] = package.name

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
        cdebug('   pkg: \'%s\'' % pkg)
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

    # all_in_pocket
    #
    def all_in_pocket(s, pocket='Proposed'):
        '''
        All dependent packages are in the pocket 'pocket'.
        '''
        center(s.__class__.__name__ + '.all_in_pocket')
        retval = True

        for pkg in s.srcs:
            try:
                pkg_seen = s.srcs[pkg][pocket]['status'] in ['BUILDING', 'FULLYBUILT', 'FAILEDTOBUILD']
            except KeyError:
                pkg_seen = False

            if pkg_seen:
                cinfo('        %s is present in %s.' % (pkg, pocket), 'yellow')
            else:
                cinfo('        %s is NOT present in %s.' % (pkg, pocket), 'yellow')
                retval = False

        cleave(s.__class__.__name__ + '.all_in_pocket (%s)' % (retval))
        return retval

    # all_built_and_in_proposed
    #
    @property
    def all_built_and_in_proposed(s):
        '''
        All dependent packages are fully built and in the proposed pocket.
        '''
        center(s.__class__.__name__ + '.all_built_and_in_proposed')
        retval = True

        for pkg in s.srcs:
            try:
                pkg_built = s.srcs[pkg]['Proposed']['built']
            except KeyError:
                pkg_built = False

            if not pkg_built:
                cinfo('        %s is either not fully built yet or not in proposed.' % pkg, 'red')
                retval = False
                break

        cleave(s.__class__.__name__ + '.all_built_and_in_proposed (%s)' % (retval))
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
                if s.srcs[pkg][pocket]['status'] in ['BUILDING', 'FULLYBUILT', 'FAILEDTOBUILD']:
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

    # package_fully_built
    #
    def package_fully_built(s, pkg):
        '''
        For the package specified, the status of whether or not it is fully built
        is returned.
        '''
        retval = s.fully_built(pkg)
        return retval

    # packages_released
    #
    @property
    def packages_released(s):
        '''
        '''
        retval = True

        if s.bug.is_development_series:
            pocket = 'Release'
        else:
            pocket = 'Updates'

        bi = s.build_info
        for pkg in bi:
            if bi[pkg][pocket]['built'] is not True:
                cinfo('            %s has not been released.' % (pkg), 'yellow')
                retval = False
                break

        return retval

    # packages_released_to_security
    #
    @property
    def packages_released_to_security(s):
        '''
        '''
        retval = True

        pocket = 'Security'

        bi = s.build_info
        for pkg in bi:
            if bi[pkg][pocket]['built'] is not True:
                cinfo('            %s has not been released.' % (pkg), 'yellow')
                retval = False
                break

        return retval

    # proposed_pocket_clear
    #
    @property
    def proposed_pocket_clear(s):
        '''
        Check that the proposed pocket is either empty or contains the same version
        as found in -updates/-release.
        '''
        retval = True

        if s.bug.is_development_series:
            pocket = 'Release'
        else:
            pocket = 'Updates'

        bi = s.build_info
        for pkg in bi:
            if bi[pkg]['Proposed']['version'] not in (None, bi[pkg][pocket]['version']):
                cinfo('            %s has %s pending in -proposed.' % (pkg, bi[pkg]['Proposed']['version']), 'yellow')
                retval = False

        # If proposed is not clear, consider if it is full due to a bug
        # which has been duplicated against me.
        if not retval:
            duplicates = s.bug.workflow_duplicates
            for dup_wb in duplicates:
                # Consider only those supporting debs.
                if dup_wb.debs and dup_wb.debs.all_built_and_in_proposed:
                    cinfo('            %s is duplicate of us and owns the binaries in -proposed, overriding' % (dup_wb.lpbug.id,), 'yellow')
                    retval = True
                    break

        return retval

    # all_dependent_packages_fully_built
    #
    @property
    def all_dependent_packages_fully_built(s):
        '''
        For the kernel package associated with this bug, the status of whether or
        not all of the dependent packages (meta, signed, lbm, etc.) are fully built
        is returned.
        '''
        retval = True

        bi = s.build_info
        for pkg in bi:
            pkg_built = False
            try:
                for pocket in bi[pkg]:
                    if bi[pkg][pocket]['built']:
                        pkg_built = True
                        break
            except KeyError:
                pkg_built = False

            if not pkg_built:
                cinfo('        %s is not fully built yet.' % (pkg), 'yellow')
                retval = False
                break

        return retval

    # all_dependent_packages_uploaded
    #
    @property
    def all_dependent_packages_uploaded(s):
        '''
        For the kernel package associated with this bug, the status of whether or
        not all of the dependent packages (meta, signed, lbm, etc.) are uploaded
        is returned.
        '''
        retval = True

        bi = s.build_info
        for pkg in bi:
            pkg_uploaded = False
            try:
                for pocket in bi[pkg]:
                    if bi[pkg][pocket]['status'] in ['BUILDING', 'FULLYBUILT', 'FULLYBUILT_PENDING', 'FAILEDTOBUILD']:
                        pkg_uploaded = True
                        break
            except KeyError:
                pkg_uploaded = False

            if not pkg_uploaded:
                cinfo('        %s is not uploaded.' % (pkg), 'yellow')
                retval = False
                break

        return retval


    # uploaded
    #
    def uploaded(s, pkg):
        '''
        '''
        center(s.__class__.__name__ + '.uploaded')
        retval = False

        bi = s.build_info
        for pocket in bi[pkg]:
            if bi[pkg][pocket]['status'] in ['BUILDING', 'FULLYBUILT', 'FAILEDTOBUILD']:
                retval = True

        cleave(s.__class__.__name__ + '.uploaded (%s)' % (retval))
        return retval

    def upload_version(s, pkg):
        '''
        '''
        center(s.__class__.__name__ + '.upload_version')
        retval = None

        bi = s.build_info
        for pocket in bi[pkg]:
            if bi[pkg][pocket]['status'] in ['BUILDING', 'FULLYBUILT', 'FAILEDTOBUILD', 'FULLYBUILT_PENDING']:
                retval = bi[pkg][pocket]['version']
                break

        cleave(s.__class__.__name__ + '.upload_version (%s)' % (retval))
        return retval

    # ready_for_testing
    #
    @property
    def ready_for_testing(s):
        '''
        In order to determine if we're ready for testing the packages need to be
        fully built and published to -proposed. We build in a delay after these
        two conditions are met so that the packages are available in the archive
        to the lab machines that will be installing them.
        '''
        center(s.__class__.__name__ + '.ready_for_testing')
        retval = False
        if s.all_built_and_in_proposed:

            # Find the most recent date of either the publish date/time or the
            # date/time of the last build of any arch of any of the dependent
            # package.
            #
            date_available = None
            bi = s.build_info
            for d in sorted(bi):
                for p in sorted(bi[d]):
                    if bi[d][p]['published'] is None:
                        continue
                    if bi[d][p]['most_recent_build'] is None:
                        continue

                    if bi[d][p]['published'] > bi[d][p]['most_recent_build']:
                        if date_available is None or bi[d][p]['published'] > date_available:
                            date_available = bi[d][p]['published']
                    else:
                        if date_available is None or bi[d][p]['most_recent_build'] > date_available:
                            date_available = bi[d][p]['most_recent_build']
            now = datetime.utcnow()
            comp_date = date_available + timedelta(hours=1.5)
            if comp_date < now:
                # It has been at least 1 hours since the package was either published or fully built
                # in proposed.
                #
                retval = True
            else:
                cinfo('It has been less than 1 hr since the last package was either published or built.')
                cinfo('    build time + 1 hrs: %s' % comp_date)
                cinfo('                   now: %s' % now)

        cinfo('        Ready for testing: %s' % (retval), 'yellow')
        cleave(s.__class__.__name__ + '.ready_for_testing (%s)' % (retval))
        return retval

    # relevant_packages_list
    #
    def relevant_packages_list(s):
        '''
        For every tracking bug there are 'prepare-package-*' tasks. Not every tracking bug has all the
        same 'prepare-pacakge-*' tasks. Also, there is a specific package associated with each of the
        'prepare-package-*' tasks.

        This method builds a list of the packages that are relevant to this particular bug.
        '''
        return sorted(s.pkgs.values())

    def check_component_in_pocket(s, tstamp_prop, pocket):
        """
        Check if packages for the given tracking bug were properly copied
        to the right component in the given pocket.
        """
        center(s.__class__.__name__ + '.check_component_in_pocket')
        cdebug('tstamp_prop: ' + tstamp_prop)
        cdebug('     pocket: %s' % pocket)

        # If the packages are not all built and in -proposed then just bail out of
        # here.
        #
        if not s.ready_for_testing:
            cleave(s.__class__.__name__ + '.check_component_in_pocket (False)')
            return False

        check_component = CheckComponent(s.lp, s)

        pkg_list = s.relevant_packages_list()

        primary_src_component = None
        missing_pkg = []
        mis_lst = []
        for pkg in pkg_list:
            if pkg == s.name:
                check_ver = s.version
            else:
                check_ver = None

            ps = check_component.get_published_sources(s.series, pkg, check_ver, pocket)
            if not ps:
                if check_ver:
                    missing_pkg.append([pkg, check_ver])
                elif 'linux-signed' in pkg:
                    missing_pkg.append([pkg, 'for version=%s' % (s.version)])
                else:
                    missing_pkg.append([pkg, 'with ABI=%s' % (s.abi)])
                continue

            # We are going to use the primary package source component as
            # our guide.  If we do not have that, then we cannot check.
            if pkg == s.name:
                primary_src_component = ps[0].component_name

            if 'linux-signed' in pkg:
                src_ver = ps[0].source_package_version
                if src_ver.startswith(s.version):
                    mis_lst.extend(check_component.mismatches_list(s.series,
                                   pkg, ps[0].source_package_version,
                                   pocket, ps, primary_src_component))
                else:
                    missing_pkg.append([pkg, 'for version=%s' % (s.version)])
            elif not check_ver:
                src_ver = ps[0].source_package_version

                # source_package_version for linux-ports-meta and linux-meta is
                # <kernel-version>.<abi>.<upload #> and for linux-backports-modules
                # it is <kernel-version-<abi>.<upload #>
                #
                v1 = s.bug.kernel_version + '.' + s.abi
                v2 = s.bug.kernel_version + '-' + s.abi
                if src_ver.startswith(v1) or src_ver.startswith(v2):
                    mis_lst.extend(check_component.mismatches_list(s.series,
                                   pkg, ps[0].source_package_version,
                                   pocket, ps, primary_src_component))
                else:
                    missing_pkg.append([pkg, 'with ABI=%s' % (s.abi)])
            else:
                mis_lst.extend(check_component.mismatches_list(s.series,
                               pkg, check_ver, pocket, ps, primary_src_component))

        if missing_pkg:
            cdebug('missing_pkg is set')
            cinfo('        packages not yet available in pocket')
            cdebug('check_component_in_pocket leave (False)')
            return False

        if mis_lst:
            cdebug('mis_lst is set')

            task_name = 'promote-to-%s' % (pocket,)
            cinfo('        checking %s task status is %s' % (task_name, s.tasks_by_name[task_name].status))
            if s.tasks_by_name[task_name].status != 'Incomplete':
                s.tasks_by_name[task_name].status = 'Incomplete'

                body  = "The following packages ended up in the wrong"
                body += " component in the -%s pocket:\n" % (pocket)
                for item in mis_lst:
                    cdebug('%s %s - is in %s instead of %s' % (item[0], item[1], item[2], item[3]), 'green')
                    body += '\n%s %s - is in %s instead of %s' % (item[0], item[1], item[2], item[3])

                subject = '[ShankBot] [bug %s] Packages copied to the wrong component' % (s.lpbug.id)
                to_address  = "kernel-team@lists.ubuntu.com"
                to_address += ", ubuntu-installer@lists.ubuntu.com"
                cinfo('        sending email alert')
                s.send_email(subject, body, to_address)

                body += "\n\nOnce this is fixed, set the "
                body += "promote-to-%s to Fix Released again" % (pocket)
                s.add_comment('Packages outside of proper component', body)

            cinfo('        packages ended up in the wrong pocket')
            cdebug('check_component_in_pocket leave (False)')
            return False

        cleave(s.__class__.__name__ + '.check_component_in_pocket (True)')
        return True

