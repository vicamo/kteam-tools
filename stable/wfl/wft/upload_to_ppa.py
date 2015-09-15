
from wfl.log                                    import center, cleave
from .base                                      import TaskHandler

class UploadToPPA(TaskHandler):
    '''
    A Task Handler for the upload-to-ppa task.
    '''

    # __init__
    #
    def __init__(s, lp, task, bug):
        center(s.__class__.__name__ + '.__init__')
        super(UploadToPPA, s).__init__(lp, task, bug)

        s.jumper['Confirmed']    = s._confirmed

        cleave(s.__class__.__name__ + '.__init__')

    # _confirmed
    #
    def _confirmed(s):
        center(s.__class__.__name__ + '._confirmed')
        retval = True
        s.bug.phase = 'ReadyToBePackaged'
        cleave(s.__class__.__name__ + '._confirmed (%s)' % retval)
        return retval

# vi: set ts=4 sw=4 expandtab syntax=python
