#
# Cranky pull-source
#

from crankylib import cli


@cli.cranky_command()
def pull_source(ctx):
    """Downloads the specified VERSION of the kernel source package SOURCE_PACKAGE
    from Launchpad, or the latest version of the specified RELEASE.

    There are basically two modes of operation:
      1) If both VERSION and RELEASE are specified, the script will use the URLs
         from the file ~/.getabis.<RELEASE>[-<VARIANT>] to download the package.
         This mode is used for downloading packages from ESM or private PPAs.
      2) Otherwise, the script simply calls pull-lp-source with the specified
         positional arguments. This mode is used for downloading regular kernel
         packages from the archive."""
    cli.cranky_call(ctx, "pull-source")
