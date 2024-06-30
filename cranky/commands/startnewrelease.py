#
# Cranky startnewrelease
#

from crankylib import cli


@cli.cranky_command()
def startnewrelease(ctx):
    """Create an opening changelog entry."""
    cli.cranky_call(ctx, "startnewrelease")
