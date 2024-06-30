#
# Cranky tags
#

from crankylib import cli


@cli.cranky_command()
def tags(ctx):
    """Tag all packages of current Ubuntu kernel git tree set with the correct version
    tag."""
    cli.cranky_call(ctx, "tags")
