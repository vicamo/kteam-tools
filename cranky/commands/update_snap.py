#
# Cranky update-snap
#

from crankylib import cli


@cli.cranky_command()
def update_snap(ctx):
    """Update the kernel snap snapcrat.yaml file with the source package version
    published on the specified pocket (default from -proposed)."""
    cli.cranky_call(ctx, "update-snap")
