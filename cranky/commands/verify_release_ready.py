#
# Cranky verify-release-ready
#

from crankylib import cli


@cli.cranky_command()
def verify_release_ready(ctx):
    """Verify various parameters (eg. release/package names, ABI, git tags, LP bugs)
    of main and dependent kernel packages for release."""
    cli.cranky_call(ctx, "verify-release-ready")
