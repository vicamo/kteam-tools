#!/usr/bin/env python
#

# FalseReturn
#
class FalseReturn(Exception):
    '''
    I want to jump down the end of the method and return.
    '''
    def __init__(s, msg):
        s.__message = msg

    @property
    def message(s):
        '''
        Maybe we want to explain why we jumped to the end of the method and returned.
        '''
        return s.__message

# GeneralError
#
class GeneralError(Exception):
    '''
    Generic base class for my exceptions.
    '''
    def __init__(s, emsg):
        s.__message = emsg

    @property
    def message(s):
        '''
        The shell command that was being executed when the timeout occured.
        '''
        return s.__message

# ErrorExit
#
class ErrorExit(GeneralError):
    '''
    If an error message has already been displayed and we want to just exit the app, this
    exception is raised.
    '''
    def __init__(s, emsg):
        GeneralError(emsg)

