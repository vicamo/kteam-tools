#!/usr/bin/env python
#

from dash.dbg                           import Dbg
from dash.utils                         import date_to_string

class UbuntuReleases(dict):

    # __init__
    #
    def __init__(self, lp, *args):
        Dbg.enter("UbuntuReleases.__init__")

        dict.__init__(self, args)

        self.lp = lp
        ubuntu = lp.distributions['ubuntu']

        for s in ubuntu.series:
            ds = {}
            ds['name'] = s.name
            ds['active'] = s.active
            ds['series'] = s
            self[s.name] = ds

        Dbg.leave("UbuntuReleases.__init__")

class Srus(dict):

    # __init__
    #
    def __init__(self, lp, *args):
        Dbg.enter("Srus.__init__")

        dict.__init__(self, args)

        self.lp = lp

        self.ubuntu = lp.distributions['ubuntu']
        self.archive = self.ubuntu.getArchive(name='primary')
        releases = UbuntuReleases(lp)
        for release in releases:
            Dbg.verbose('release: %s\n' % release)
            if not releases[release]['active']: continue

            for published in self.archive.getPublishedSources(pocket='Proposed', status='Published', distro_series=releases[release]['series']):
                pkg = published.source_package_name
                if pkg.startswith('language-pack-') and pkg not in ('language-pack-en', 'language-pack-en-base'): continue
                Dbg.verbose('   pkg: %s\n' % pkg)

                self.setdefault(release, {})[pkg] = self.current_versions(releases[release]['series'], pkg)
                #self[release][pkg]['bugs'] = self.match_srubugs(self[release][pkg]['changesfile'])

        Dbg.leave("Srus.__init__")

    # current_versions
    #
    def current_versions(self, series, pkg):
        Dbg.verbose('Fetching publishing history for %s/%s' % (series.name, pkg))
        history = {'release': '', 'updates': '', 'proposed': ''}
        pubs = self.archive.getPublishedSources(source_name=pkg, exact_match=True, status='Published', distro_series=series)
        for pub in pubs:
            if 'Proposed' in pub.pocket:
                history['changesfile'] = pub.changesFileUrl()
                history['published'] = date_to_string(pub.date_published)
            Dbg.verbose('%s=%s published to %s/%s on %s' % (pkg,
                                                              pub.source_package_version,
                                                              series.name, pub.pocket,
                                                              pub.date_published))
            history[pub.pocket.lower()] = pub.source_package_version
        return history

# vi:set ts=4 sw=4 expandtab:
