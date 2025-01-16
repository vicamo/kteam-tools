#
# Cranky kernels-distribute
#

import os

from dataclasses import dataclass
from enum import Enum
from ktl.log import cerror, cinfo
from ktl.format_kernel_series import KernelSeriesYamlFormat
from ktl.sru_cycle import SruCycle
from typing import Any, Optional

# kernel-versions repo local path
KERNEL_VERSIONS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "kernel-versions"))
# local path where the cranky_distribute files are found
INFO_DIR = os.path.join(KERNEL_VERSIONS_DIR, "info/cranky_distribute")
KERNEL_SERIES = "info/kernel-series.yaml"


class KernelsDistributeStep(Enum):
    """Enum that shows if the distribute information is for step 1 or step 2.
    Step 1 --> distribute kernels for people working on upload rights that also need peer-reviewers.
    Step 2 --> extra in case there are people WITH upload rights that volunteered to help.
    """

    FIRST_STEP = 1
    SECOND_STEP = 2


# maps needed for getting the input files for each step of cranky distribute
flexible_kernels_filename = {
    KernelsDistributeStep.FIRST_STEP: os.path.join(INFO_DIR, "flexible_kernels_step_1"),
    KernelsDistributeStep.SECOND_STEP: os.path.join(INFO_DIR, "flexible_kernels_step_2"),
}

flexible_owners_filename = {
    KernelsDistributeStep.FIRST_STEP: os.path.join(INFO_DIR, "flexible_owners_step_1"),
    KernelsDistributeStep.SECOND_STEP: os.path.join(INFO_DIR, "flexible_owners_step_2"),
}

peer_reviewers_filename = {
    KernelsDistributeStep.FIRST_STEP: os.path.join(INFO_DIR, "peer_reviewers"),
    KernelsDistributeStep.SECOND_STEP: None,
}


@dataclass
class KernelsDistributeInfo:
    """Class that stores the cranky distribute info from <kernel_versions>/info/cranky_distribute.
    This is per step. Therefore
    - flexible_kernels -> <kernel_versions>/info/cranky_distribute/flexible_kernels_<step>
    - flexible_owners -> <kernel_versions>/info/cranky_distribute/flexible_owners_<step>
    - peer_reviewers --> <kernel_versions>/info/cranky_distribute/peer_reviewers

    peer-reviewers is only needed for step 1, thus is optional
    """

    flexible_kernels: list[str]
    flexible_owners: dict[str, str]
    peer_reviewers: Optional[dict[str, int]] = None

    @classmethod
    def from_files(cls, distribute_step, cycle):
        flexible_kernels = cls.parse_kernel_file(distribute_step=distribute_step)
        # Permutate the kernel list
        sru_cycles = [cycle.name for cycle in SruCycle().cycles]
        shift_no = Helper.calculate_shift_number(cycle, sru_cycles)
        flexible_kernels = Helper.permutate_list(shift_no, flexible_kernels)

        flexible_owners = cls.parse_dict_file(file=flexible_owners_filename[distribute_step])
        peer_reviewers = cls.parse_dict_file(file=peer_reviewers_filename[distribute_step])

        return cls(
            flexible_kernels=flexible_kernels,
            flexible_owners=flexible_owners,
            peer_reviewers=peer_reviewers,
        )

    @classmethod
    def parse_kernel_file(cls, distribute_step):
        kernels = []
        with open(flexible_kernels_filename[distribute_step]) as f:
            for line in f.readlines():
                kernels.append(line.strip())

        return kernels

    @classmethod
    def parse_dict_file(cls, file):
        if file is None:
            return None

        people = {}
        with open(file) as f:
            for line in f.readlines():
                data = line.split(":")
                no_kernels = int(data[1])
                people[str(data[0])] = no_kernels

        return people


class Helper:
    """class for helper methods"""

    @classmethod
    def calculate_shift_number(cls, cycle: str, cycles: list[str]) -> int:
        """Calculate the index of an sru cycle since 2024.01.08.
        cycles is a list of cycles from sru_info.yaml
        """
        p0 = cycles.index(cycle)
        p1 = cycles.index("2024.01.08")

        # Ignore security or development cycles
        shift_no = len([c for c in cycles[p0:p1] if c[0] not in ["s", "d"]]) - 1
        cinfo("Shift number {}".format(shift_no))

        return shift_no

    @classmethod
    def permutate_list(cls, shift_no: int, kernels: list[str]) -> list[str]:
        """Returns a shifted list by index = shift_no"""
        if shift_no < 0:
            return kernels

        shift_position = shift_no % len(kernels)

        return kernels[shift_position:] + kernels[:shift_position]

    @classmethod
    def distribute_kernels(cls, assignees: dict[str, int], _kernels: list[str]) -> dict[str, str]:
        """Generic method to distribute a list of kernels to a list of people.
        The assignee param is a map that contains the id of people and their maximum number of kernels
        they can take.
        The results is a map of (kernel, assignee)
        """
        kernels = _kernels.copy()
        result = {}

        i = 0
        maximum = assignees[max(assignees, key=lambda x: assignees[x])]
        for i in range(maximum):
            if len(kernels) == 0:
                break

            for assignee in assignees.keys():
                if len(kernels) == 0:
                    break
                if assignees[assignee] == 0:
                    continue

                result[kernels.pop(0)] = assignee

            i += 1

        return result

    @classmethod
    def find_kernel_series_entry(cls, kernel_series, series_name):
        for ks_entry in kernel_series.values():
            try:
                if ks_entry["codename"] == series_name:
                    return ks_entry
            except KeyError:
                continue


