#
# Cranky check-packaging
#

from crankylib import cli


@cli.cranky_command()
def check_packaging(ctx):
    """Perform some basic packaging sanity checks."""
    cli.cranky_call(ctx, "check-packaging")
