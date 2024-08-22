#
# Cranky build-sources
#

from crankylib import cli


@cli.cranky_command()
def build_sources(ctx):
    """Build all source packages for the specified series and source as specified in
    kernel-series.yaml."""
    cli.cranky_call(ctx, "build-sources")
