#
# Cranky list-repos
#

from crankylib import cli


@cli.cranky_command()
def list_repos(ctx):
    """Query the kernel-series.yaml database for a list of kernels and their package's repo
    urls and the name of its main branch."""
    cli.cranky_call(ctx, "list-repos")
