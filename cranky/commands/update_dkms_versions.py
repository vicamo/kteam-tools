#
# Cranky update-dkms-versions
#

from crankylib import cli


@cli.cranky_command()
def update_dkms_versions(ctx):
    """Update DKMS versions file debian.<variant>/dkms-versions."""
    cli.cranky_call(ctx, "update-dkms-versions")
