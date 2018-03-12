#!/usr/bin/env python
#
# Helper utilities and classes for the cranky tools
#
# Juerg Haefliger <juerg.haefliger@canonical.com>
#

import sys

from ktl.termcolor import colored


def cerror(txt, die=True):
    """
    Cranky error: Emit a red error message
    """
    print(colored("Error: %s" % txt, "red"))
    if die:
        sys.exit(1)


def cinfo(txt):
    """
    Cranky info: Emit a yellow info message
    """
    print(colored(txt, "yellow"))
