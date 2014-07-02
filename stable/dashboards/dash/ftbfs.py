#!/usr/bin/env python
#

from dash.dbg                            import Dbg

class Ftbfs(dict):

    # __init__
    #
    def __init__(self, lp, *args):
        Dbg.enter("Builders.__init__")

        dict.__init__(self, args)

        self.lp = lp
        self.failure = {'Failed to build' : 'Build failed', 'Dependency wait' : 'Waiting on dependency', 'Chroot problem' : 'Chroot problem', 'Failed to upload' : 'Upload failed'}
        self.default_arch_list = ('i386', 'amd64', 'armel', 'armhf', 'powerpc')
        self.archive_by_arch = {}

        problem_states = ('Failed to build', 'Dependency wait', 'Chroot problem', 'Failed to upload')

        ubuntu = self.lp.distributions['ubuntu']
        series = ubuntu.current_series
        #self.distro_series_info(series)

        #for ps in lp.packagesets:
        #    self.packageset_info(ps)
        #    srcs = ps.getSourcesIncluded(direct_inclusion=False)

        states = {}
        for state in problem_states:
            #print("state: %s" % (state))
            build_recs = series.getBuildRecords(build_state = state)

            br = {}
            stats = {}
            for build in build_recs:
                if not build.current_source_publication_link: continue
                if build.arch_tag not in self.default_arch_list: continue

                csp = build.current_source_publication
                t = {}
                t["name"] = csp.source_package_name
                t["arch"] = build.arch_tag
                t["archive"] = self.archive(build.arch_tag)
                #t["version"] = csp.source_package_version
                #t["pocket"] = csp.pocket
                #print("       name: %s" % (csp.source_package_name))
                #print("    version: %s" % (csp.source_package_version))
                #print("     pocket: %s" % (csp.pocket))
                #print("       arch: %s" % (build.arch_tag))
                #self.person_info(csp.package_creator)

                try:
                    br[csp.source_package_name].append(t)
                except KeyError:
                    br[csp.source_package_name] = [t]

                try:
                    stats[build.arch_tag] += 1
                except KeyError:
                    stats[build.arch_tag] = 1

            self[self.failure[state]] = br
            self[self.failure[state]]['__stats__'] = stats

        Dbg.leave("Builders.__init__")

    def archive(self, arch):
        try:
            return self.archive_by_arch[arch]
        except KeyError:
            ubuntu = self.lp.distributions['ubuntu']
            series = ubuntu.current_series
            das = series.getDistroArchSeries(archtag = arch)
            self.archive_by_arch[arch] = das.official and 'main' or 'ports'
            return self.archive_by_arch[arch]

# vi:set ts=4 sw=4 expandtab:
