from wfl.log                                    import center, cleave

class TaskHandler(object):
    '''
    Base class for all TaskHandlers.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        s.__cn__ = 'TaskHandler'
        center(s.__cn__ + '.__init__')
        s._lp = lp
        s._task = task
        s._bug = bug

        s.jumper = {}
        s.jumper['New']           = s._new
        s.jumper['Incomplete']    = s._incomplete
        s.jumper['Opinion']       = s._opinion
        s.jumper['Invalid']       = s._invalid
        s.jumper['Won\'t Fix']    = s._wont_fix
        s.jumper['Expired']       = s._expired
        s.jumper['Confirmed']     = s._confirmed
        s.jumper['Triaged']       = s._triaged
        s.jumper['In Progress']   = s._in_progress
        s.jumper['Fix Committed'] = s._fix_committed
        s.jumper['Fix Released']  = s._fix_released
        s.jumper['Unknown']       = s._unknown

        cleave(s.__cn__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__cn__ + '._new')
        retval = False
        cleave(s.__cn__ + '._new (%s)' % retval)
        return retval

    # _incomplete
    #
    def _incomplete(s):
        center(s.__cn__ + '._incomplete')
        retval = False
        cleave(s.__cn__ + '._incomplete (%s)' % retval)
        return retval

    # _opinion
    #
    def _opinion(s):
        center(s.__cn__ + '._opinion')
        retval = False
        cleave(s.__cn__ + '._opinion (%s)' % retval)
        return retval

    # _invalid
    #
    def _invalid(s):
        center(s.__cn__ + '._invalid')
        retval = False
        cleave(s.__cn__ + '._invalid (%s)' % retval)
        return retval

    # _wont_fix
    #
    def _wont_fix(s):
        center(s.__cn__ + '._wont_fix')
        retval = False
        cleave(s.__cn__ + '._wont_fix (%s)' % retval)
        return retval

    # _expired
    #
    def _expired(s):
        center(s.__cn__ + '._expired')
        retval = False
        cleave(s.__cn__ + '._expired (%s)' % retval)
        return retval

    # _confirmed
    #
    def _confirmed(s):
        center(s.__cn__ + '._confirmed')
        retval = False
        cleave(s.__cn__ + '._confirmed (%s)' % retval)
        return retval

    # _triaged
    #
    def _triaged(s):
        center(s.__cn__ + '._triaged')
        retval = False
        cleave(s.__cn__ + '._triaged (%s)' % retval)
        return retval

    # _in_progress
    #
    def _in_progress(s):
        center(s.__cn__ + '._im_progress')
        retval = False
        cleave(s.__cn__ + '._im_progress (%s)' % retval)
        return retval

    # _fix_committed
    #
    def _fix_committed(s):
        center(s.__cn__ + '._fix_committed')
        retval = False
        cleave(s.__cn__ + '._fix_committed (%s)' % retval)
        return retval

    # _fix_released
    #
    def _fix_released(s):
        center(s.__cn__ + '._fix_released')
        retval = False
        cleave(s.__cn__ + '._fix_released (%s)' % retval)
        return retval

    # _unknown
    #
    def _unknown(s):
        center(s.__cn__ + '._unknown')
        retval = False
        cleave(s.__cn__ + '._unknown (%s)' % retval)
        return retval

    @property
    def lp(s):
        return s._lp

    @property
    def task(s):
        return s._task

    @property
    def bug(s):
        return s._bug
# vi: set ts=4 sw=4 expandtab syntax=python
