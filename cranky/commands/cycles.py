#
# Cranky cycles
#

from crankylib import cli


@cli.cranky_command()
def cycles(ctx):
    """Manipulate refs/swm/*/* for this handle"""
    cli.cranky_call(ctx, "cycles")
