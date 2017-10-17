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

        cdebug('CheckComponent::__init__ leave')
        return

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

    def mismatches_list(self, series, package, version, pocket, ps=None, component=None):
        '''
        Return a list of the source and binary components that are not in the correct repository.
        '''
        cdebug("CheckComponent::mismatches_list enter")
        cdebug("         series: %s" % series)
        cdebug("        package: %s" % package)
        cdebug("        version: %s" % version)
        cdebug("         pocket: %s" % pocket)
        cdebug("      component: %s" % component)

        mlist = []
        if not ps:
            ps = self.get_published_sources(series, package, version, pocket)
        if ps:
            src_pkg = ps[0]
            if not component:
                component = src_pkg.component_name
            if src_pkg.component_name != component:
                cdebug("        src package name: %s" % src_pkg.source_package_name, 'cyan')
                cdebug("            src_pkg.component_name: %s      component: %s" % (src_pkg.component_name, component), 'cyan')
                mlist.append([src_pkg.source_package_name, src_pkg.source_package_version, src_pkg.component_name, component])

            for bin_pkg in src_pkg.getPublishedBinaries():
                pkg_name = bin_pkg.binary_package_name
                if bin_pkg.component_name != component:
                    cdebug("        bin package name: %s" % bin_pkg.binary_package_name, 'cyan')
                    cdebug("            bin_pkg.component_name: %s      component: %s" % (bin_pkg.component_name, component), 'cyan')
                    mlist.append([bin_pkg.binary_package_name, bin_pkg.binary_package_version, bin_pkg.component_name, component])

        cdebug("CheckComponent::mismatches_list leave")
        return mlist

# vi:set ts=4 sw=4 expandtab:
