#
# Cranky review
#

from crankylib import cli


@cli.cranky_command()
def review(ctx):
    """Run final checks on a source package set, and generate a set of diffs from the
    previous package versions for review."""
    cli.cranky_call(ctx, "review")
