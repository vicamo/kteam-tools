#
# Cranky update-dependents
#

from crankylib import cli


@cli.cranky_command()
def update_dependents(ctx):
    """Update all dependent packages (-meta, -signed, ...).

    Runs 'cranky update-dependent' against all packages in this tree set. This
    command may be run from any package in a tree set. All updates are completed as
    part of a transaction so that if any package fails to update, all packages will
    be restored to their original HEAD state.

    Note: Arguments must match update-dependent"""
    cli.cranky_call(ctx, "update-dependents")
