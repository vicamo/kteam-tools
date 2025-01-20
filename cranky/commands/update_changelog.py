#
# Cranky update-changelog
#

import sys

from crankylib import cli, error
from crankylib.cranky import Cranky

from ktl.log import cerror, Clog


epilog_update_changelog = """
Examples:

\b
$ cranky update-changelog --from-commit HEAD~20

    Print the changes from the last 20 commits to the console.

\b
$ cranky update-changelog --from-commit HEAD~10 --changelog debian.master/changelog

    Add the changes from the last 10 commits to debian.master/changelog.

\b
$ cranky update-changelog --from-changelog debian.master/changelog --from-version 5.4.0-10.10 --changelog debian.raspi/changelog

    Add the changes from debian.master/changelog since version 5.4.0-10.10
to debian.raspi/changelog.
"""  # noqa: E501 (Line too long)


@cli.command(epilog=epilog_update_changelog)
@cli.option_color()
@cli.option(
    "--changelog",
    type=cli.Path(exists=True),
    help="Changelog file to update. If not provided, prints the changes to the console.",
)
@cli.option(
    "--from-commit",
    help="Starting commit of the changes to include in the changelog.",
)
@cli.option("--from-changelog", type=cli.Path(exists=True), help="Changelog file to pull the changes from.")
@cli.option(
    "--from-version", help="Starting version of the changes to include in the changelog. Implies --from-changelog."
)
def update_changelog(color, changelog, from_commit, from_version, from_changelog):
    """Update an Ubuntu kernel changelog."""
    Clog.color = color
    try:
        Cranky().update_changelog(
            changelog=changelog, from_commit=from_commit, from_version=from_version, from_changelog=from_changelog
        )
    except error.CrankyError as e:
        cerror(e)
        sys.exit(1)
