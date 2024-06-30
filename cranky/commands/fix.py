#
# Cranky fix
#

from crankylib import cli


@cli.cranky_command()
def fix(ctx):
    """Fix various common files from kteam-tools for main packages, and sync those between
    main and subsiduary packages."""
    cli.cranky_call(ctx, "fix")
