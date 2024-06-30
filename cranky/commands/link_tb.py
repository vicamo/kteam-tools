#
# Cranky link-tb
#

from crankylib import cli


@cli.cranky_command()
def link_tb(ctx):
    """Find and update the Launchpad tracking bug to reflect the proposed kernel
    version being created, and make a local git commit with a link to it."""
    cli.cranky_call(ctx, "link-tb")
