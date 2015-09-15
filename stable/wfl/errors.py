# ShankError
#
class ShankError(Exception):
    '''
    Base class for exceptions in this module.
    '''
    def __init__(s, emsg):
        s.message = emsg

    def __str__(s):
        return s.__message


# ShankConfigFileMissing
#
class ShankConfigFileMissing(ShankError):
    '''
    '''
    # __init__
    #
    def __init__(s):
        super(ShankError, s).__init__('Unable to find the file (~/.shank). This file is required for the SRU Workflow Manager to operate correctly.')

    def __str__(s):
        return s.message

# GeneralError
#
class GeneralError(Exception):
    '''
    '''
    def __init__(s, emsg):
        s.message = emsg

    def __str__(s):
        return s.__message

# ErrorExit
#
class ErrorExit(ShankError):
    '''
    If an error message has already been displayed and we want to just exit the app, this
    exception is raised.
    '''
    def __init__(s, emsg):
        super(ShankError, s).__init__(emsg)

