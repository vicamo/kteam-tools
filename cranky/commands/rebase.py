#
# Cranky rebase
#

from crankylib import cli


@cli.cranky_command()
def rebase(ctx):
    """Rebase the current main kernel tree onto its parent tree."""
    cli.cranky_call(ctx, "rebase")
