#!/usr/bin/env python
#

from sys                                import stdout, stderr
from os                                 import path
from datetime                           import datetime
import json

import yaml

from .dbg                               import Dbg

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

    def print_std_error(self):
        error('The file (%s) does not exist.\n' % self.file_name)

    def print_std_warning(self):
        stde('** Warning: The file (%s) does not exist.\n' % self.file_name)

# o2ascii
#
# Convert a unicode string or a decial.Decimal object to a str.
#
def o2ascii(obj):
    retval = None
    if type(obj) != str:
        if type(obj) == unicode:
            retval = obj.encode('ascii', 'ignore')
        else:
            retval = str(obj)
    else:
        retval = obj
    return retval

# error
#
def error(out):
    """
    Writes a string to stdout preceeded by a linefeed and "Error:" text and
    followed by a linefeed.
    """
    stde("\n ** Error: %s\n" % out)

# stdo
#
def stdo(ostr):
    """
    Write a string to stdout:
      1. Doesn't automatically add a linefeed to the end.
      2. Does a flush after every write.
    """
    stdout.write(ostr)
    stdout.flush()
    return

# stde
#
def stde(ostr):
    """
    Write a string to stderr:
      1. Doesn't automatically add a linefeed to the end.
      2. Does a flush after every write.
    """
    stderr.write(ostr)
    stderr.flush()
    return

# dump
#
def dump(obj):
    """
    Writes to stdout a json formatted version of the object that was passed in.
    """
    stdo(json.dumps(obj, sort_keys=True, indent=4))
    stdo('\n')

# data_load
#
def data_load(file_name):
    if file_name.endswith('.rc') or file_name.endswith('.json'):
        return json_load(file_name)
    if file_name.endswith('.yaml'):
        return yaml_load(file_name)
    raise ValueError("unknown file type for {}".format(file_name))

# json_load
#
def json_load(file_name):
    """
    Load the indicated json format file, returning the created object.
    """
    Dbg.enter("json_load")

    retval = None
    if path.exists(file_name):
        with open(file_name, 'r') as f:
            retval = json.load(f)
    else:
        raise FileDoesntExist(file_name)

    Dbg.leave("json_load")
    return retval

# yaml_load
#
def yaml_load(file_name):
    """
    Load the indicated yaml format file, returning the created object.
    """
    Dbg.enter("yaml_load")

    retval = None
    if path.exists(file_name):
        with open(file_name, 'r') as f:
            retval = yaml.safe_load(f)
    else:
        raise FileDoesntExist(file_name)

    Dbg.leave("yaml_load")
    return retval

# file_load
#
def file_load(file_name):
    """
    Load the indicated file into a string and return the string.
    """
    Dbg.enter("file_load")

    retval = None
    if path.exists(file_name):
        with open(file_name, 'r') as f:
            retval = f.read()
    else:
        raise FileDoesntExist(file_name)

    Dbg.leave("file_load")
    return retval

# date_to_string
#
def date_to_string(date):
    """
    Return a standard, string representation of the date given. It is assumed that the
    date is UTC based.
    """
    return "None" if date is None else date.strftime("%A, %d. %B %Y %H:%M UTC")

# string_to_date
#
def string_to_date(date):
    """
    Return a datetime object based on the string in a well known format.
    """
    return datetime.strptime(date, '%A, %d. %B %Y %H:%M UTC')

# vi:set ts=4 sw=4 expandtab:
