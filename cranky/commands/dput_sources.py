#
# Cranky dput-sources
#

from crankylib import cli


@cli.cranky_command()
def dput_sources(ctx):
    """Sign and upload the kernel source packages specified by HANDLE to the
    DESTINATION PPA. The script will show the details of the destination PPA
    and list the source packages that it wants to upload and wait for user
    confirmation before doing the actual sign and upload."""
    cli.cranky_call(ctx, "dput-sources")
