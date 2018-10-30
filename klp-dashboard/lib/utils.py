#!/usr/bin/env python
#

from os                                 import path
import json

# Exit
#
class Exit(Exception):
    """
    If an error message has already been displayed and we want to just exit the app, this
    exception is raised.
    """
    pass

# FileDoesntExist
#
class FileDoesntExist(Exception):
    def __init__(self, file_name=''):
        self.file_name = file_name

# json_load
#
def json_load(file_name):
    """
    Load the indicated json format file, returning the created object.
    """
    retval = None
    if path.exists(file_name):
        with open(file_name, 'r') as f:
            retval = json.load(f)
    else:
        raise FileDoesntExist(file_name)
    return retval

# file_load
#
def file_load(file_name):
    """
    Load the indicated file into a string and return the string.
    """
    retval = None
    if path.exists(file_name):
        with open(file_name, 'r') as f:
            retval = f.read()
    else:
        raise FileDoesntExist(file_name)
    return retval