@dataclass
class KernelsDistribute:
    """Class used for reassignment of kernels.
    It is per cycle and it can be used for both step 1 and step 2 of assignments.
    To facilitate the implementation, a copy of <kernel_versions>/<cycle>/info/kernel-series.yaml
    is stored in memory. It is later used for validating if the kernels used for assignment do exist
    and are supported, but also for the actual reassignment.
    For first step, kernels that do not have a peer-reviewer will be automatically peer-reviewed by
    the cycle owner.
    """

    cycle: str
    cycle_owner: str
    distribute_step: KernelsDistributeStep
    kernels_distribute_info: KernelsDistributeInfo
    # Needed later to dump the new assignment to the kernel_series.yaml file
    kernel_series_path: str
    kernel_series_content: Any

    @classmethod
    def from_files(cls, cycle, step):
        distribute_step = KernelsDistributeStep(step)
        kd_info = KernelsDistributeInfo.from_files(distribute_step=distribute_step, cycle=cycle)

        cycle_owner = SruCycle().lookup_cycle(cycle=cycle).owner

        kernel_series_path = os.path.join(KERNEL_VERSIONS_DIR, cycle, KERNEL_SERIES)
        kernel_series_content = KernelSeriesYamlFormat.load(filename=kernel_series_path)

        return cls(
            cycle=cycle,
            cycle_owner=cycle_owner,
            distribute_step=distribute_step,
            kernels_distribute_info=kd_info,
            kernel_series_path=kernel_series_path,
            kernel_series_content=kernel_series_content,
        )

    def validate_kernel_list(self):
        """
        It will check if the flexible kernels are found and supported in the corresponding
        kernel_series.yaml cached file
        """

        for k in self.kernels_distribute_info.flexible_kernels:
            [series, kernel] = k.split(":")
            series_entry = Helper.find_kernel_series_entry(kernel_series=self.kernel_series_content, series_name=series)
            if not series_entry["supported"]:
                cerror("series {} is no longer supported".format(series))
                return False

            kernel_entry = series_entry["sources"][kernel]
            # Some kernels do not have 'supported' field, it is
            # inherrited from the series
            if "supported" not in kernel_entry:
                continue

            if not kernel_entry["supported"]:
                cerror("kernel {} is not supported".format(kernel))
                return False

        return True

    def update_kernel_series(self, reassignment, reviewers=None):
        """It will dump the new assignment to the corresponding kernel_series.yaml file.
        For first step, for each kernel entry, a peer-reviewer is used.
        For second step, no peer-reviewer is used because the new owners have upload rights.
        """

        cinfo("Overriding owners for cycle {}".format(self.cycle))

        for k, owner in reassignment.items():
            [series, kernel] = k.split(":")
            ks_entry = Helper.find_kernel_series_entry(kernel_series=self.kernel_series_content, series_name=series)
            ks_entry["sources"][kernel]["owner"] = owner
            if self.distribute_step == KernelsDistributeStep.FIRST_STEP:
                ks_entry["sources"][kernel]["peer-reviewer"] = reviewers[k]

        KernelSeriesYamlFormat.dump(filename=self.kernel_series_path, content=self.kernel_series_content)

    def distribute_step_1(self):
        """First step of assignments. The owners are people working on getting upload rights.
        Their kernels will also be automatically assigned to a peer-reviewer
        """
        if self.kernels_distribute_info.peer_reviewers is None:
            cerror("No peer reviewers list")
            return

        # Check if list of flexible kernels exist and are still supported
        if not self.validate_kernel_list():
            cerror("Validation failed, check the flexible kernels list")
            return

        # New owners arrangements
        owners_assignment = Helper.distribute_kernels(
            self.kernels_distribute_info.flexible_owners, self.kernels_distribute_info.flexible_kernels
        )
        reviewers_assignment = Helper.distribute_kernels(
            self.kernels_distribute_info.peer_reviewers, self.kernels_distribute_info.flexible_kernels
        )
        final_reviewers = {}
        # Leftover reviewers will be done by the cycle owner
        # This will also make sure only kernels that were assigned to new owner will also have
        # a peer-reviewer
        for kernel in owners_assignment.keys():
            if kernel in reviewers_assignment.keys():
                final_reviewers[kernel] = reviewers_assignment[kernel]
            else:
                final_reviewers[kernel] = self.cycle_owner

        # modify kernel-series.yaml files
        self.update_kernel_series(reassignment=owners_assignment, reviewers=final_reviewers)

    def distribute_step_2(self):
        """Second step of assignments. The owners are people who volunteered for help through
        their managers.  They do not need a peer-reviewer because they already have upload rights.
        """

        # Check if list of flexible kernels exist and are still supported
        if not self.validate_kernel_list():
            cerror("Validation failed, check the flexible kernels list")
            return

        # New owners arrangements
        owners_assignment = Helper.distribute_kernels(
            self.kernels_distribute_info.flexible_owners, self.kernels_distribute_info.flexible_kernels
        )

        # modify kernel-series.yaml files
        self.update_kernel_series(reassignment=owners_assignment)

    def distribute(self):
        distribute_map = {
            KernelsDistributeStep.FIRST_STEP: self.distribute_step_1,
            KernelsDistributeStep.SECOND_STEP: self.distribute_step_2,
        }

        return distribute_map[self.distribute_step]()


def kernels_distribute(cycle, step):
    kd = KernelsDistribute.from_files(cycle, step=step)
    kd.distribute()
