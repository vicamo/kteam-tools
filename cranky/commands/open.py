#
# Cranky open
#

from crankylib import cli


@cli.cranky_command()
def open(ctx):
    """Create a "start new release" commit. The new commit will contain ABI
    changes and any customization required by backport kernels."""
    cli.cranky_call(ctx, "open")
