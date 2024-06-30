#
# Cranky diff-sauce
#

from crankylib import cli


@cli.cranky_command()
def diff_sauce(ctx):
    """compare SAUCE patches applied between two different Ubuntu tags."""
    cli.cranky_call(ctx, "diff-sauce")
