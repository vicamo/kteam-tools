#!/usr/bin/env python
#

import re

from lpltk.LaunchpadService             import LaunchpadService
from ktl.ubuntu                         import Ubuntu

from sb.exceptions                      import GeneralError
from sb.log                             import Clog, cinfo, cdebug, cerror, cwarn

# KernelPackageVersion
#
class KernelPackageVersion():
    '''
    Given a kernel version string, break it down into its various components to make
    it easier for users to access those individual components.
    '''
    def __init__(s, txt):
        matched = False
        #                                       .- package name (group(1))
        #                                      /           .- kernel version (group(2))
        #                                     /           /          .- version/abi separator (group(3))
        #                                    /           /          /
        ver_with_pkg_rc     = re.compile("(\S+): (\d+\.\d+\.\d+)([-\.])(\d+)\.(\d+)([~a-z\d]*)")
        #                                                                /      /       /
        #                                                               /      /       .- backport extra (m.group(6))
        #                                                              /      .- upload number (m.group(5))
        #                                                             .- abi (group(4))

        #                                  .- kernel version (group(1))
        #                                 /          .- version/abi separator (group(2))
        #                                /          /
        ver_rc     = re.compile("(\d+\.\d+\.\d+)([-\.])(\d+)\.(\d+)([~a-z\d]*)")
        #                                                /      /       /
        #                                               /      /       .- backport extra (m.group(5))
        #                                              /      .- upload number (m.group(4))
        #                                             .- abi (group(3))

        setattr(s, 'valid', False)
        m = ver_with_pkg_rc.search(txt)
        if m is not None:
            matched = True
            setattr(s, 'package', m.group(1))
            setattr(s, 'full', '%s%s%s.%s%s' % (m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
            setattr(s, 'kernel', m.group(2))
            setattr(s, 'abi', m.group(4))
            setattr(s, 'upload', m.group(5))
            setattr(s, 'extra', m.group(6))
            setattr(s, 'sep', m.group(2))
            s.valid = True
        else:
            m = ver_rc.search(txt)
            if m is not None:
                matched = True
                setattr(s, 'package', '')
                setattr(s, 'full', '%s%s%s.%s%s' % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
                setattr(s, 'kernel', m.group(1))
                setattr(s, 'abi', m.group(3))
                setattr(s, 'upload', m.group(4))
                setattr(s, 'extra', m.group(5))
                setattr(s, 'sep', m.group(2))
                s.valid = True

        if matched:
            cdebug('    package: %s' % (s.package))
            cdebug('       full: %s%s%s.%s%s' % (s.kernel, s.sep, s.abi, s.upload, s.extra))
            cdebug('     kernel: %s' % s.kernel)
            cdebug('        abi: %s' % s.abi)
            cdebug('     upload: %s' % s.upload)
            cdebug('      extra: %s' % s.extra)

        if not matched:
            cwarn(' ** None of the regular expressions matched the title (%s)' % txt)

# KernelPackageError
#
class KernelPackageError(GeneralError):
    '''
    Thrown when some basic information about the package that is associated with the
    shankbug could not be determined.
    '''
    def __init__(s, emsg):
        GeneralError(emsg)

# KernelPackageBuildStatus
#
class KernelPackageBuildStatus():

    # __init__
    #
    def __init__(s):
        s.built    = False
        s.building = False
        s.missing  = False
        s.pkg      = None

    def __str__(s):
        return "built: %5s; building: %5s; missing: %5s" % (s.built, s.building, s.missing)

# KernelPackage
#
class KernelPackage():

    # __init__
    #
    def __init__(s, lp, version):
        cdebug('KPac::__init__ enter')
        s.__distro_series = None

        s.lp = lp
        s.ubuntu = Ubuntu()
        ckt = s.lp.launchpad.people['canonical-kernel-team']
        s.ckt_ppa = ckt.getPPAByName(name='ppa')
        s.main_archive = s.lp.launchpad.distributions["ubuntu"].main_archive

        cdebug('Kernel Package:', 'yellow')
        cdebug('       name: %s' % version.package)
        s.version = version
        s.name = s.version.package
        s.pkgs = s.dependent_packages
        cdebug('     series: %s' % s.distro_series)

        cdebug('')
        cdebug('    Dependents:', 'cyan')
        for pkg in s.pkgs:
            cdebug('        %s' % pkg)

        s.package_version_not_found  = 0
        s.package_version_building   = 1
        s.package_version_in_archive = 2

        s.determine_build_status()

        cdebug('KPac::__init__ leave')

    def is_in_pocket(s, pocket):
        retval = True

        # Check to see if all the dependencies have been built and are in the
        # proposed pocket.
        #
        for dep in s.status:
            if not s.status[dep]['status'][pocket].built:
                retval = False

        return retval

    # dependent_packages
    #
    @property
    def dependent_packages(s):
        '''
        Put together a list of all the packages that depend on this package.
        '''
        pkgs = {}
        series = s.ubuntu.series_name(s.name, s.version.full)
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
            series = s.ubuntu.series_name(s.name, s.version.full)
            if series:
                sc = s.lp.launchpad.distributions["ubuntu"].series_collection
                for ds in sc:
                    if ds.name == series:
                        s.__distro_series = ds
                        break

            if s.__distro_series is None:
                emsg = "        ERROR: can't figure out the distro series for %s-%s\n" % (s.name, s.version.full)
                cerror(emsg)
                raise KernelPackageError(emsg)

        return s.__distro_series

    # determine_build_status
    #
    def determine_build_status(s):
        """
        Verify the required packages for this update, and determine its
        build status
        """
        # Check build status. This is really convoluted... due to number
        # of tasks and we wanting the better behaviour as possible
        s.status = {}

        cdebug('')
        cdebug('    Determining Build Status', 'cyan')
        deps = []
        for dep in iter(s.pkgs):
            deps.append(dep)

        cdebug('        Dependent packages:')
        cdebug('')
        cdebug('            %s' % ' '.join(deps))
        cdebug('')


        cdebug('        Processing depedent packages:')
        for dep in iter(s.pkgs):
            cdebug('')
            cdebug('            %s:' % dep, 'yellow')

            abi_num = None
            pkg_rel = s.version.full
            if dep in [ 'lbm', 'meta', 'ports-meta' ] and s.version.abi:
                abi_num = s.version.abi
                pkg_rel = s.version.kernel

            status_updates = 0
            status_release = 0
            prepare_status = 0
            prepare_assignee = None
            prepare_uploader = None

            cdebug('                Stable Package', 'cyan')
            cdebug('')
            s.status[dep] = {}
            s.status[dep]['status'] = {}
            s.status[dep]['status']['ppa']      = s.build_status(s.pkgs[dep], abi_num, s.ckt_ppa,    pkg_rel)
            s.status[dep]['status']['proposed'] = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Proposed')
            s.status[dep]['status']['security'] = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Security')
            s.status[dep]['status']['updates']  = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Updates')
            s.status[dep]['status']['release']  = s.build_status(s.pkgs[dep], abi_num, s.main_archive, pkg_rel, 'Release')

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

        cdebug('                ---------------------------------------------------------------------------')
        cdebug('                Build Status')
        cdebug('')
        cdebug('                    package: %s' % package)
        cdebug('                        abi: %s' % abi)
        cdebug('                    archive: %s' % archive)
        cdebug('                    release: %s' % release)
        if pocket == '':
            cdebug('                     pocket: ppa')
        else:
            cdebug('                     pocket: %s' % pocket)
        cdebug('')
        pbs = KernelPackageBuildStatus()

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
                cdebug('                    src_ver: %s' % src_ver)
                if ((src_ver.startswith(dep_ver1 + '.') or src_ver.startswith(dep_ver2 + '.'))):
                    matches.append(p)
        else:
            rel_match = '<%s>' % (release)
            for p in ps:
                matches.append(p)

        retval = s.package_version_not_found, None
        status = 'missing'
        if not matches:
            cdebug('                    Can\'t find "%s" (%s) build on %s (pocket:%s)' % (package, rel_match, archive.displayname, pocket))
            pbs.pkg = None
        else:
            lst_date = None
            for pkg in matches:
                pbs.pkg = pkg
                src_id = str(pkg.self).rsplit('/', 1)[1]
                build_summaries = archive.getBuildSummariesForSourceIds(source_ids=[src_id])[src_id]
                if build_summaries['status'] == 'FULLYBUILT':
                    cdebug('                    "%s" %s built (pocket:%s)' % (package, rel_match, pocket))
                    bs = s.package_version_in_archive
                    status = 'built'
                    pbs.built = True
                else:
                    cdebug('                    "%s" %s not fully built yet, skipping (pocket:%s)' % (package, rel_match, pocket))
                    bs = s.package_version_building
                    status = 'building'
                    pbs.building = True
                # prefer newer published items...
                if lst_date:
                    if lst_date > pkg.date_published:
                        continue
                lst_date = pkg.date_published
                retval = bs, pkg

        cdebug('                    result: %s, %s' % (status, retval[1]), 'red')
        #return retval
        return pbs

# vi:set ts=4 sw=4 expandtab:

