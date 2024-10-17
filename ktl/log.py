import logging
from logging                            import info, debug, exception, warning
from ktl.termcolor                      import colored

def cinfo(msg, color='white'):
    Clog.info(msg, color)

def cdebug(msg, color='magenta'):
    Clog.debug(msg, color)

def cwarn(msg, color='red'):
    Clog.warn(msg, color)

def cerror(msg, color='red'):
    Clog.warn(msg, color)

def cexception(ex):
    Clog.exception(ex)

def cnotice(msg, color='yellow'):
    Clog.notice(msg, color)

def center(msg):
    Clog.enter('Enter ' + msg)

def cleave(msg):
    Clog.leave('Leave ' + msg)

class Clog:
    '''
    Colored logging.
    '''
    dbg = False
    color = True
    indent = 0

    @classmethod
    def info(c, msg, color='white'):
        if c.dbg:
            # I do this becaus i'm weird and like things lined up in my log output
            # and "INFO -" is fewer chars then "DEBUG -" and so things don't line
            # up.
            #
            debug(colored(msg, color))
        else:
            info(colored(msg, color))

    @classmethod
    def debug(c, msg, color='magenta'):
        if c.color:
            debug(colored(msg, color))
        else:
            debug(msg)

    @classmethod
    def warn(c, msg, color='red'):
        if c.color:
            warning(colored(msg, color))
        else:
            warning(msg)

    @classmethod
    def exception(c, ex):
        exception(ex)

    @classmethod
    def notice(c, msg, color='yellow'):
        if c.color:
            c.info(colored(msg, color))
        else:
            info(msg)

    @classmethod
    def enter(c, msg):
        if c.color:
            c.debug(colored(msg, 'green'))
        else:
            c.debug(msg)
        c.indent += 4

    @classmethod
    def leave(c, msg):
        c.indent -= 4
        if c.color:
            c.debug(colored(msg, 'green'))
        else:
            c.debug(msg)


# modules which wish to override the default colours when logging need to use
# the ClogAdapter when declaring their logger.
#
# from ktl.log import ClogAdapter
# logger = ClogAdapter(logging.getLogger(__name__))
class ClogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return msg, kwargs

    def log(self, level, msg, *args, **kwargs):
        if "color" in kwargs:
            kwargs.setdefault("extra", {})["color"] = kwargs.pop("color")

        super().log(level, msg, *args, **kwargs)


# applications which to honour colours of colourised records
# need to use the ClogFilter filter on their output.
#
# import logging
# from ktl.log import ClogFilter
#
# if __name__ == "__main__":
#    logging.basicConfig(...)
#
#    # Enable colorisation.
#    root = logging.getLogger()
#    root.handlers[0].addFilter(ClogFilter())
class ClogFilter(logging.Filter):
    def filter(self, record):
        color = getattr(record, "color", None)
        if color is None:
            color = {
                logging.DEBUG: "magenta",
                logging.INFO: "white",
                logging.WARNING: "yellow",
                logging.ERROR: "red",
                logging.CRITICAL: "red",
            }.get(record.levelno)
        if color is not None:
            record.msg = colored(record.msg, color=color)

        return True


# vi:set ts=4 sw=4 expandtab syntax=python:
