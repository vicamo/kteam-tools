
import os
import json
from wfl.log                                    import Clog, center, cleave, cdebug, cinfo, cerror, centerleave
from wfl.context                                import ctx
from wfl.errors                                 import ShankError

from .base                                      import TaskHandler


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

    # _spam_bug
    #
    @centerleave
    def _spam_bug(self, lp_bug, dry_run=False):
        spammed_v1 = 'kernel-spammed-{}-{}'.format(self.bug.series, self.bug.name)
        spammed_v2 = spammed_v1 + "-v2"
        if spammed_v1 in lp_bug.tags or spammed_v2 in lp_bug.tags:
            return

        # We are going to comment, load and fill in the template.
        comment_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../../boilerplate/bugtext-start-verification.txt",
        )
        with open(comment_file) as cfd:
            comment_text = "\n".join(cfd.readlines())
        comment_text = (
            comment_text.replace("_SERIES_", self.bug.series)
            .replace("_PACKAGE_", self.bug.name)
            .replace("_VERSION_", self.bug.version)
        )
        cinfo("_spam_bug: comment_text={}".format(comment_text))
        if not dry_run:
            lp_bug.newMessage(content=comment_text)

        by_package = self.bug.series + "-" + self.bug.name
        tags = set(lp_bug.tags)
        for tag in (
            'verification-failed-' + by_package,
            'verification-reverted-' + by_package,
            'verification-needed-' + by_package,
            'verification-done-' + by_package,
            'verification-done',
        ):
            if tag in tags:
                cinfo('_spam_bug: removing tag {}'.format(tag))
                tags.remove(tag)
        for tag in (
            'verification-needed-' + by_package,
            'kernel-spammed-{}-{}-v2'.format(self.bug.series, self.bug.name)
        ):
            cinfo('_spam_bug: adding tag {}'.format(tag))
            tags.add(tag)

        # Write the tags back if they are changed.
        if set(lp_bug.tags) != tags:
            cinfo('_spam_bug: tags changed writing back')
            if not dry_run:
                lp_bug.tags = list(tags)
                lp_bug.lp_save()

    # _verification_status
    #
    def _verification_status(self):
        center(self.__class__.__name__ + '._verification_status')

        # Grab a list of our bugs (as found in the changes file).
        sru_bugs = self.bug.debs.bugs
        if sru_bugs is None:
            spam_needed = "needed"
            cleave(self.__class__.__name__ + '._verification_status retval={}'.format(spam_needed))
            return spam_needed
        cdebug("SPAM-V sru_bugs {} {}".format(len(sru_bugs), sru_bugs))

        # If we have a parent tracker then we ask for its list of bugs and subtract those from ours
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
            spam = False
            try:
                lp_bug = self.lp.bugs[bug]
                spammed_v1 = 'kernel-spammed-{}-{}'.format(self.bug.series, self.bug.name)
                spammed_v2 = spammed_v1 + "-v2"
                if spammed_v1 in lp_bug.tags:
                    key = self.bug.series
                else:
                    key = self.bug.series + "-" + self.bug.name

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
                if 'verification-failed-%s' % key       in lp_bug.tags: state = 'failed'
                elif 'verification-reverted-%s' % key   in lp_bug.tags: state = 'reverted'
                elif 'verification-done-%s'   % key     in lp_bug.tags: state = 'verified'
                elif 'verification-needed-%s' % key     in lp_bug.tags: state = 'needed'
                #elif 'verification-done'                in lp_bug.tags: state = 'verified'

                if spammed_v1 not in lp_bug.tags and spammed_v2 not in lp_bug.tags:
                    spam = True

            except KeyError:
                state = 'private'

            human_state.append("{}:{}".format(bug, state))

            # Trackers are not individually verified.
            if state.endswith('-tracker'):
                continue

            if spam:
                self._spam_bug(lp_bug)

            overall[state] = overall.get(state, 0) + 1

        # Find the most concerning state.
        spam_needed = 'none'
        summary = []
        for state in ('missing', 'failed', 'needed', 'reverted', 'private', 'verified'):
            if state in overall:
                if spam_needed == 'none':
                    spam_needed = state
                summary.append("{}:{}".format(state, overall[state]))

        cdebug("verification_testing: detail {}".format(' '.join(human_state)))
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
            # Work out if the testing is complete.
            status = 'needed'
            try:
                status = s._verification_status()
                s.bug.flag_assign('bugs-spammed', True)

            except BugSpamError as e:
                cerror('            %s' % str(e))

            task_status = s.task.status
            if status == 'failed' and task_status != 'Incomplete':
                s.task.status = 'Incomplete'
                retval = True

            elif status == 'needed' and s.bug.flag('bugs-spammed') and task_status != 'In Progress':
                s.task.status = 'In Progress'
                retval = True

            elif status == 'needed' and not s.bug.flag('bugs-spammed') and task_status != 'Confirmed':
                s.task.status = 'Confirmed'
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
