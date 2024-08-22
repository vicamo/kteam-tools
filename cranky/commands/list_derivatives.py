#
# Cranky list-derivatives
#

from crankylib import cli


@cli.cranky_command()
def list_derivatives(ctx):
    """List all kernel sources which are derived from one or more given kernel
    source(s). If no source is specified, then the current directory would
    have to be one of the working trees belonging to the set related to a
    kernel source.

    Filters can be specified and limit the list of derivatives to those
    satisfying all filters. The provided sources are always included in
    the list, regardless of filters."""
    cli.cranky_call(ctx, "list-derivatives")
