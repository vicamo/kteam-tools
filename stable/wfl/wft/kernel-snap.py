
from wfl.log                                    import center, cleave
from .base                                      import TaskHandler

class KernelSnapBase(TaskHandler):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(KernelSnapBase, s).__init__(lp, task, bug)

        # The tracking bug should start this task out as 'Confirmed'.
        #
        s.jumper['New']           = s._new
        s.jumper['Confirmed']     = s._common
        s.jumper['Triaged']       = s._common
        s.jumper['In Progress']   = s._common
        s.jumper['Fix Committed'] = s._common

        cleave(s.__class__.__name__ + '.__init__')

    # _new
    #
    def _new(s):
        center(s.__class__.__name__ + '._new')
        retval = False
        cleave(s.__class__.__name__ + '._new (%s)' % (retval))
        return retval

    # _common
    #
    def _common(s):
        '''
        '''
        center(s.__class__.__name__ + '._common')
        retval = False
        cleave(s.__class__.__name__ + '._common (%s)' % (retval))
        return retval


class KernelSnapEdge(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(KernelSnapEdge, s).__init__(lp, task, bug)
        cleave(s.__class__.__name__ + '.__init__')


class KernelSnapBeta(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(KernelSnapBeta, s).__init__(lp, task, bug)
        cleave(s.__class__.__name__ + '.__init__')


class KernelSnapCandidate(KernelSnapBase):
    '''
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(KernelSnapCandidate, s).__init__(lp, task, bug)
        cleave(s.__class__.__name__ + '.__init__')

class KernelSnapStable(KernelSnapBase):
    '''
    A Task Handler for the prepare-package-lbm task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(KernelSnapStable, s).__init__(lp, task, bug)
        cleave(s.__class__.__name__ + '.__init__')

# vi: set ts=4 sw=4 expandtab syntax=python
