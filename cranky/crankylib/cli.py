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
