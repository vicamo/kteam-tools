#
# Cranky view-repos
#

from crankylib import cli


@cli.cranky_command()
def view_repos(ctx):
    """View kernel repositories in web browser, given a kernel
    handle and optional dependent package repo comma-separated list."""
    cli.cranky_call(ctx, "view-repos")
