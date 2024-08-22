#
# Cranky tag
#

from crankylib import cli


@cli.cranky_command()
def tag(ctx):
    """Tag the current Ubuntu kernel git tree with the correct version tag."""
    cli.cranky_call(ctx, "tag")
