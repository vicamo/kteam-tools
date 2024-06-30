#
# Cranky close
#

from crankylib import cli


@cli.cranky_command()
def close(ctx):
    """Prepare the closing release commit. Include all the changelog entries
    in the current release, including the changes from the base
    kernel. Also close the changelog entry and check for config changes."""
    cli.cranky_call(ctx, "close")
