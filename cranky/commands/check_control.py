#
# Cranky check-control
#

from crankylib import cli


@cli.cranky_command()
def check_control(ctx):
    """Check debian/control for missing or invalid package stanzas."""
    cli.cranky_call(ctx, "check-control")
