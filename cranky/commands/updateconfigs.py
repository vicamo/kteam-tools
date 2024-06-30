#
# Cranky updateconfigs
#

from crankylib import cli


@cli.cranky_command()
def updateconfigs(ctx):
    """Call `fakeroot debian/rules updateconfigs <target>...` inside the appropriate chroot."""
    cli.cranky_call(ctx, "updateconfigs")
