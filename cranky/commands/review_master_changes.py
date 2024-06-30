#
# Cranky review-master-changes
#

from crankylib import cli


@cli.cranky_command()
def review_master_changes(ctx):
    """List all the relevant changes since the last release in the
    debian.BRANCH directory of the base kernel of a derivative. This list
    should be used as a guide for things that might need to be ported to a
    derivative."""
    cli.cranky_call(ctx, "review-master-changes")
