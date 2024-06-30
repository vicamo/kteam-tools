#
# Cranky list-owners
#

from crankylib import cli


@cli.cranky_command()
def list_owners(ctx):
    """Query the kernel-series.yaml database and produce a list of kernels in the
    handle format (<series>:<source>) and the assigned owner (the shown owner
    is either a Launchpad Id or "UNASSIGNED")."""
    cli.cranky_call(ctx, "list-owners")
