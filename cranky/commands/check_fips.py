#
# Cranky check-fips
#

from crankylib import cli


@cli.cranky_command()
def check_fips(ctx):
    """Check if there are any FIPS relevant changes since the last release. Any change
    that is identified should either be reverted or have a justification in the
    justifications file; otherwise the check will fail."""
    cli.cranky_call(ctx, "check-fips")
