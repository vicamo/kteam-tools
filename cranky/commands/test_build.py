#
# Cranky test-build
#

from crankylib import cli


@cli.cranky_command()
def test_build(ctx):
    """Build kernel binary packages using Kamal's git-build-kernel build script."""
    cli.cranky_call(ctx, "test-build")
