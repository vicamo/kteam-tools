
from wfl.log                                    import center, cleave
from .base                                      import TaskHandler

class SecuritySignoff(TaskHandler):
    '''
    A Task Handler for the security-signoff task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(SecuritySignoff, s).__init__(lp, task, bug)

        # s.jumper['Invalid']      = s._fix_released    # FIXME bjf - invalid means _invalid_ and nothing should be done when in
                                                        #             this state.
        s.jumper['Fix Released'] = s._fix_released

        cleave(s.__class__.__name__ + '.__init__')

    # _fix_released
    #
    def _fix_released(s):
        """
        When security-signoff is set to either Invalid or Fix Released, it is done.
        If set to Fix Released, we set a flag to indicate that the package must
        be copied to the -security pocket.
        """
        center(s.__class__.__name__ + '._fix_released')
        retval = True
        s.security_signoff_complete = True
        s.bug.set_tagged_timestamp('kernel-stable-Security-signoff-end')
        cleave(s.__class__.__name__ + '._fix_released (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
