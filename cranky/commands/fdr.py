#
# Cranky fdr
#

from crankylib import cli


@cli.cranky_command()
def fdr(ctx):
    """Call `fakeroot debian/rules  <target>...` inside the appropriate chroot."""
    cli.cranky_call(ctx, "fdr")
