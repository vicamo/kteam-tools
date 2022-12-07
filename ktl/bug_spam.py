import sys
import os

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'py3')))

from lpltk.LaunchpadService             import LaunchpadService
from logging                            import basicConfig, DEBUG, INFO
from ktl.log                            import cwarn, cdebug


class BugSpam:
    # __init__
    #
    def __init__(self, cfg, lp_service=None, lp=None):
        self.cfg = cfg

        if lp is not None:
            self.lp = lp

        elif lp_service is not None:
            self.lp = lp_service.default_service.launchpad

        else:
            self.lp_service = LaunchpadService(self.cfg).default_service.launchpad

        log_format = "%(levelname)s - %(message)s"
        if 'debug' in self.cfg or 'verbose' in self.cfg:
            basicConfig(level=DEBUG, format=log_format)

    def verbose(self, msg):
        cdebug("BugSpam: %s" % msg)

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
                bug = self.lp.bugs[bug_id]
                self.print_bug_info(bug_id, bug)
                should_be_spammed = True
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

                    if 'kernel-packaging-tracking-bug' in bug.tags:
                        self.verbose('    . has kernel-packaging-tracking-bug tag')
                        break

                    self.verbose('    . no tracking tags')
                    is_tracker_bug = False
                    break

                if is_tracker_bug:
                    should_be_spammed = False

                    # TRANSITION: fix up errant tagging of non-spammable bugs.
                    series = self.cfg['series']
                    tags = set(bug.tags)
                    for tag in (
                        'verification-failed-' + series,
                        'verification-reverted-' + series,
                        'verification-needed-' + series,
                        'verification-done-' + series,
                        'verification-done',
                    ):
                        if tag in tags:
                            self.verbose('    . has {} tag removing'.format(tag))
                            tags.remove(tag)

                    # Write the tags back if they are changed.
                    if set(bug.tags) != tags:
                        bug.tags = list(tags)
                        bug.lp_save()

                if 'kernel-spammed-%s-%s' % (self.cfg['series'], self.cfg['package']) in bug.tags:
                    self.verbose('    . already spammed for this package')
                    should_be_spammed = False

                # Now that we are limiting spamming to those bugs which are unique to a kernel
                # we can and should remove any old verification tags as we go.
                if should_be_spammed:
                    self.verbose('    . should be spammed')

                    # Comment
                    #
                    if 'comment-text' in self.cfg:
                        self.verbose('        . adding comment')
                        if not self.cfg['dryrun']:
                            bug.newMessage(content=self.cfg['comment-text'].replace('_SERIES_', self.cfg['series']).replace('_PACKAGE_', self.cfg['package']).replace('_VERSION_', self.cfg['version']))

                    series = self.cfg['series']
                    tags = set(bug.tags)
                    for tag in (
                        'verification-failed-' + series,
                        'verification-reverted-' + series,
                        'verification-needed-' + series,
                        'verification-done-' + series,
                        'verification-done',
                    ):
                        if tag in tags:
                            self.verbose('    . has {} tag removing'.format(tag))
                            tags.remove(tag)

                    # Tags
                    #
                    for tag in ('verification-needed-' + series, 'kernel-spammed-%s-%s' % (self.cfg['series'], self.cfg['package'])):
                        self.verbose('        . adding tag: ' + tag)
                        if not self.cfg['dryrun']:
                            tags.add(tag)

                    # Write the tags back if they are changed.
                    if set(bug.tags) != tags:
                        bug.tags = list(tags)
                        bug.lp_save()

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
