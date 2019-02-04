
from wfl.log                                    import center, cleave
from .base                                      import TaskHandler

class Ignore(TaskHandler):
    pass

class IgnoreInvalid(TaskHandler):
    '''
    A Task Handler for the tasks we which to make invalid.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super().__init__(lp, task, bug)

        s.jumper['New']           = s._invalid
        s.jumper['Confirmed']     = s._invalid
        s.jumper['Triaged']       = s._invalid
        s.jumper['In Progress']   = s._invalid
        s.jumper['Incomplete']    = s._invalid
        s.jumper['Fix Committed'] = s._invalid

        cleave(s.__class__.__name__ + '.__init__')

    # _invalid
    #
    def _invalid(s):
        center(s.__class__.__name__ + '._invalid')
        retval = False

        if s.task.status != 'Invalid':
            retval = True
            s.task.status = 'Invalid'

        cleave(s.__class__.__name__ + '._invalid (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
