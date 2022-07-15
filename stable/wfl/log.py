#!/usr/bin/env python3
#
from logging                            import info, debug
from ktl.termcolor                      import colored

def cinfo(msg, color='white'):
    Clog.info(msg, color)

def cdebug(msg, color='magenta'):
    Clog.debug(msg, color)

def cwarn(msg, color='red'):
    Clog.warn(msg, color)

def cerror(msg, color='red'):
    Clog.warn(msg, color)

def cnotice(msg, color='yellow'):
    Clog.notice(msg, color)

def center(msg):
    Clog.enter('Enter ' + msg)

def cleave(msg):
    Clog.leave('Leave ' + msg)

@contextmanager
def cinstance(instance):
    try:
        Clog.instance = instance + " "
        yield
    finally:
        Clog.instance = ""


class Clog:
    '''
    Colored logging.
    '''
    dbg = False
    color = True
    indent = 0
    instance = ""

    @classmethod
    def colored(c, msg, color):
        if c.color:
            return colored(msg, color)
        return msg

    @classmethod
    def info(c, msg, color='white'):
        msg = c.instance + ' ' * c.indent + str(msg)
        info(c.colored(msg, color))

    @classmethod
    def debug(c, msg, color='magenta'):
        msg = c.instance + ' ' * c.indent + str(msg)
        debug(c.colored(msg, color))

    @classmethod
    def warn(c, msg, color='red'):
        c.info(msg, color)

    @classmethod
    def notice(c, msg, color='yellow'):
        c.info(msg, color)

    @classmethod
    def enter(c, msg):
        c.debug(msg, 'green')
        if c.dbg:
            c.indent += 4

    @classmethod
    def leave(c, msg):
        if c.dbg:
            c.indent -= 4
        c.debug(msg, 'green')

# vi:set ts=4 sw=4 expandtab syntax=python:
