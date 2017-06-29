#!/usr/bin/env python
#

from sys                    import stdout, stderr
from decimal                import Decimal
import json
from os.path                import exists, getmtime
from time                   import time
from datetime               import datetime
from .dbg                   import Dbg

# o2ascii
#
# Convert a unicode string or a decial.Decimal object to a str.
#
def o2ascii(obj):
    retval = None
    if type(obj) != str:
        if type(obj) == unicode:
            retval = obj.encode('ascii', 'ignore')
        elif type(obj) == Decimal:
            retval = str(obj)
        elif type(obj) == int:
            retval = str(obj)
    else:
        retval = obj
    return retval

# fileage
#
def fileage(filename):
    # get time last modified
    if not exists(filename):
        return None

    # time in seconds since last change to file
    return time() - getmtime(filename)

# error
#
# Print strings to standard out preceeded by "error:".
#
def error(out):
    stderr.write("\n ** Error: %s\n" % out)
    stderr.flush()

# debug
#
# Print strings to standard out preceeded by "debug:".
#
def debug(out, dbg=False, prefix=True):
    if dbg:
        if prefix:
            stdo("debug: ")
        stdo(out)

# eout
#
# Print out an error message to stderr in a standard format. Note, since this uses
# the stderr.write() function, the emsg must contain any desired newlines.
#
def eout(emsg):
    stderr.write("\n")
    stderr.write("  ** Error: %s" % (emsg))
    stderr.write("\n")
    stderr.flush()

# stdo
#
# My own version of print but won't automatically add a linefeed to the end. And
# does a flush after every write.
#
def stdo(ostr):
    stdout.write(ostr)
    stdout.flush()
    return

def stde(ostr):
    stderr.write(ostr)
    stderr.flush()
    return

def dump(obj):
    stdo(json.dumps(obj, sort_keys=True, indent=4))
    stdo('\n')

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

# FileDoesntExist
#
class FileDoesntExist(Exception):
    def __init__(self, file_name=''):
        self.file_name = file_name

    def print_std_error(self):
        error('The file (%s) does not exist.\n' % self.file_name)

    def print_std_warning(self):
        stde('** Warning: The file (%s) does not exist.\n' % self.file_name)

# json_load
#
def json_load(file_name):
    """
    Load the indicated json format file, returning the created object.
    """
    Dbg.enter("json_load")

    retval = None
    if exists(file_name):
        with open(file_name, 'r') as f:
            retval = json.load(f)
    else:
        raise FileDoesntExist(file_name)

    Dbg.leave("json_load")
    return retval

# file_load
#
def file_load(file_name):
    """
    Load the indicated file into a string and return the string.
    """
    Dbg.enter("file_load")

    retval = None
    if exists(file_name):
        with open(file_name, 'r') as f:
            retval = f.read()
    else:
        raise FileDoesntExist(file_name)

    Dbg.leave("file_load")
    return retval

# vi:set ts=4 sw=4 expandtab:

