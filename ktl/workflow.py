#!/usr/bin/env python
#

# UbuntuError
#
class UbuntuError(Exception):
    # __init__
    #
    def __init__(self, error):
        self.msg = error

# Workflow
#
class Workflow:

    # Tasks, tags, etc vary according to the package name
    tdb = {
        'linux' :  {
            'task_assignment' : {
                'prepare-package'            : 'canonical-kernel-team',
                'prepare-package-lbm'        : 'canonical-kernel-team',
                'prepare-package-lrm'        : 'canonical-kernel-team',
                'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                'prepare-package-ports-meta' : 'canonical-kernel-team',
                #'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'canonical-kernel-team',
                'certification-testing'      : 'canonical-hw-cert',
                'regression-testing'         : 'canonical-platform-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru", "hardware-certification"],
            'invalidate_tasks' : {
                'certification-testing' : [ '2.6.24' ]
                }
            },
        'linux-ec2' :  {
            'task_assignment' : {
                'prepare-package'            : 'stefan-bader-canonical',
                #'prepare-package-lbm'        : 'canonical-kernel-team',
                #'prepare-package-lrm'        : 'canonical-kernel-team',
                #'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                #'prepare-package-ports-meta' : 'canonical-kernel-team',
                'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'canonical-kernel-team',
                'certification-testing'      : 'canonical-hw-cert',
                'regression-testing'         : 'canonical-platform-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru", "hardware-certification"]
            },
        'linux-mvl-dove' :  {
            'task_assignment' : {
                'prepare-package'            : 'ubuntu-armel-kernel',
                #'prepare-package-lbm'        : 'canonical-kernel-team',
                #'prepare-package-lrm'        : 'canonical-kernel-team',
                #'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                #'prepare-package-ports-meta' : 'canonical-kernel-team',
                'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'ubuntu-armel-kernel',
                #'certification-testing    ' : 'ubuntu-armel-qa',
                'regression-testing'         : 'ubuntu-armel-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug', 'armel'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru", "ubuntu-armel-qa"]
            },
        'linux-fsl-imx51' :  {
            'task_assignment' : {
                'prepare-package'            : 'ubuntu-armel-kernel',
                #'prepare-package-lbm'        : 'canonical-kernel-team',
                #'prepare-package-lrm'        : 'canonical-kernel-team',
                #'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                #'prepare-package-ports-meta' : 'canonical-kernel-team',
                'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'ubuntu-armel-kernel',
                #'certification-testing'     : 'ubuntu-armel-qa',
                'regression-testing'         : 'ubuntu-armel-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug', 'armel'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru", "ubuntu-armel-qa"]
            },
        'linux-ti-omap4' :  {
            'task_assignment' : {
                'prepare-package'            : 'ubuntu-armel-kernel',
                #'prepare-package-lbm'        : 'canonical-kernel-team',
                #'prepare-package-lrm'        : 'canonical-kernel-team',
                #'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                #'prepare-package-ports-meta' : 'canonical-kernel-team',
                'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'ubuntu-armel-kernel',
                #'certification-testing'     : 'ubuntu-armel-qa',
                'regression-testing'         : 'ubuntu-armel-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug', 'armel'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru", "ubuntu-armel-qa"]
            },
        'linux-lts-backport-oneiric' :  {
            'task_assignment' : {
                'prepare-package'            : 'canonical-kernel-team',
                #'prepare-package-lbm'        : 'canonical-kernel-team',
                #'prepare-package-lrm'        : 'canonical-kernel-team',
                #'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                #'prepare-package-ports-meta' : 'canonical-kernel-team',
                #'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'canonical-kernel-team',
                #'certification-testing'     : 'canonical-hw-cert',
                'regression-testing'         : 'canonical-platform-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru"],
            },
        'linux-lts-backport-natty' :  {
            'task_assignment' : {
                'prepare-package'            : 'canonical-kernel-team',
                #'prepare-package-lbm'        : 'canonical-kernel-team',
                #'prepare-package-lrm'        : 'canonical-kernel-team',
                #'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                #'prepare-package-ports-meta' : 'canonical-kernel-team',
                #'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'canonical-kernel-team',
                #'certification-testing'     : 'canonical-hw-cert',
                'regression-testing'         : 'canonical-platform-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru"],
            },
        'linux-lts-backport-maverick' :  {
            'task_assignment' : {
                'prepare-package'            : 'canonical-kernel-team',
                #'prepare-package-lbm'        : 'canonical-kernel-team',
                #'prepare-package-lrm'        : 'canonical-kernel-team',
                #'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                #'prepare-package-ports-meta' : 'canonical-kernel-team',
                #'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'canonical-kernel-team',
                #'certification-testing'     : 'canonical-hw-cert',
                'regression-testing'         : 'canonical-platform-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru"],
            },
        'default' :  {
            'task_assignment' : {
                'prepare-package'            : 'canonical-kernel-team',
                'prepare-package-lbm'        : 'canonical-kernel-team',
                'prepare-package-lrm'        : 'canonical-kernel-team',
                'prepare-package-lum'        : 'canonical-kernel-team',
                'prepare-package-meta'       : 'canonical-kernel-team',
                'prepare-package-ports-meta' : 'canonical-kernel-team',
                #'upload-to-ppa'              : 'canonical-kernel-team',
                'promote-to-proposed'        : 'ubuntu-sru',
                'verification-testing'       : 'canonical-kernel-team',
                'certification-testing'      : 'canonical-hw-cert',
                'regression-testing'         : 'canonical-platform-qa',
                'promote-to-updates'         : 'ubuntu-sru',
                'promote-to-security'        : 'ubuntu-sru',
                'security-signoff'           : 'canonical-security'
                },
            'initial_bug_tags' :
                ['kernel-release-tracking-bug'],
            'subscribers' :
                ["sru-verification", "ubuntu-sru", "hardware-certification"]
            }
        }

    # assignee
    #
    def assignee(self, packagename, taskname):
        """
        Using the given package name and task name, return the launchpad
        team or person who should be assigned that task. If the
        package name is not in the dictionary, return the default
        """
        if packagename in self.tdb:
            if taskname in self.tdb[packagename]['task_assignment']:
                return self.tdb[packagename]['task_assignment'][taskname]
            else:
                return None
        else:
                return self.tdb['default']['task_assignment'][taskname]

    # initial_tags
    #
    def initial_tags(self, packagename):
        """
        Lookup the given package name and return the tags which
        should be initially applied to the tracking bug
        """
        if packagename in self.tdb:
                return self.tdb[packagename]['initial_bug_tags']
        else:
                return self.tdb['default']['initial_bug_tags']

    # subscribers
    #
    def subscribers(self, packagename):
        """
        Lookup the given package name and return a list of
        teams who should be initially subscribed to the tracking bug
        """
        if packagename in self.tdb:
                return self.tdb[packagename]['subscribers']
        else:
                return self.tdb['default']['subscribers']

    # is task invalid for that series version
    #
    def is_task_invalid(self, packagename, taskname, version):
        """
        Return if the task is invalid for that package version
        """
        if not packagename in self.tdb:
            return False
        if not 'invalidate_tasks' in self.tdb[packagename]:
            return False
        if not taskname in self.tdb[packagename]['invalidate_tasks']:
            return False
        version_list = self.tdb[packagename]['invalidate_tasks'][taskname]
        return (version in version_list)

    # series where that package version is found
    #
    def expected_series_name(self, db, package, version):
        """
        Return the series name where that package-version is found
        """
        if (package == 'linux' or
            package == 'linux-ti-omap4' or
            package == 'linux-ec2'):
            for entry in db.itervalues():
                if version.startswith(entry['kernel']):
                    return entry['name']
        if package.startswith('linux-lts-backport'):
            for entry in db.itervalues():
                if entry['name'] in version:
                    return entry['name']
        if package == 'linux-mvl-dove' or package == 'linux-fsl-imx51':
            version, release = version.split('-')
            if release:
                abi, upload = release.split('.')
                try:
                    abi_n = int(abi)
                except ValueError:
                    abi_n = 0
                if abi_n:
                    if package == 'linux-mvl-dove':
                        if abi_n < 400:
                            return 'lucid'
                        else:
                            return 'maverick'
                    if package == 'linux-fsl-imx51':
                        if abi_n < 600:
                            return 'karmic'
                        else:
                            return 'lucid'
        return None

if __name__ == '__main__':
    workflow = Workflow()
    db = workflow.tdb

    #for record in db:
    #    print db[record]

    print(workflow.assignee('linux', 'prepare-package'))
    print(workflow.assignee('linux', 'nonexistent-task'))
    print(workflow.initial_tags('linux-ti-omap4'))
    print(workflow.subscribers('linux-ti-omap4'))

# vi:set ts=4 sw=4 expandtab:
