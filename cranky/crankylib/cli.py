#
# Cranky cli related helper functions
#

import logging as log

import click

from crankylib import cranky


class KeepDoubleDashArgs(click.Group):
    def parse_args(self, ctx, args):
        # Click swallows '--' arguments so replace them with '----' to prevent that
        args = ["----" if a == "--" else a for a in args]
        super(KeepDoubleDashArgs, self).parse_args(ctx, args)


@click.group(cls=KeepDoubleDashArgs)
@click.option("--debug", is_flag=True, help="Print debugging output.")
@click.pass_context
def cranky_cli(ctx, debug):
    """The cranky command line tool is a collection of tools that simplifies the
    process of preparing and developing Ubuntu kernel source packages."""
    # Set up the logger
    log_level = log.DEBUG if debug else log.INFO
    log.basicConfig(format="%(levelname)s: %(message)s", level=log_level)

    # Initialize the cranky class that is passed to all commands via the context
    ctx.obj = cranky.Cranky()


def cranky_command(*args, **kwargs):
    # TODO: Remove this once all subcommands in cmds.d have been converted.
    # Temporary (click) command decorator that:
    #   1) ignores unknown options and arguments, so that they can be passed down unparsed to
    #      the cranky subcommands
    #   2) removes the special --help option, so that click doesn't act on it and instead is
    #      also passed down to the cranky subcommands
    #   3) passes the click context to all commands, so that the Cranky class is available
    cs = kwargs.get("context_settings", {})
    cs["ignore_unknown_options"] = True
    cs["allow_extra_args"] = True
    cs["help_option_names"] = []
    kwargs["context_settings"] = cs

    # @click.command()
    click_command = click.command(*args, **kwargs)

    def wrapper(func):
        # @click.command()
        # @click.pass_context
        return click_command(click.pass_context(func))

    return wrapper


def cranky_call(ctx, cmd):
    # TODO: Remove this once all subcommands in cmds.d have been converted.
    # Wrappper that calls 'old' subcommands in cmds.d.
    cranky = ctx.obj
    args = ctx.args

    # Convert "----" arguments back to "--"
    args = ["--" if a == "----" else a for a in args]

    cranky.call([cmd] + args)


# Convenience aliases. These are defined so that all related functions are provided by a
# single module (this file) and click does not need to be imported by subcommands.
command = click.command
option = click.option


def option_dry_run(help=None):
    """Common --dry-run option decorator"""
    if not help:
        help = "Do not modify state."

    def wrapper(func):
        return click.option("--dry-run", help=f"{help}", is_flag=True)(func)

    return wrapper


def option_color(default=True):
    """Common --color option decorator"""
    help = "Enable/disable colored output"

    def wrapper(func):
        return click.option("--color/--no-color", help=f"{help} (default={default}).", default=default)(func)

    return wrapper


def option_deprecated_warn(cmd, opt):
    log.warning(
        f"Option '{opt}' is deprecated and will be removed soon. Check 'cranky {cmd} --help' for more information."
    )


def option_deprecated(*args, **kwargs):
    """Generic decorator for deprecated options"""
    new = kwargs.pop("new_option", None)
    if new:
        prefix = f"(DEPRECATED, use '{new}' instead)"
    else:
        prefix = "(DEPRECATED)"
    kwargs["help"] = prefix + " " + kwargs.get("help", "")

    def wrapper(func):
        return click.option(*args, **kwargs)(func)

    return wrapper


def option_deprecated_nc():
    """Common deprecated --nc option decorator"""

    def wrapper(func):
        return option_deprecated(
            "--nc",
            is_flag=True,
            new_option="--no-color",
            help="No Colour. By default the debug output that is printed comes out in multiple "
            + "colours to help with the debugging. This option disables that.",
        )(func)

    return wrapper


def _add_argument_help(func, metavar, help):
    """Append an argument help line to the function's docstring"""
    doc = func.__doc__.split("\n")
    if "Arguments:" not in doc:
        doc.append("")
        doc.append("Arguments:")

    # Insert the help line (we can't append but need to insert at the top of the
    # argument list to preseve the correct argument order)
    idx = doc.index("Arguments:")
    doc.insert(idx + 1, "")
    doc.insert(idx + 2, f"  {metavar}  {help}")

    func.__doc__ = "\n".join(doc)


def argument(*args, **kwargs):
    """Generic argument decorator that supports a 'help' keyword"""

    def wrapper(func):
        # Check if "help" is provided (which click doesn't support for arguments)
        # so we can implement our own argument help text rendering
        help = kwargs.pop("help", None)
        if help:
            metavar = kwargs.get("metavar") or args[0].upper()
            _add_argument_help(func, metavar, help)
        return click.argument(*args, **kwargs)(func)

    return wrapper


def argument_handle(help=None):
    """Common 'handle' argument decorator"""
    if not help:
        help = "Handle to a kernel package set in <series>:<package> format or a directory path."

    def wrapper(func):
        return argument("handle", help=help)(func)

    return wrapper
