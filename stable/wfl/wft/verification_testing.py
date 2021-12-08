
import os
import json
from wfl.log                                    import Clog, center, cleave, cdebug, cinfo, cerror
from wfl.errors                                 import ShankError
from .base                                      import TaskHandler
from ktl.sru_report                             import SruReport
from ktl.bug_spam                               import BugSpam


class BugSpamError(ShankError):
    '''
    A class to handle sru-report and bug spamming errors
    '''
    pass


class VerificationTesting(TaskHandler):
    '''
    A Task Handler for the verification-testing task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(VerificationTesting, s).__init__(lp, task, bug)

        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._status_check
        s.jumper['In Progress']   = s._status_check
        s.jumper['Incomplete']    = s._status_check
        s.jumper['Opinion']       = s._status_check
        s.jumper['Fix Committed'] = s._status_check
        s.jumper['Fix Released']  = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    # _sru_report
    #
    def _sru_report(s, series, package):
        try:
            # generate the sru report json
            sru_report_cfg = {}
            sru_report_cfg['series'] = [series]
            sru_report_cfg['pkgs'] = [package]
            sru_report_cfg['archive-versions'] = False
            if Clog.debug:
                sru_report_cfg['debug'] = 'core'
            sru_report = json.loads(SruReport(cfg=sru_report_cfg, lp_service=s.lp.default_service).generate())
        except Exception as e:
            raise BugSpamError('Failed to generate sru-report: %s' % str(e))

        if (series not in sru_report['releases'] or
                package not in sru_report['releases'][series]):
            raise BugSpamError('Failed to generate sru-report: series/package not found')

        return sru_report

    # _spam_bugs
    #
    def _spam_bugs(s, dry_run=False):
        '''
        Get the list of bugs for this release and spam them.
        '''
        center(s.__class__.__name__ + '._spam_bugs')

        s._comment_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       "../../boilerplate/bugtext-start-verification.txt")

        # Grab our list of bugs.
        sru_report = s._sru_report(s.bug.series, s.bug.name)
        sru_bugs = sru_report['releases'][s.bug.series][s.bug.name]['bugs']

        cdebug("SPAM sru_bugs {} {}".format(len(sru_bugs), sru_bugs))

        # If we have a master bug then we ask for its list of bugs and subtract those from ours
        master_bug = s.bug.master_bug
        if master_bug is not None:
            master_report = s._sru_report(master_bug.series, master_bug.name)
            master_bugs = master_report['releases'][master_bug.series][master_bug.name]['bugs']

            if master_bugs is None:
                raise BugSpamError("master-bug has no bugs list yet...")

            cdebug("SPAM master_bugs {} {}".format(len(master_bugs), master_bugs))

            # sru_bugs = sru_bugs - master_bugs
            for bug in master_bugs:
                if bug in sru_bugs:
                    del sru_bugs[bug]

            sru_report['releases'][s.bug.series][s.bug.name]['bugs'] = sru_bugs

        if not dry_run and len(sru_bugs) > 0:
            try:
                bug_spam_cfg = {}
                bug_spam_cfg['series'] = s.bug.series
                bug_spam_cfg['package'] = s.bug.name
                bug_spam_cfg['version'] = s.bug.version
                bug_spam_cfg['sru'] = sru_report
                # the dryrun flag is passed from the swm CLI to the WorkflowBug object
                bug_spam_cfg['dryrun'] = s.bug._dryrun
                if Clog.debug:
                    bug_spam_cfg['debug'] = True

                # load the contents from the comment file
                with open(s._comment_file, 'r') as f:
                    bug_spam_cfg['comment-text'] = f.read()

                # feed the report to the bug spammer
                BugSpam(cfg=bug_spam_cfg, lp_service=s.lp.default_service).spam()
            except Exception as e:
                raise BugSpamError('Failed to spam bugs: %s' % str(e))
            except:
                raise BugSpamError('Failed to spam bugs: unknown error')

        cdebug("SPAM final_bugs {} {}".format(len(sru_bugs), sru_bugs))

        cleave(s.__class__.__name__ + '._spam_bugs')

    # _verification_status
    #
    def _verification_status(self):
        center(self.__class__.__name__ + '._verification_status')

        # Grab a list of our bugs (as found in the changes file).
        sru_bugs = self.bug.debs.bugs
        cdebug("SPAM-V sru_bugs {} {}".format(len(sru_bugs), sru_bugs))

        # If we have a master bug then we ask for its list of bugs and subtract those from ours
        master_bug = self.bug.master_bug
        if master_bug is not None:
            master_bugs = master_bug.debs.bugs
            if master_bugs is None:
                master_bugs = []
            cdebug("SPAM-V master_bugs {} {}".format(len(master_bugs), master_bugs))

            sru_bugs = list(set(sru_bugs) - set(master_bugs))
        cdebug("SPAM-V final_bugs {} {}".format(len(sru_bugs), sru_bugs))

        # See if we have any trackers that need verification.
        human_state = []
        overall = {}
        for bug in sru_bugs:
            try:
                lp_bug = self._lp.default_service.launchpad.bugs[bug]
                rls = self.bug.series

                state = 'missing'
                if   'kernel-tracking-bug'              in lp_bug.tags: state = 'release-tracker'
                elif 'kernel-release-tracker'           in lp_bug.tags: state = 'release-tracker'
                elif 'kernel-release-tracking-bug'      in lp_bug.tags: state = 'release-tracker'
                elif 'kernel-cve-tracker'               in lp_bug.tags: state = 'cve-tracker'
                elif 'kernel-cve-tracking-bug'          in lp_bug.tags: state = 'cve-tracker'
                elif 'kernel-stable-tracking-bug'       in lp_bug.tags: state = 'stable-tracker'
                elif 'kernel-packaging-tracking-bug'    in lp_bug.tags: state = 'packaging-tracker'

                # By making these checks separately and after the previous ones, we
                # can add the correct state for tracking bugs.
                #
                if 'verification-failed-%s' % rls       in lp_bug.tags: state = 'failed'
                elif 'verification-reverted-%s' % rls   in lp_bug.tags: state = 'reverted'
                elif 'verification-done-%s'   % rls     in lp_bug.tags: state = 'verified'
                elif 'verification-needed-%s' % rls     in lp_bug.tags: state = 'needed'
                elif 'verification-done'                in lp_bug.tags: state = 'verified'
            except KeyError:
                state = 'private'

            human_state.append("{}:{}".format(bug, state))

            # Trackers are not individually verified.
            if state.endswith('-tracker'):
                continue

            overall[state] = overall.get(state, 0) + 1

        # Find the most concerning state.
        spam_needed = 'none'
        summary = []
        for state in ('failed', 'needed', 'reverted', 'private', 'verified'):
            if state in overall:
                if spam_needed == 'none':
                    spam_needed = state
                summary.append("{}:{}".format(state, overall[state]))

        cinfo("verification_testing: {}".format(' '.join(summary)))

        cleave(self.__class__.__name__ + '._verification_status retval={}'.format(spam_needed))

        return spam_needed

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False

        while not retval:
            # This test requires the sources to be prepared.
            if s.bug.tasks_by_name['prepare-package'].status != 'Fix Released':
                break

            # And where builds exist for them to be in -proposed.
            if s.bug.debs.routing('Proposed') is not None and not s.bug.debs.ready_for_testing_as_proposed:
                break

            s.task.status = 'Confirmed'
            retval = True
            break

        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    def _status_check_payload(s):
        retval = False

        promote_status = s.bug.task_status('promote-to-updates')
        if promote_status == 'Invalid':
            promote_status = s.bug.task_status('promote-to-release')
        if promote_status == 'Fix Released':
            cinfo('kernels promoted successfully from Proposed', 'green')
            return retval

        present = s.bug.debs.all_built_and_in_pocket_or_after('Proposed')
        if not present:
            if s.task.status not in ('Incomplete', 'Fix Released', "Won't Fix", 'Opinion'):
                cinfo('Kernels no longer present in Proposed moving Aborted (Opinion)', 'yellow')
                s.task.status = 'Opinion'
                retval = True

        elif present and s.task.status == 'Opinion':
            s.task.status = 'New'
            retval = True

        elif 'verification-testing-failed' in s.bug.tags:
            cdebug('Verification Testing tagged as FAILED', 'yellow')
            if s.task.status != 'Incomplete':
                s.task.status = 'Incomplete'
                retval = True

        elif 'verification-testing-passed' in s.bug.tags:
            cdebug('Verification Testing tagged as PASSED', 'yellow')
            if s.task.status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        else:
            # Spam bugs against this package (but not those against our master)
            # if they haven't been spammed already.
            if 'bugs-spammed' not in s.bug.bprops:
                cinfo('            Spamming bugs for verification', 'yellow')
                try:
                    s._spam_bugs()
                    s.bug.bprops['bugs-spammed'] = True
                except BugSpamError as e:
                    cerror('            %s' % str(e))

            # If we have managed to spam the bugs then verification is now in-progress.
            if 'bugs-spammed' in s.bug.bprops:
                if s.task.status == 'Confirmed':
                    s.task.status = 'In Progress'
                    retval = True

            # Work out if the testing is complete.
            status = 'needed'
            try:
                status = s._verification_status()
            except BugSpamError as e:
                cerror('            %s' % str(e))

            task_status = s.task.status
            if status == 'failed' and task_status != 'Incomplete':
                s.task.status = 'Incomplete'
                retval = True

            elif status == 'needed' and task_status != 'In Progress':
                s.task.status = 'In Progress'
                retval = True

            elif status in ('reverted', 'verified', 'none') and task_status != 'Fix Released':
                s.task.status = 'Fix Released'
                retval = True

        return retval

    # _status_check
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._confirmed')

        retval = s._status_check_payload()

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Stalled -s testing FAILED'
        else:
            s.task.reason = 'Ongoing -s testing in progress'

        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
