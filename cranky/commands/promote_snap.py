#
# Cranky promote-snap
#

from crankylib import cli


@cli.cranky_command()
def promote_snap(ctx):
    """This command is for promoting snaps which have been produced already
    into their next destination channels (as determines by the workflow).
    For some kernel snaps this may also be a required step for some edge
    and beta channels if automatic uploads cannot cover all combinations
    of tracks."""
    cli.cranky_call(ctx, "promote-snap")
