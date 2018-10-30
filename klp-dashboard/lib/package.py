#!/usr/bin/env python
#

import re
from datetime                           import datetime
import json
import urllib.request

from .ubuntu                            import Ubuntu
from .errors                            import LKPError, ErrorExit
from klog.log                           import cdebug, cerror, cwarn, center, cleave, Clog, cinfo

# PackageError
#
class PackageError(LKPError):
    '''
    Thrown when some basic information about the package that is associated with the
    shankbug could not be determined.
    '''
    def __init__(s, emsg):
        s.message = emsg

# SeriesLookupFailure
#
class SeriesLookupFailure(LKPError):
    '''
    Thrown when the series lookup throws a KeyError exception.
    '''
    def __init__(s, emsg):
        super(LKPError, s).__init__(emsg)

def dump(obj):
    for l in json.dumps(obj, sort_keys=True, indent=4).split('\n'):
        cinfo(l, 'green')

# Package
#
class Package():

    #                              .- package name (group(1))
    #                             /           .- package version (group(2))
    #                            /           /
    #                           /           /
    package_rc = re.compile("(\S+): (\d+\.\d+)")

    #
    #                                             .- kernel version (group(2))
    #                                            /          .- version/abi separator (group(3))
    #                                           /          /
    kernel_rc  = re.compile("livepatch-linux-(\d+\.\d+\.\d+)([-\.])(\d+)\.(\d+)([+a-z\d.]*)-([a-z-]+)")
    #                                                           /      /       /            .- flavour block
    #                                                          /      /       .- backport extra (m.group(6))
    #                                                         /      .- upload number (m.group(5))
    #                                                        .- abi (group(4))

    # __init__
    #
    def __init__(s, lp, lpbug):
        center(s.__class__.__name__ + '.__init__')
        s.lp = lp

        s.ubuntu = Ubuntu()
        s.__distro_series = None

        s.builder_ppas = []
        team = s.lp.people['canonical-livepatch-kernel']
        for ppa in team.ppas:
            if ppa.name.startswith("builder") and "deleted" not in ppa.name:
                s.builder_ppas.append(ppa)

        team = s.lp.people['canonical-livepatch']
        s.proposed_ppa = team.getPPAByName(name='proposed')
        s.updates_ppa = team.getPPAByName(name='updates')

        s.main_archive = s.lp.distributions["ubuntu"].main_archive

        # Determine some properties of the package we are looking at based on the
        # bug title. This information is used further on.
        #
        s.package = s.__title_decode(lpbug.title)
        if not s.valid:
            raise PackageError(['Unable to check package builds for this bug: either the package name or',
                                'the version is not properly indicated in the bug title.'])

        s.pkgs = s.dependent_packages
        s._cache = None

        cleave(s.__class__.__name__ + '.__init__')

    def __title_decode(s, txt):
        center(s.__class__.__name__ + '.__title_decode')
        m = Package.package_rc.search(txt)
        setattr(s, 'valid', False)
        if m is not None:
            setattr(s, 'name', m.group(1))
            setattr(s, 'version', '%s' % (m.group(2)))
            setattr(s, 'hwe', False)

            m = Package.kernel_rc.search(s.name)
            if m is not None:
                setattr(s, 'kernel_version', '%s%s%s.%s%s' % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5).replace('+', '~')))
                setattr(s, 'kernel', m.group(1))
                setattr(s, 'kernel_abi', m.group(3))
                setattr(s, 'kernel_flavour', m.group(6))
                s.kernel_package = 'linux-%s' % m.group(6)
                try:
                    if m.group(5): # it's an LTS or HWE kernel
                        setattr(s, 'kernel_series', s.ubuntu.series_name('linux-lts-', s.kernel_version))
                        setattr(s, 'hwe', True)
                    else: # regular kernel
                        setattr(s, 'kernel_series', s.ubuntu.series_name('linux', s.kernel_version))

                    setattr(s, 'kernel_series_version', s.ubuntu.index_by_series_name[s.kernel_series]['series_version'])

                    # the test series is the series the kernel originated from (i.e. ignore the lts tag).
                    setattr(s, 'test_series', s.ubuntu.lookup(m.group(1))['name'])
                    setattr(s, 'test_series_version', s.ubuntu.index_by_series_name[s.test_series]['series_version'] )

                except KeyError:
                    raise SeriesLookupFailure(['Unable to determine the series from the kernel version specified',
                                               'in the bug title.'])
                setattr(s, 'valid', True)
            else:
                cwarn(' ** Was unable to determine the kernel version from the package name (%s)' % s.name)
        else:
            cwarn(' ** Was unable to determine the package name and the package version from the title (%s)' % txt)

        cleave(s.__class__.__name__ + '.__title_decode')

    # __determine_build_status
    #
    def __determine_build_status(s):
        center(s.__class__.__name__ + '.__determine_build_status')

        s._cache = {}
        for dep in iter(s.pkgs):
            cdebug('')
            cdebug('%s: ' % dep, 'blue')
            if dep in s._cache:
                break
            Clog.indent += 4

            abi = None
            version = s.version

            s._cache[dep] = {}
            for builder in s.builder_ppas:
                info = s.__is_fully_built(s.pkgs[dep], abi, builder, version, None)
                s._cache[dep][builder.name] = {}
                s._cache[dep][builder.name]['built']   = info[0]
                s._cache[dep][builder.name]['creator'] = info[1]
                s._cache[dep][builder.name]['signer']  = info[2]
                s._cache[dep][builder.name]['published'] = info[3]
                s._cache[dep][builder.name]['most_recent_build'] = info[4]
                s._cache[dep][builder.name]['status'] = info[5]
                cinfo('        %-8s : %-5s / %-10s    (%s : %s)' % (builder.name, info[0], info[5], info[3], info[4]), 'cyan')

            info = s.__is_fully_built(s.pkgs[dep], abi, s.proposed_ppa, version, None)
            s._cache[dep]['proposed'] = {}
            s._cache[dep]['proposed']['built']   = info[0]
            s._cache[dep]['proposed']['creator'] = info[1]
            s._cache[dep]['proposed']['signer']  = info[2]
            s._cache[dep]['proposed']['published'] = info[3]
            s._cache[dep]['proposed']['most_recent_build'] = info[4]
            s._cache[dep]['proposed']['status'] = info[5]
            cinfo('        %-8s : %-5s / %-10s    (%s : %s)' % ('proposed', info[0], info[5], info[3], info[4]), 'cyan')

            info = s.__is_fully_built(s.pkgs[dep], abi, s.updates_ppa, version, None)
            s._cache[dep]['updates'] = {}
            s._cache[dep]['updates']['built']   = info[0]
            s._cache[dep]['updates']['creator'] = info[1]
            s._cache[dep]['updates']['signer']  = info[2]
            s._cache[dep]['updates']['published'] = info[3]
            s._cache[dep]['updates']['most_recent_build'] = info[4]
            s._cache[dep]['updates']['status'] = info[5]
            cinfo('        %-8s : %-5s / %-10s    (%s : %s)' % ('updates', info[0], info[5], info[3], info[4]), 'cyan')

            Clog.indent -= 4

        cdebug('')
        cdebug('The Cache:', 'cyan')
        for d in s._cache:
            cdebug('    %s' % d, 'cyan')
            for p in s._cache[d]:
                cdebug('        %-8s : %s' % (p, s._cache[d][p]['built']), 'cyan')

        cleave(s.__class__.__name__ + '.__determine_build_status')
        return None

    # __is_fully_built
    #
    def __is_fully_built(s, package, abi, archive, release=None, pocket=''):
        '''
        Have the source package specified been fully built?
        '''
        center(s.__class__.__name__ + '.__is_fully_built')
        cdebug('')
        center('Sources::__is_fully_built')
        cdebug('package: %s' % package, 'yellow')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('archive: %s' % archive, 'yellow')
        cdebug('release: %s' % release, 'yellow')
        cdebug(' pocket: %s' % pocket, 'yellow')
        retval = False

        ps = s.__get_published_sources(package, abi, archive, release, pocket)
        matches = s.__find_matches(ps, abi, release)
        if len(matches) > 0:
            cdebug('    match: %s (%s)' % (release, abi), 'green')
            fullybuilt, creator, signer, published, most_recent_build, status = s.__sources_built(matches, archive, package, release, pocket)
        else:
            fullybuilt   = False
            status  = ''
            creator = None
            signer  = None
            published = None
            most_recent_build = None

        cleave(s.__class__.__name__ + '.__is_fully_built (%s)' % retval)
        return fullybuilt, creator, signer, published, most_recent_build, status

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

        center('Sources::__get_published_sources')
        cdebug('package: %s' % package, 'yellow')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('archive: %s' % archive, 'yellow')
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

        cleave(s.__class__.__name__ + '.__get_published_sources')
        return ps

    # __find_matches
    #
    def __find_matches(s, ps, abi, release):
        center(s.__class__.__name__ + '.__find_matches')
        center('Sources::__find_matches')
        cdebug('    abi: %s' % abi,     'yellow')
        cdebug('release: %s' % release, 'yellow')

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
        else:
            cdebug('exact version match required')
            for p in ps:
                src_ver = p.source_package_version
                cdebug('adding: %s' % src_ver, 'green')
                matches.append(p)

        cleave(s.__class__.__name__ + '.__find_matches')
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
                cdebug('"%s" %s built (pocket:%s)' % (package, release, pocket), 'green')
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
            if s.kernel_series:
                sc = s.lp.distributions["ubuntu"].series_collection
                for ds in sc:
                    if ds.name == s.kernel_series:
                        s.__distro_series = ds
                        break

            if s.__distro_series is None:
                emsg = "        ERROR: can't figure out the distro series for %s-%s\n" % (s.name, s.version)
                cerror(emsg)
                raise ErrorExit(emsg)

        return s.__distro_series

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
            for package in s.srcs:
                if not s.srcs[package]['proposed']['built']:
                    retval = False
                    break

        cleave('Packages::ready_for_testing (%s)' % retval)
        return retval

    # released
    #
    @property
    def released(s):
        '''
        '''
        center('Packages::released')
        retval = False
        if s.all_dependent_packages_fully_built:
            retval = True
            for package in s.srcs:
                if not s.srcs[package]['updates']['built']:
                    retval = False
                    break

        cleave('Packages::released (%s)' % retval)
        return retval

    # ready_for_proposed
    #
    @property
    def ready_for_proposed(s):
        '''
        All dependent packages are fully built and in the proposed pocket.
        '''
        center(s.__class__.__name__ + '.ready_for_proposed')
        retval = True

        for pkg in s.srcs:
            for builder in s.builder_ppas:
                try:
                    pkg_built = s.srcs[pkg][builder.name]['built']
                except KeyError:
                    pkg_built = False
                if pkg_built:
                    cdebug('Packages built in "%s" PPA' % (builder.name), 'green')
                    break

            if not pkg_built:
                cinfo('        %s is either not fully built yet or not in proposed.' % pkg, 'red')
                retval = False
                break

        cleave(s.__class__.__name__ + '.ready_for_proposed (%s)' % (retval))
        return retval

    # present_in_swift
    def present_in_swift(s, bucket):
        center(s.__class__.__name__ + '.present_in_swift')
        retval = False
        pkgname = 'livepatch-%s-%s-%s.tar.bz2' % (s.kernel_version, s.kernel_flavour, s.version)
        url='https://livepatch.canonical.com:335/api/restricted/patch-tier/%s' % bucket

        cdebug('checking for %s in %s' % (pkgname, bucket))
        try:
            with urllib.request.urlopen(url) as page:
                if page.headers.get_content_charset() is None:
                    list = page.read().decode('utf-8')
                else:
                    list = page.read().decode(page.headers.get_content_charset())

            if pkgname in list:
                retval = True
        except Exception:
            cdebug('exception occurred, will try again later')

        cleave(s.__class__.__name__ + '.present_in_swift (%s)' % (retval))
        return retval

