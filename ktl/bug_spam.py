import sys
import os

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'py3')))

from lpltk.LaunchpadService             import LaunchpadService
from logging                            import basicConfig, DEBUG, INFO
from ktl.log                            import cinfo, cwarn


class BugSpam:
    # __init__
    #
    def __init__(self, cfg):
        self.cfg = cfg
        self.service = LaunchpadService(self.cfg)

        log_format = "%(levelname)s - %(message)s"
        if 'verbose' in self.cfg:
            basicConfig(level=INFO, format=log_format)
        elif 'debug' in self.cfg:
            basicConfig(level=DEBUG, format=log_format)

    def verbose(self, msg):
        cinfo("BugSpam: %s" % msg)

    # modify_bug_status
    #
    # Change the bugs status.
    #
    def modify_bug_status(self, bug):
        tasks = bug.tasks
        if len(tasks) == 1:
            self.verbose('        . changing status to: %s' % (self.cfg['status']))
            # task = tasks[0]
            # tasks[0].status = self.cfg['status']
        else:
            cwarn("   ** Warning: This bug contains multiple bug tasks, not able to set the status.")

    def print_bug_info(self, bug_id, bug):
        bug_link = 'https://bugs.launchpad.net/bugs/%s' % bug_id
        self.verbose("%s    %40s    %s" % (bug_id, bug_link, bug.title))

    # spam
    #
    def spam(self):
        try:
            # Find the bugs in the specified release and package that need spamming.
            #
            series = self.cfg['series']
            package = self.cfg['package']
            try:
                self.cfg['sru']['releases'][series][package]
            except:
                cwarn("E: %s/%s: no such series/package" % (series, package))
                return
            try:
                bugs = self.cfg['sru']['releases'][series][package]['bugs']
            except:
                self.verbose("  . %s/%s has no SRU bugs" % (series, package))
                return
            self.verbose("%s/%s:" % (series, package))

            for bug_id in bugs:
                bug = self.service.get_bug(bug_id)
                self.print_bug_info(bug_id, bug)
                should_be_spammed = False
                is_tracker_bug = True

                # RULE: Do not add verification tags or comments to bugs that exist
                #       as "tracking" bugs.
                #
                while (True):
                    if 'kernel-cve-tracker' in bug.tags:
                        self.verbose('    . has kernel-cve-tracker tag')
                        break  # This is a bug used to track a CVE patch

                    if 'kernel-cve-tracking-bug' in bug.tags:
                        self.verbose('    . has kernel-cve-tracking-bug tag')
                        break  # This is a bug used to track a CVE patch

                    if 'kernel-release-tracker' in bug.tags:
                        self.verbose('    . has kernel-release-tracker tag')
                        break  # This is a bug used to track the status of a particular release

                    if 'kernel-release-tracking-bug' in bug.tags:
                        self.verbose('    . has kernel-release-tracking-bug tag')
                        break  # This is a bug used to track the status of a particular release

                    if 'kernel-tracking-bug' in bug.tags:
                        self.verbose('    . has kernel-tracking-bug tag')
                        break  # Old tag that was previously used for this.

                    if 'kernel-stable-tracking-bug' in bug.tags:
                        self.verbose('    . has kernel-stable-tracking-bug tag')
                        break  # Old tag that was previously used for this.

                    self.verbose('    . no tracking tags')
                    is_tracker_bug = False
                    break

                # RULE: If a bug already has the appropriate verification tags on
                #       it, we don't add them again.
                #
                while (not is_tracker_bug):
                    if 'verification-failed-%s' % self.cfg['series'] in bug.tags:
                        self.verbose('    . has verification-failed-%s tag' % self.cfg['series'])
                        break  # The tag exists

                    if 'verification-reverted-%s' % self.cfg['series'] in bug.tags:
                        self.verbose('    . has verification-reverted-%s tag' % self.cfg['series'])
                        break  # The tag exists

                    if 'verification-needed-%s' % self.cfg['series'] in bug.tags:
                        self.verbose('    . has verification-needed-%s tag' % self.cfg['series'])
                        break  # The tag exists

                    if 'verification-done-%s' % self.cfg['series'] in bug.tags:
                        self.verbose('    . has verification-done-%s tag' % self.cfg['series'])
                        break  # The tag exists

                    # None of the tags that we are checking for exist, lets hook em up.
                    #
                    self.verbose('    . no verification tags')
                    should_be_spammed = True
                    break

                if should_be_spammed:
                    self.verbose('    . should be spammed')

                    # Tags
                    #
                    self.verbose('        . adding tag: verification-needed-%s' % (self.cfg['series']))
                    if not self.cfg['dryrun']:
                        bug.tags.append('verification-needed-%s' % self.cfg['series'])

                    # Comment
                    #
                    if 'comment-text' in self.cfg:
                        self.verbose('        . adding comment')
                        if not self.cfg['dryrun']:
                            bug.add_comment(self.cfg['comment-text'].replace('_SERIES_', self.cfg['series']))

                    # Status
                    #
                    if 'status' in self.cfg:
                        tasks = bug.tasks
                        if len(tasks) == 1:
                            self.verbose('        . changing status to: %s' % (self.cfg['status']))
                            if not self.cfg['dryrun']:
                                tasks[0].status = self.cfg['status']
                        else:
                            cwarn("   ** Warning: This bug contains multiple bug tasks, not able to set the status.")

        # Handle the user presses <ctrl-C>.
        #
        except KeyboardInterrupt:
            pass

        return
