#
# Cranky reorder
#

from crankylib import cli


@cli.cranky_command()
def reorder(ctx):
    """Move the latest "start new release" commit right after the latest
    "closing" commit."""
    cli.cranky_call(ctx, "reorder")
