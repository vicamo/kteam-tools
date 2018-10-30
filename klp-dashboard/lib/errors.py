# LKPError
#
class LKPError(Exception):
    '''
    '''
    def __init__(s, emsg):
        s.message = emsg


# ErrorExit
#
class ErrorExit(LKPError):
    '''
    If an error message has already been displayed and we want to just exit the app, this
    exception is raised.
    '''
    def __init__(s, emsg):
        super(LKPError, s).__init__(emsg)
