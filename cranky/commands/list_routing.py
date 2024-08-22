#
# Cranky list-routing
#

from crankylib import cli


@cli.cranky_command()
def list_routing(ctx):
    """List the known routing information for a kernel package (set)."""
    cli.cranky_call(ctx, "list-routing")
