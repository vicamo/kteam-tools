# ShankError
#
class ShankError(Exception):
    '''
    Base class for exceptions in this module.
    '''
    def __init__(s, emsg):
        s.message = emsg

    def __str__(s):
        return s.message

# ShankConfigFileMissing
#
class ShankConfigFileMissing(ShankError):
    '''
    '''
    # __init__
    #
    def __init__(s):
        super(ShankConfigFileMissing, s).__init__('Unable to find the file (~/.shank). This file is required for the SRU Workflow Manager to operate correctly.')


# GeneralError
#
class GeneralError(Exception):
    '''
    '''
    def __init__(s, emsg):
        s.message = emsg

    def __str__(s):
        return s.message


# ErrorExit
#
class ErrorExit(ShankError):
    '''
    If an error message has already been displayed and we want to just exit the app, this
    exception is raised.
    '''
    pass


class WorkflowCrankError(ShankError):
    pass

class WorkflowCorruptError(ShankError):
    pass
