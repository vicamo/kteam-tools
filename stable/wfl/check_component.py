#!/usr/bin/env python
#

import re
from .kernel_versions                   import KernelVersions
from .log                               import cdebug, cerror

#
# CheckComponent
#
# This class uses the launchpad api to list components where packages
# landed or checking for their component mismatches. Intended to check
# kernel set packages, but can be extended or used with all packages
#
class CheckComponent():

    def __init__(self, lp, package):
        cdebug('CheckComponent::__init__ enter')
        self.lp = lp
        self.package = package

        self.main_packages = [
            'linux-ec2',
            'linux-ti-omap4',
            'linux-armadaxp',
            'linux-keystone',
            'linux-meta-keystone',
            'linux-hwe',
            'linux-meta-hwe',
            'linux-signed-hwe',
            'linux-hwe-edge',
            'linux-meta-hwe-edge',
            'linux-signed-hwe-edge',
            'linux-aws',
            'linux-meta-aws',
            'linux-azure',
            'linux-meta-azure',
        ]

        self.release_db = {}
        self.abi_db = {}
        cdebug('CheckComponent::__init__ leave')
        return

    def load_release_components(self, series, package):
        cdebug('        CheckComponent::load_release_components enter')
        (archive, pocket) = self.package.routing("Release")
        ubuntu = self.lp.launchpad.distributions["ubuntu"]
        lp_series = ubuntu.getSeries(name_or_version=series)
        pkg_rel = archive.getPublishedSources(exact_match=True, source_name=package, distro_series=lp_series, status='Published', pocket=pocket)
        if pkg_rel:
            src_pkg = pkg_rel[0]
            self.release_db[package] = {}
            self.release_db[package][None] = src_pkg.component_name
            for bin_pkg in src_pkg.getPublishedBinaries():
                bname = bin_pkg.binary_package_name
                bcomponent = bin_pkg.component_name
                self.release_db[package][bname] = bcomponent
        cdebug('        CheckComponent::load_release_components leave')
        return

    def default_component(self, default, series, package, bin_pkg):
        cdebug('    CheckComponent::default_component enter')
        cdebug("            default: %s" % default)
        cdebug("             series: %s" % series)
        cdebug("            package: %s" % package)

        if not self.release_db:
            self.load_release_components(series, package)

        try:
            retval = self.release_db[package][bin_pkg]
        except KeyError:
            retval = default

        cdebug('    CheckComponent::default_component leave (%s)' % retval)
        return retval

    def override_component(self, default, series, package, bin_pkg):
        cdebug('    CheckComponent::override_component enter')
        cdebug("            default: %s" % default)
        cdebug("             series: %s" % series)
        cdebug("            package: %s" % package)
        cdebug("            bin_pkg: %s" % bin_pkg)
        retval = None
        if package == 'linux-meta':
            if bin_pkg:
                if bin_pkg.startswith('linux-backports-modules-') or bin_pkg.startswith('linux-hwe-') or bin_pkg.startswith('linux-image-hwe-'):
                    if not bin_pkg.endswith('-preempt'):
                        retval = 'main'

        if not retval:
            retval = self.default_component(default, series, package, bin_pkg)
        cdebug('    CheckComponent::override_component leave (%s)' % retval)
        return retval

    def main_component(self, default, series, package, bin_pkg):
        cdebug('    CheckComponent::main_component enter')
        cdebug('    CheckComponent::main_component leave (main)')
        return 'main'

    def name_abi_transform(self, name):
        cdebug('        CheckComponent::name_abi_transform enter')
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
        cdebug('        CheckComponent::name_abi_transform leave (%s)' % name)
        return name

    def linux_abi_component(self, dcomponent, series, package, bpkg):
        cdebug('    CheckComponent::linux_abi_component enter')
        if package in self.abi_db:
            mpkg = self.name_abi_transform(bpkg)
            if mpkg in self.abi_db[package]:
                cdebug('    CheckComponent::linux_abi_component leave')
                return self.abi_db[package][mpkg]
            else:
                if package.startswith('linux-backports-modules-'):
                    if not bpkg or not bpkg.endswith('-preempt'):
                        cdebug('    CheckComponent::linux_abi_component leave (main)')
                        return 'main'
                cdebug('    CheckComponent::linux_abi_component leave (universe)')
                return 'universe'

        ubuntu = self.lp.launchpad.distributions["ubuntu"]
        archive = ubuntu.main_archive
        lp_series = ubuntu.getSeries(name_or_version=series)
        pkg_rel = archive.getPublishedSources(exact_match=True, source_name=package, distro_series=lp_series, status='Published', pocket='Release')
        if pkg_rel:
            src_pkg = pkg_rel[0]
            self.abi_db[package] = {}
            self.abi_db[package][None] = src_pkg.component_name
            for bin_pkg in src_pkg.getPublishedBinaries():
                bname = self.name_abi_transform(bin_pkg.binary_package_name)
                self.abi_db[package][bname] = bin_pkg.component_name
        else:
            self.abi_db[package] = {}
        cdebug('    CheckComponent::linux_abi_component leave (?)')
        return self.linux_abi_component(dcomponent, series, package, bpkg)

    def component_function(self, series, package):
        '''
        Determine which method to use to figure out where the components should be ('main' or 'universe').
        '''
        cdebug("    CheckComponent::component_function enter")
        retval = self.default_component

        if (package == 'linux') or (package == 'linux-signed') or (package == 'linux-ppc'):
            # All linux package components should be in 'main' except for lucid where there
            # were some things on universe.
            #
            if series in ['lucid']:
                retval = self.linux_abi_component
            else:
                retval = self.main_component

        elif (package == 'linux-meta'):
            # Some precise meta packages were new and never released originally, so they will
            # default to 'universe' in the checker. All of them should be on main anyway, so
            # always return 'main'
            #
            if series in ['precise']:
                retval = self.main_component
            else:
                retval = self.override_component

        elif package.startswith('linux-backports-modules-'):
            retval = self.linux_abi_component

        elif (package.startswith('linux-lts-') or package.startswith('linux-meta-lts-') or package.startswith('linux-signed-lts-')):
            retval = self.main_component

        elif package in self.main_packages:
            retval = self.main_component

        else:
            cdebug("        NO MATCH")

        cdebug("    CheckComponent::component_function leave")
        return retval

    def get_published_sources(self, series, package, version, pocket):
        cdebug("    CheckComponent::get_published_sources enter")
        (archive, pocket) = self.package.routing(pocket.title())
        ubuntu = self.lp.launchpad.distributions["ubuntu"]
        lp_series = ubuntu.getSeries(name_or_version=series)
        if version:
            ps = archive.getPublishedSources(exact_match=True,
                                             source_name=package,
                                             distro_series=lp_series,
                                             pocket=pocket,
                                             version=version)
        else:
            ps = archive.getPublishedSources(exact_match=True,
                                             source_name=package,
                                             distro_series=lp_series,
                                             pocket=pocket,
                                             status='Published')
        if not ps:
            cerror("No results returned by getPublishedSources")
        cdebug("    CheckComponent::get_published_sources leave (ps)")
        return ps

    def components_list(self, series, package, version, pocket, ps=None):
        '''
        Return a list of all the source and binary components for a given package.
        '''
        cdebug("CheckComponent::components_list enter")

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

        cdebug("CheckComponent::components_list leave")
        return clist

    def mismatches_list(self, series, package, version, pocket, ps=None):
        '''
        Return a list of the source and binary components that are not in the correct repository.
        '''
        cdebug("CheckComponent::mismatches_list enter")
        cdebug("         series: %s" % series)
        cdebug("        package: %s" % package)
        cdebug("        version: %s" % version)
        cdebug("         pocket: %s" % pocket)

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
                cdebug("        src package name: %s" % src_pkg.source_package_name, 'cyan')
                cdebug("            src_pkg.component_name: %s      component: %s" % (src_pkg.component_name, component), 'cyan')
                mlist.append([src_pkg.source_package_name, src_pkg.source_package_version, src_pkg.component_name, component])

            for bin_pkg in src_pkg.getPublishedBinaries():
                pkg_name = bin_pkg.binary_package_name
                component = get_component('universe', series, package, pkg_name)
                if bin_pkg.component_name != component:
                    cdebug("        bin package name: %s" % bin_pkg.binary_package_name, 'cyan')
                    cdebug("            bin_pkg.component_name: %s      component: %s" % (bin_pkg.component_name, component), 'cyan')
                    mlist.append([bin_pkg.binary_package_name, bin_pkg.binary_package_version, bin_pkg.component_name, component])

        cdebug("CheckComponent::mismatches_list leave")
        return mlist

# vi:set ts=4 sw=4 expandtab:
