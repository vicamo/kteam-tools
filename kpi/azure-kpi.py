from pprint import pprint
import urllib2, re, datetime
from datetime import datetime
from launchpadlib.launchpad import Launchpad

def no_credential():
        print("Can't proceed without Launchpad credential.")
        sys.exit()

launchpad = Launchpad.login_with('UCT', 'production', credential_save_failed=no_credential, version='devel')
date_format = "%Y-%m-%d"
total_bugs = 0
total_days = 0
days_per_bug = []
ubuntu = launchpad.distributions["ubuntu"]
archive = ubuntu.main_archive
series = ubuntu.getSeries(name_or_version="xenial")
output = ""
print ("| Release | Date Published to -proposed | Total # Bugs | Avg Days to Publish Per Bug |")
for x in archive.getPublishedSources(exact_match=True,source_name="linux-azure",distro_series=series,pocket="Proposed"):
#    print ("=== %s Published %s ===" % (x.source_package_version, "{:%Y-%m-%d}".format(x.date_published)))
    file = urllib2.urlopen(x.changesFileUrl())
    for line in file:
        if "Launchpad-Bugs-Fixed" in line:
            for bug_num in re.findall('\d+', line):
                lpbug = launchpad.bugs[bug_num]
                for bug_task in lpbug.bug_tasks_collection:
                    if "linux-azure" in bug_task.bug_target_name:

#                        print("LP%s: %s" % (bug_num, lpbug.title))
#                        print("Bug Created: %s" % ("{:%Y-%m-%d}".format(lpbug.date_created)))
#                        print("linux-azure Created: %s" % ("{:%Y-%m-%d}".format(bug_task.date_created)))
                        date_created = datetime.strptime("{:%Y-%m-%d}".format(bug_task.date_created), date_format)
                        date_closed = datetime.strptime("{:%Y-%m-%d}".format(x.date_published), date_format)
                        days = date_closed - date_created
                        days_per_bug.append(float(days.days))
                        total_days += float(days.days)
#                        print ("Days to close: %s" % days_per_bug[-1])
                        total_bugs += 1
#                        print("Created %s | Open %s days" % (("{:%Y-%m-%d}".format(bug_task.date_created)), days_per_bug[-1]))
                        break

#    print "-------------------------------"
#    print ("Total # bugs: %d" % len(days_per_bug))
#    print ("Total days: %s" % sum(days_per_bug))
#    print ("Avg days to publish: %s" % (sum(days_per_bug) / len(days_per_bug)))
    print ("%s %s %d %s" % (x.source_package_version,"{:%Y-%m-%d}".format(x.date_published), len(days_per_bug), (sum(days_per_bug) / len(days_per_bug))))
    days_per_bug = []
#    print ("__________________________________________")

print ("Total Days: %s" % total_days)
print ("Total Bugs: %s" % total_bugs)
print ("Avg Days/Bug: %s" % (total_days/total_bugs))
