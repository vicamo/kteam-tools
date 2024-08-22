#
# Cranky chroot
#

from crankylib import cli


@cli.cranky_command()
def chroot(ctx):
    """Build either base chroots or chroot sessions appropriate for building
    sources or updating configurations."""
    cli.cranky_call(ctx, "chroot")
