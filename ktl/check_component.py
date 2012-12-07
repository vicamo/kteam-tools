#!/usr/bin/env python
#

from ktl.utils                          import error
import sys, os, re
common_lib = os.path.dirname(os.path.abspath(sys.argv[0]))
common_lib = os.path.dirname(common_lib)
common_lib = os.path.join(common_lib, "lib")
sys.path.insert(0, common_lib)
from buildenv_lib                       import GetUploadVersion

#
# CheckComponent
#
# This class uses the launchpad api to list components where packages
# landed or checking for their component mismatches. Intended to check
# kernel set packages, but can be extended or used with all packages
#
class CheckComponent():

    def __init__(self, lp):
        self.lp = lp
        # note: for package names with ABI in the name, replace the
        # number with the string 'ABI'
        self.override_db = { 'hardy': {
                               'linux-meta' : {
                                 'linux-restricted-modules-server' : 'restricted'
                               },
                               'linux-backports-modules-2.6.24' : {
                                 'updates-modules-2.6.24-ABI-lpia-di' : 'main'
                               }
                             }
                           }
        self.release_db = {}
        self.abi_db = {}
        return

    def load_release_components(self, series, package):
        ubuntu = self.lp.launchpad.distributions["ubuntu"]
        archive = ubuntu.main_archive
        lp_series = ubuntu.getSeries(name_or_version=series)
        rel_ver = GetUploadVersion(series, package, pocket="release")
        if rel_ver:
            pkg_rel = archive.getPublishedSources(exact_match=True,
                        source_name=package,
                        distro_series=lp_series,
                        pocket='Release',
                        version=rel_ver)
            if pkg_rel:
                src_pkg = pkg_rel[0]
                self.release_db[package] = {}
                self.release_db[package][None] = src_pkg.component_name
                for bin_pkg in src_pkg.getPublishedBinaries():
                    bname = bin_pkg.binary_package_name
                    bcomponent = bin_pkg.component_name
                    self.release_db[package][bname] = bcomponent
        return

    def entry_override_db(self, series, package, bin_pkg, default):
        if series in self.override_db:
            if package in self.override_db[series]:
                if bin_pkg in self.override_db[series][package]:
                    return self.override_db[series][package][bin_pkg]
        return default

    def default_component(self, dcomponent, series, package, bin_pkg):
        if not self.release_db:
            self.load_release_components(series, package)
        if package in self.release_db:
            if bin_pkg in self.release_db[package]:
                return self.release_db[package][bin_pkg]
        return dcomponent

    def override_component(self, dcomponent, series, package, bin_pkg):
        comp = self.entry_override_db(series, package, bin_pkg, None)
        if comp:
            return comp
        if series != 'hardy' and package == 'linux-meta':
            if (bin_pkg and bin_pkg.startswith('linux-backports-modules-') and
                (not bin_pkg.endswith('-preempt'))):
                return 'main'
        return self.default_component(dcomponent, series, package, bin_pkg)

    def main_component(self, dcomponent, series, package, bin_pkg):
        return 'main'

    def name_abi_transform(self, name):
        if not name:
            return name
        abi = re.findall('([0-9]+\.[^ ]+)', name)
        if abi:
            abi = abi[0]
            abi = abi.split('-')
            if len(abi) >= 2:
                abi = abi[1]
            else:
                abi = None
            if abi:
                version = re.findall('([0-9]+\.[^-]+)', name)
                if version:
                    version = version[0]
                    name = name.replace('%s-%s' % (version, abi),
                                        '%s-ABI' % version)
        return name

    def linux_abi_component(self, dcomponent, series, package, bpkg):
        if package in self.abi_db:
            mpkg = self.name_abi_transform(bpkg)
            if mpkg in self.abi_db[package]:
                return self.entry_override_db(series, package, mpkg,
                                              self.abi_db[package][mpkg])
            else:
                if package.startswith('linux-backports-modules-'):
                    if not bpkg or not bpkg.endswith('-preempt'):
                        return 'main'
                return 'universe'

        ubuntu = self.lp.launchpad.distributions["ubuntu"]
        archive = ubuntu.main_archive
        lp_series = ubuntu.getSeries(name_or_version=series)
        rel_ver = GetUploadVersion(series, package, pocket="release")
        if rel_ver:
            pkg_rel = archive.getPublishedSources(exact_match=True,
                        source_name=package,
                        distro_series=lp_series,
                        pocket='Release',
                        version=rel_ver)
            if pkg_rel:
                src_pkg = pkg_rel[0]
                self.abi_db[package] = {}
                self.abi_db[package][None] = src_pkg.component_name
                for bin_pkg in src_pkg.getPublishedBinaries():
                    bname = self.name_abi_transform(bin_pkg.binary_package_name)
                    self.abi_db[package][bname] = bin_pkg.component_name
            else:
                self.abi_db[package] = {}
        else:
            self.abi_db[package] = {}
        return self.linux_abi_component(dcomponent, series, package, bpkg)

    def component_function(self, series, package):
        if (package == 'linux') or (package == 'linux-signed'):
            # Everything on linux package should be on 'main'. Except
            # for hardy and lucid, where we had some things on universe
            # etc., so we use the linux_abi_component that will check
            # also where packages were on 'release' pocket
            if series in [ 'hardy', 'lucid' ]:
                return self.linux_abi_component
            return self.main_component
        if (package == 'linux-meta'):
            # Some precise meta packages were new and never released
            # originally, so they will default to 'universe' in the
            # checker. All of them should be on main anyway, so always
            # return 'main'
            if series in [ 'precise' ]:
                return self.main_component
            return self.override_component
        if package.startswith('linux-backports-modules-'):
            return self.linux_abi_component
        if package.startswith('linux-restricted-modules-'):
            return self.linux_abi_component
        if package.startswith('linux-ubuntu-modules-'):
            return self.linux_abi_component
        if (package.startswith('linux-lts-') or
            package.startswith('linux-meta-lts-')):
            return self.main_component
        if package in ['linux-ec2', 'linux-fsl-imx51', 'linux-ti-omap4',
                       'linux-mvl-dove', 'linux-armadaxp']:
            return self.main_component
        if (package.startswith('linux-signed') or
            package.startswith('kernel-signed')):
            return self.main_component
        return self.default_component

    def get_published_sources(self, series, package, version, pocket):
        if not version:
            version = GetUploadVersion(series, package, pocket=pocket)
            if not version:
                error("No upload of %s for %s is currently available in"
                      " the %s pocket" % (package, series, pocket))
                return None
        ubuntu = self.lp.launchpad.distributions["ubuntu"]
        archive = ubuntu.main_archive
        lp_series = ubuntu.getSeries(name_or_version=series)
        ps = archive.getPublishedSources(exact_match=True,
                                         source_name=package,
                                         distro_series=lp_series,
                                         pocket=pocket.title(),
                                         version=version)
        if not ps:
            error("No results returned by getPublishedSources")
        return ps

    def components_list(self, series, package, version, pocket, ps = None):
        clist = []
        if not ps:
            ps = self.get_published_sources(series, package, version, pocket)
        if ps:
            src_pkg = ps[0]
            clist.append([src_pkg.source_package_name,
                          src_pkg.source_package_version,
                          src_pkg.component_name])
            for bin_pkg in src_pkg.getPublishedBinaries():
                clist.append([bin_pkg.binary_package_name,
                              bin_pkg.binary_package_version,
                              bin_pkg.component_name])
        return clist

    def mismatches_list(self, series, package, version, pocket, ps = None):
        mlist = []
        self.release_db = {}
        self.abi_db = {}
        get_component = self.component_function(series, package)
        if not ps:
            ps = self.get_published_sources(series, package, version, pocket)
        if ps:
            src_pkg = ps[0]
            component = get_component('universe', series, package, None)
            if src_pkg.component_name != component:
                mlist.append([src_pkg.source_package_name,
                              src_pkg.source_package_version,
                              src_pkg.component_name, component])
            for bin_pkg in src_pkg.getPublishedBinaries():
                pkg_name = bin_pkg.binary_package_name
                component = get_component('universe', series, package, pkg_name)
                if bin_pkg.component_name != component:
                    mlist.append([bin_pkg.binary_package_name,
                                  bin_pkg.binary_package_version,
                                  bin_pkg.component_name, component])
        return mlist

# vi:set ts=4 sw=4 expandtab:

