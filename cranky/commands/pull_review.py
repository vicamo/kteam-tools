#
# Cranky pull-review
#

from crankylib import cli


@cli.cranky_command()
def pull_review(ctx):
    """Pull a crank review request from a formatted text input."""
    cli.cranky_call(ctx, "pull-review")
