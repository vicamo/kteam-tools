#
# Cranky checkout
#

from crankylib import cli


@cli.cranky_command()
def checkout(ctx):
    """Checkout the repos (typically 'linux', 'linux-meta', and 'linux-signed') that
    make up a set of Ubuntu kernel packages. The repos are cloned first, if they
    don't yet exist locally. The local directories where the repos are cloned into
    are specified in the cranky config file (see 'package-path' in the
    'Configuration file' section below)."""
    cli.cranky_call(ctx, "checkout")
