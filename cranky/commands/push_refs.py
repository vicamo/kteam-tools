#
# Cranky push-refs
#

from crankylib import cli


@cli.cranky_command()
def push_refs(ctx):
    """Push the refs (HEAD and tags) to all remotes."""
    cli.cranky_call(ctx, "push-refs")
