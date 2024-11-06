"""Module to parse pending patchset and run checks on them

"""

import click
import json
import subprocess
import logging
from patchset_processor import PatchsetProcessor


@click.command()
@click.option("--pending", help="use file as input instead of calling pending_SRU.sh")
@click.option("--dry-run", is_flag=True, default=False, help="Don't do any thing.")
@click.option("--verbose", is_flag=True, default=False)
@click.option("--period", default="3month", help="Period to look back for patches, default to 3month.")
def check_pending(pending, period, dry_run, verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")
    if pending:
        with open(pending) as input:
            pending_patchsets_search = json.load(input)
    else:
        pending_patchsets_search = json.loads(
            subprocess.run(["./pending_SRU.sh", "-p", period, "-j"], stdout=subprocess.PIPE).result.stdout
        )

    for patchset in pending_patchsets_search:
        p = PatchsetProcessor(patchset, dry_run)
        p.patchset_processing()


if __name__ == "__main__":
    check_pending()
