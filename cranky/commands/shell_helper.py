#
# Cranky shell-helper
#

from crankylib import cli


@cli.cranky_command()
def shell_helper(ctx):
    """Helper program for getting cranky config and handle data from shell scripts."""
    cli.cranky_call(ctx, "shell-helper")
