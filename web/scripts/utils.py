#!/usr/bin/env python
#

from sys                    import stdout, stderr
from decimal                            import Decimal
import json
from os.path                import exists, getmtime
from time                   import time
import subprocess

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

# run_command
#
def run_command(cmd, dbg=False, dry_run=False):
        """
        Run a command in the shell, returning status and the output.
        prints a message if there's an error, and raises an exception.
        """
        status = ""
        result = ""
        if not dry_run:
            p = subprocess.Popen(*args, **kwargs)
            result, stderr = p.communicate()
            status = p.returncode
            debug("     cmd: '%s'" % cmd, dbg)
            debug("  status: '%d'" % status, dbg)
            debug("  result: '%s'" % result, dbg)
        else:
            debug("run_command: '%s'" % (cmd))

        return status, result.split('\n')

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
def debug(out, dbg=False):
    if dbg:
       stdout.write("debug: %s" % out)

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

def dump(obj):
    stdo(json.dumps(obj, sort_keys=True, indent=4))
    stdo('\n')

# vi:set ts=4 sw=4 expandtab:
