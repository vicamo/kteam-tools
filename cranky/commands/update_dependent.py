#
# Cranky update-dependent
#

from crankylib import cli


@cli.cranky_command()
def update_dependent(ctx):
    """Update a dependent package (-meta, -signed, ...).

    This script checks that there is an 'update-version' script in the current
    directory and executes it. It parses the output of 'update-version' to extract
    the 'git commit' line and runs that command to commit the changes.

    Note: Arguments must match update-dependents"""
    cli.cranky_call(ctx, "update-dependent")
