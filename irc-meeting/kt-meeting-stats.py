#!/usr/bin/env python

# Generate the weekly bug stats for the Ubuntu Kernel Team IRC meeting.
#
#   bzr branch lp:~canonical-kernel-team/arsenal/kernel kernel_arsenal
#   cp kt-meeting-stats.py kernel_arsenal/contrib/linux/
#   python ./kt-meeting-stats.py
#
# It is assumed this will be run in a cron _once a week_.  The script
# takes approximately 45sec to run.
#
# NOTE: the stats are written to $filename and used as input upon the next
# run of this script.  If you run this more frequently than once a week,
# you'll get incorrect rate of change values for the week.

from launchpadlib.launchpad import Launchpad
from ktl.ubuntu import Ubuntu
from ktl.kernel_series import KernelSeries
from datetime import *
import os
import urllib

#calculate the change in numbers from last week
def calculate_change(stat, key):
    if key in stats.keys() and stat > stats[key]:
        change = "up"
        change_num = stat - stats[key]
    elif key in stats.keys() and stat < stats[key]:
        change = "down"
        change_num = stats[key] - stat
    else:
        change = "no change"
        change_num = 0

    return (change, change_num)

stats = {}

filename = "$HOME/public_html/reports/kt-meeting-stats.txt"
if not os.path.exists(filename):
    urllib.urlretrieve("http://people.canonical.com/~kernel/reports/kt-meeting-stats.txt", filename)

# Import last week's stats
FILE = open(filename, 'r')
for line in FILE:
    line = line.strip()
    key_val = line.split(':')
    key = key_val[0]
    stats[key] = int(key_val[1])
FILE.close()

kernel_series = KernelSeries()
releases = [ series.codename for series in sorted(kernel_series.series, key=KernelSeries.key_series_name, reverse=True) if series.supported ]

#releases = ['oneiric', 'natty', 'maverick', 'lucid', 'hardy']

regressions = ['regression-update', 'regression-release', 'regression-proposed']
output = {'release':'',
          'milestone':'',
          'incoming':'',
          'regression-update':'',
          'regression-release':'',
          'regression-proposed': ''}

cachedir = os.path.expanduser("~/.cache/")
lp = Launchpad.login_anonymously('kernel team tools', 'production', cachedir)
distro = lp.distributions['ubuntu']
linux = distro.getSourcePackage(name='linux')
series = distro.current_series
linux_series = series.getSourcePackage(name='linux')

# Release Metrics (nominated bugs)
# LP:320596 - Series.searchTasks() always returns an empty collection
# Should be fixed in later versions to not require omit_targeted=False
devel_tasks = linux_series.searchTasks(omit_targeted=False)
# LP:274074 Missing total_size on collections returned by named operations
# Should be fixed in later version, so we could do len(tasks)
nominated = devel_tasks._wadl_resource.representation['total_size']
(change, change_num) = calculate_change(nominated, "nominated")
output['release'] += "==== %s nominated bugs ====\n" % (series.name)
output['release'] += " * %d linux kernel bugs (%s %d)\n" % (nominated, change, change_num)

# Release Metrics (Ubuntu <current_milestone> bugs)
size = len(series.active_milestones)
milestone = series.active_milestones[size - 1]
linux_milestone = linux.searchTasks(milestone=milestone)
milestoned = linux_milestone._wadl_resource.representation['total_size']
(change, change_num) = calculate_change(milestoned, "milestoned")
output['release'] += "==== %s bugs ====\n" % (milestone.title)
output['release'] += " * %s linux kernel bugs (%s %d)\n" % (milestoned, change, change_num)

output['milestone'] += "==== <series>-updates bugs ====\n"

for release_name in releases:
    # Release Metrics (<release>-updates bugs)
    milestone_name = "%s-updates" % (release_name)
    milestone = distro.getMilestone(name=milestone_name)
    release = linux.searchTasks(milestone=milestone)
    update_bugs = release._wadl_resource.representation['total_size']
    (change, change_num) = calculate_change(update_bugs, "%s-updates" % (release_name))
    stats[milestone_name] = update_bugs
    output['milestone'] += " * %d %s linux kernel bugs (%s %d)\n" % (update_bugs, release_name, change, change_num)

    # Incoming Bugs
    release_bugs = linux.searchTasks(tags=release_name)
    num_release_bugs = release_bugs._wadl_resource.representation['total_size']
    stat_name = "%s-incoming" % (release_name)
    (change, change_num) = calculate_change(num_release_bugs, stat_name)
    stats[stat_name] = num_release_bugs
    output['incoming'] += " * %d %s bugs (%s %d)\n" % (num_release_bugs, release_name, change, change_num)

    # Regressions
    for regression in regressions:
        regression_bugs = linux.searchTasks(tags=[release_name,regression], tags_combinator="All")
        num_regressions = regression_bugs._wadl_resource.representation['total_size']
        stat_name = "%s-%s" % (release_name, regression)
        (change, change_num) = calculate_change(num_regressions, stat_name)
        stats[stat_name] = num_regressions
        output[regression] += " * %d %s bugs (%s %d)\n" % (num_regressions, release_name, change, change_num)

now = datetime.utcnow()
print "Last Updated: %s\n" % (now)
print "=== Release Metrics ==="
print "[LINK] http://people.canonical.com/~kernel/reports/kt-meeting.txt\n"
print output['release']
print output['milestone']
print "=== Incoming Bugs ==="
print output['incoming']
print "=== Regressions ==="
for regression in regressions:
    print "==== %s bugs ====" % (regression)
    print output[regression]

# Save the meeting stats to use next week
FILE = open(filename, 'w')
for key in stats.keys():
    FILE.write("%s:%s\n" % (key, stats[key]))
FILE.close()
    
# vi:set ts=4 sw=4 expandtab:
