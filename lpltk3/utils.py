#!/usr/bin/python3

import os.path
from decimal                     import Decimal
from lazr.restfulclient.resource import (
    Collection,
    Entry,
    )

# o2str
#
# Convert a unicode, decimal.Decimal, or datetime object to a str.
#
def o2str(obj):
    retval = None
    if type(obj) == str:
        return obj
    elif type(obj) == unicode:
        return obj.encode('ascii', 'ignore')
    elif type(obj) == Decimal:
        return str(obj)
    elif type(obj) == list:
        new_list = []
        for item in obj:
            new_list.append(o2str(item))
        return new_list
    elif str(type(obj)) == "<type 'datetime.datetime'>":
        return obj.ctime()
    else:
        #print str(type(obj))
        return obj

# typecheck_Collection
#
# Raises TypeError if the given object is not a Launchpad 'Collection' object
#
def typecheck_Collection(obj):
    if type(obj) != Collection:
        raise TypeError("Object is of type %s, but must be Launchpad Collection object" %(type(obj)))
    return obj

# typecheck_Entry
#
# Raises TypeError if the given object is not a Launchpad 'Entry' object
#
def typecheck_Entry(obj):
    if type(obj) != Entry:
        raise TypeError("Object is of type %s, but must be Launchpad Entry object" %(type(obj)))
    return obj

# vi:set ts=4 sw=4 expandtab:

# load_file
#
# Returns the contents of a text file
#
def load_file(filename):
    f = open(filename, 'r')
    text = f.read()
    f.close()
    return text

# write_file
#
# Writes text into a given file path, creating path if needed
#
def write_file(filename, text):
    path = os.path.dirname(filename)
    if not os.path.isdir(path):
        os.makedirs(path)
    f = open(filename, 'w')
    f.write(text)
    f.close()
    return

# file_age
#
# Returns age of file in seconds
#
def file_age(filename):
    from time import time
    file_time = os.stat(filename).st_mtime
    return time() - file_time
