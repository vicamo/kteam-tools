#
# Cranky kernels-distribute
#

import sys

from crankylib import cli
from crankylib.cranky import Cranky
from ktl.log import cerror


epilog_kernels_distribute = """
Examples:

$ cranky kernels-distribute --cycle 2024.01.08 --step 1

$ cranky kernels-distribute --cycle 2024.02.05 --step 2
"""


@cli.option_cycle(required=True)
@cli.option_step(required=True)
@cli.command(epilog=epilog_kernels_distribute)
def kernels_distribute(cycle, step):
    """Reassign kernels based on <kernel-versions>info/cranky_distribute input files"""
    try:
        Cranky().kernels_distribute(cycle=cycle, step=step)
    except Exception as e:
        cerror(e)
        sys.exit(1)
