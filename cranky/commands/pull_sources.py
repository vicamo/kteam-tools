#
# Cranky pull-sources
#

from crankylib import cli


@cli.cranky_command()
def pull_sources(ctx):
    """Download the kernel source packages specified by HANDLE to the current
    directory. The trees for the HANDLE need to be checked out and prepared,
    and the versions downloaded will be the previous one by looking at the
    changelog. It uses cranky pull-source command, thus using getabis files."""
    cli.cranky_call(ctx, "pull-sources")
