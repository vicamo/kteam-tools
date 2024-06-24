#
# Cranky class and helpers
#

import logging as log
import os
import sys

from subprocess import call

_ROOTPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
_LIBSPATH = os.path.abspath(os.path.join(_ROOTPATH, os.pardir, "libs"))
_PYPATH = os.environ.get("PYTHONPATH")
_PYTHONPATH = f"{_PYPATH}:{_ROOTPATH}:{_LIBSPATH}"


class Cranky:
    def __init__(self):
        """Initialize the cranky class"""
        pass

    def call(self, args):
        """Call an 'old' cranky subcommand in cmds.d"""
        # TODO: Remove this once all subcommands in cmds.d have been converted.
        cmd_name = args[0]
        args[0] = os.path.join(_ROOTPATH, "cmds.d", cmd_name)

        # Set the environment for the subcommand
        env = {
            "C": os.path.abspath(sys.argv[0]),
            "P": f"cranky {cmd_name}",
            "PYTHONPATH": _PYTHONPATH,
        }
        for key, val in env.items():
            os.environ[key] = val

        log.debug("Run command: %s (env=%s)", args, env)
        rc = call(args)
        if rc:
            log.error("Command failed: %s (args=%s)", cmd_name, args[1:])
        sys.exit(rc)
