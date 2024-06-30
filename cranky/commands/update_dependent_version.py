#
# Cranky update-dependent-version
#

from crankylib import cli


@cli.cranky_command()
def update_dependent_version(ctx):
    """Update a dependent package version (meta, signed, lrm)."""
    cli.cranky_call(ctx, "update-dependent-version")
