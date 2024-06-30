#
# Cranky rmadison
#

from crankylib import cli


@cli.cranky_command()
def rmadison(ctx):
    """Query the Ubuntu archives and private PPAs for kernel source package
    information and print the data in an 'rmadison'-like format.

    For regular distribution packages, the standard Ubuntu archive is queried. For
    special kernel packages like ESM or private packages, the relevant private PPAs
    are queried.

    Note: That the user who runs this script needs to have sufficient Launchpad
    privileges to query the various private PPAs."""
    cli.cranky_call(ctx, "rmadison")
