#
# Cranky push-review
#

from crankylib import cli


@cli.cranky_command()
def push_review(ctx):
    """Push all artifacts and tags required for a cranking review to a remote builder.
    Expected to be run in the linux repo directory.
    Built packages are expected to be ready and in the parent directory."""
    cli.cranky_call(ctx, "push-review")
