#
# Cranky rebase-selector
#

from crankylib import cli


@cli.cranky_command()
def rebase_selector(ctx):
    """"""
    cli.cranky_call(ctx, "rebase-selector")
