
import os
import json
from wfl.log                                    import Clog, center, cleave, cinfo, cerror
from wfl.errors                                 import ShankError
from .base                                      import TaskHandler
from ktl.sru_report                             import SruReport
from ktl.bug_spam                               import BugSpam


class BugSpamError(ShankError):
    '''
    A class to handle sru-report and bug spamming errors
    '''
    def __init__(s, emsg):
        super().__init__(emsg)

    def __str__(s):
        return s.message


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
        s.jumper['Fix Committed'] = s._status_check

        cleave(s.__class__.__name__ + '.__init__')

    # _spam_bugs
    #
    def _spam_bugs(s):
        '''
        Get the list of bugs for this release and spam them.
        '''
        center(s.__class__.__name__ + '._spam_bugs')

        s._comment_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       "../../boilerplate/bugtext-start-verification.txt")

        try:
            # generate the sru report json
            sru_report_cfg = {}
            sru_report_cfg['series'] = [s.bug.series]
            sru_report_cfg['pkgs'] = [s.bug.pkg_name]
            sru_report_cfg['archive-versions'] = False
            if Clog.debug:
                sru_report_cfg['debug'] = 'core'
            sru_report = SruReport(cfg=sru_report_cfg, lp_service=s.lp.default_service).generate()
        except Exception as e:
            raise BugSpamError('Failed to generate sru-report: %s' % str(e))
        except:
            raise BugSpamError('Failed to generate sru-report: unknown error')

        try:
            bug_spam_cfg = {}
            bug_spam_cfg['series'] = s.bug.series
            bug_spam_cfg['package'] = s.bug.pkg_name
            bug_spam_cfg['sru'] = json.loads(sru_report)
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

        cleave(s.__class__.__name__ + '._spam_bugs')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False
        if s.bug.ready_for_testing:
            s.task.status = 'Confirmed'
            retval = True
        cleave(s.__class__.__name__ + '._new (%s)' % retval)
        return retval

    # _confirmed
    #
    def _status_check(s):
        center(s.__class__.__name__ + '._confirmed')
        retval = False
        if s.bug.is_derivative_package:
            master = s.bug.master_bug
            try:
                if s.task.status != master.tasks_by_name['verification-testing'].status:
                    if 'New' != master.tasks_by_name['verification-testing'].status:
                        s.task.status = master.tasks_by_name['verification-testing'].status
                        retval = True
            except KeyError:
                cinfo('            master bug does not contain a verification-testing task', 'yellow')
        else:
            # Spam bugs from the main package if they haven't been spammed already
            if 'bugs-spammed' not in s.bug.bprops:
                cinfo('            Spamming bugs for verification', 'yellow')
                try:
                    s._spam_bugs()
                    s.bug.bprops['bugs-spammed'] = True
                except BugSpamError as e:
                    cerror('            %s' % str(e))

        if s.task.status == 'Fix Released':
            pass
        elif s.task.status == 'Incomplete':
            s.task.reason = 'Testing FAILED'
        else:
            s.task.reason = 'Testing in progress'

        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
