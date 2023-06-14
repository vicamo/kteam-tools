#!/usr/bin/env python3

import errno
import os

def abspath(name):
    """Return the absolute pathname of 'name' which is interpreted as as
       relative path to this file's path.
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    if not os.path.isfile(path):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    return path
