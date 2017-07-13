# Utility routines and classes for debugging info

# (C) Copyright 2009, Markus Korn <thekorn@gmx.de>
# (C) Copyright 2009, Bryce Harrington <bryce@canonical.com>

import re, os, sys

def dbg(msg):
    if "LPLTK_DEBUG" in os.environ:
        sys.stderr.write("%s\n" %(msg))

def err(msg):
    sys.stderr.write("Error:  %s\n" %(msg))

def die(msg):
    sys.stderr.write("Fatal:  %s\n" %(msg))
    sys.exit(1)

StdOut = sys.stdout                                    
class DebugStdOut(object):
    '''
    Debug version of STDOUT to redact out the oauth credentials
    so that if the debug output is posted to a bug, it will not include
    this sensitive info.
    '''

    RE_OAUTH_TOKEN = re.compile(r"oauth_token=\"([^\"]{2})[^\"]*")
    RE_OAUTH_SIGNATURE = re.compile(r"oauth_signature=\"([^\"]{3})[^\"]*")

    def write(self, txt):
        txt = DebugStdOut.RE_OAUTH_SIGNATURE.sub(r"""oauth_signature="\1YYYYYYY""", txt)
        txt = DebugStdOut.RE_OAUTH_TOKEN.sub(r"""oauth_token="\1XXXXXXXX""", txt)
        StdOut.write(txt)
        
    def __getattr__(self, name):
        return getattr(StdOut, name)

def dump_launchpad_object(i):
    print repr(i)
    print " attr:  ", sorted(i.lp_attributes)
    print " ops:   ", sorted(i.lp_operations)
    print " coll:  ", sorted(i.lp_collections)
    print " entr:  ", sorted(i.lp_entries)
    print
