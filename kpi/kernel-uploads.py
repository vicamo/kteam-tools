#! /usr/bin/python

# This script is used to calculate the number of uploads performed
# for a given series.

from launchpadlib.launchpad import Launchpad
from datetime import datetime
import sys

def no_credential():
        print("Can't proceed without Launchpad credential.")
        sys.exit()

def get_published_sources(release_pocket, publishing_status, series, date):
        published_sources = []
        src = archive.getPublishedSources(exact_match=True, source_name="linux", distro_series=series, pocket=release_pocket, status=publishing_status, created_since_date=date)
        for x in src:
            published_sources.append(x.source_package_version)

        return published_sources

def date_to_influx_ts(date):
        epoch = datetime.utcfromtimestamp(0)
        dt = date
        timestamp = int((dt - epoch).total_seconds() * 1000000000.0)
        return timestamp

launchpad = Launchpad.login_with('UCT', 'production', credential_save_failed=no_credential, version='devel')

ubuntu = launchpad.distributions["ubuntu"]
archive = ubuntu.main_archive
series_collection = ubuntu.series_collection
timestamp = date_to_influx_ts(datetime.utcnow())
for series in series_collection:
    if series.active:
        if series.name == "precise":
            continue
        source = archive.getPublishedSources(exact_match=True, source_name="linux", distro_series=series, pocket="Release")[0]

        #Kernel published to -release
        published_release = [source.source_package_version]

        #Kernels published to -updates
        published_updates = get_published_sources("Updates", "Published", series, source.date_published)

        superseded_updates = get_published_sources("Updates", "Superseded", series, source.date_published)

        updates = published_updates + superseded_updates

        #Kernels published to -security
        published_security = get_published_sources("Security", "Published", series, source.date_published)

        superseded_security = get_published_sources("Security", "Superseded", series, source.date_published)

        security = published_security + superseded_security

        #Kernels Deleted from -proposed
        deleted_proposed = get_published_sources("Proposed", "Deleted", series, source.date_published)

        #Kernels deleted from -proposed which never promoted to -updates
        respins = set(updates).symmetric_difference(deleted_proposed)

        total = len(published_release) + len(updates)
        total_with_respins = total + len(respins)

        #Number of weeks since release
        weeks = ((datetime.utcnow() - source.date_published.replace(tzinfo=None)).days/7)

        #Avg weeks/SRU without respinse (ie only kernel which make it all the way out to -updates)
        avg = (float(weeks)/float(total))

        #Avg weeks/SRU including respins
        avg_with_respins = (float(weeks)/float(total_with_respins))

        print "kernel_uploads_by_series_by_package,series=%s,package=linux uploads=%d,respins=%d,security=%d %s" % (series.name, total, len(respins), len(security), timestamp)
        print "kernel_weeks_per_sru_by_series_by_package,series=%s,package=linux weeks_per_sru=%.2f %s" % (series.name, avg, timestamp)
        print "kernel_weeks_per_sru_plus_respins_by_series_by_package,series=%s,package=linux weeks_per_sru_with_respins=%.2f %s" % (series.name, avg_with_respins, timestamp)

# Debugging to check tags in the repo align with published source packages
# import subprocess, os
#        tag = "Ubuntu-" + source.source_package_version
#        version = tag.rsplit('-', 1)[0]
#        repo = os.path.join("~/ubuntu", series.name, "linux")
#        cmd = "cd " + repo + "; " + \
#            "git tag --contains " + tag + " --list " + version + "* --merged " + \
#            "| wc -l"
#        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
#        uploads, err = p.communicate()
#        print "%s total uploads: %s" % (series.name, uploads)
