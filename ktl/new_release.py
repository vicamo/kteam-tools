#
# ktl/new_release.py: Provides a KernelVersion object that allows to bump
#  Ubuntu kernel package versions according to the following rules.
#
#  For main package versions:
#
#  1) Upstream and debian versions are split with a dash. That means meta
#     packages are not supported.
#  2) Debian version is formatted as ABI.UPLOAD, ABI.UPLOAD(EXTRA), or
#     ABI.UPLOAD(.SPUN)(EXTRA) where the parentheses are only for separation.
#     ABI, UPLOAD and SPUN (sameport upload number) are only digits, EXTRA
#     may be anything else that is allowed in a debian version, starting with
#     a non-digit (in most cases, a ~ or a +), and ending with a sequence of
#     digits.
#  3) The SPUN part is optional and only exists for sameport package versions.
#  4) The EXTRA part is optional, and when it exists and no parent version is
#     given, bumping the version means bumping the last digits part of EXTRA.
#  5) When there is no EXTRA, bumping means incrementing both ABI and UPLOAD,
#     no matter if a parent is given.
#  6) When there is EXTRA and a parent is given, if the parent version matches
#     the given version without the EXTRA part, then 3 is followed. If it does
#     not match, the new version is the parent version plust the EXTRA part with
#     its last digits reset to 1.
#  7) EXCEPTION: when parent version is lower than the given version, ABI and
#     UPLOAD are incremented and EXTRA last digit is reset to 1.
#
#  For linux-restricted-modules (aka LRM), linux-signed and linux-meta (see
#  WARNING below) package versions:
#
#   If the current package version is:
#    1) less than the parent version, use the parent version.
#    2) equal to the parent version, use the parent version with a '+1' suffix.
#    3) greater than the parent version, use the current version and bump the
#       suffix by one.
#
#  WARNING:
#   Starting with Noble, linux-meta packages use the same versioning rules as
#   LRM and linux-signed packages as desribed above. Before Noble, linux-meta
#   package versions are native versions (no '-') and follow these rules:
#    1) If the current ABI if less than the parent ABI, use the parent ABI and
#       append the bumped current upload number.
#    2) If the current ABI is equal to the parent ABI, simply bump the upload
#       number.
#
#  NOTE: The point of the library is to be simple, not to validate the versions.
#   So, this does not currently:
#    1) Validate upstream version.
#    2) Validate that the version is a valid debian version.
#    3) Validate the parent version.
#
#  If bugs turn out because of those missing features, they can be added.
#
# Copyright (C) 2023, Canonical Ltd.
#
# This script is distributed under the terms and conditions of the GNU General
# Public License, Version 3 or later. See http://www.gnu.org/copyleft/gpl.html
# for details.

import re
import apt_pkg

apt_pkg.init()

# UPSTREAM-ABI.UPLOAD(.SPUN)(EXTRA DIGIT)
RE_VERSION = re.compile(r"([^-]+)-(\d+)\.(\d+)(\.\d+(?=[^\d]))?(?:(.*[^\d])(\d+))?")
# However the (.SPUN) is only needed to correctly identify the
# base version of sameport backports.
# Eg. in 6.5.0-27.28.1~22.04.1 where 6.5.0-27.28.1 is the base version,
# (SPUN) matches the .1 and (EXTRA DIGIT) matches the ~22.04.1.
# For plain sameports, eg. 6.5.0-27.28.1, the SPUN .1 is matched
# by (EXTRA DIGIT) and handled like any other extra bits added to
# the base version 6.5.0-27.28

# *[-~+]NUM.NUM.NUM
RE_OLD_BP_FP_VERSION = re.compile(r".*[-~+]\d+\.\d+\.\d+")


class KernelVersion:
    def __init__(self, version, parent_version=None, package_type=None):
        self.version = version
        self.parent_version = parent_version
        self.package_type = package_type if package_type else "main"

    def __eq__(self, other):
        return self.version == other.version

    def __str__(self):
        return self.version

    def __repr__(self):
        return "KernelVersion({})".format(self.version)

    def _bump_main(self, abi_gap):
        """Bump main package version"""
        m = re.fullmatch(RE_VERSION, self.version)
        if not m:
            raise ValueError("Invalid version {}".format(self.version))

        upstream, abi, upload, sameport, extra, digit = m.group(1, 2, 3, 4, 5, 6)
        if not extra:
            self.version = "{}-{}.{}".format(upstream, int(abi) + abi_gap, int(upload) + abi_gap)
            return

        base = "{}-{}.{}{}".format(upstream, abi, upload, sameport or "")
        parent = self.parent_version or base
        cmp = apt_pkg.version_compare(parent, base)
        if cmp < 0:
            self.version = "{}-{}.{}{}1".format(upstream, int(abi) + abi_gap, int(upload) + abi_gap, extra)
        elif cmp > 0:
            self.version = "{}{}1".format(parent, extra)
        else:
            self.version = "{}{}{}".format(parent, extra, int(digit) + 1)

    def _bump_lrm_signed_meta(self):
        """Bump lrm, signed or meta package version"""
        if not self.parent_version:
            raise ValueError("Invalid parent version: {}".format(self.parent_version))

        res = apt_pkg.version_compare(self.version, self.parent_version)
        if res < 0:
            # version < parent_version
            self.version = self.parent_version
        elif res == 0:
            # version == parent_version
            self.version = "{}+1".format(self.parent_version)
        else:
            # version > parent_version
            # In this case, it is expected that the package version has a '+X' suffix and
            # the base version without the suffix is identical to the parent version
            if "+" not in self.version:
                raise ValueError("Invalid version: {}".format(self.version))
            base, X = self.version.rsplit("+", 1)
            if base != self.parent_version:
                raise ValueError("Invalid version: {}".format(self.version))
            self.version = "{}+{}".format(self.parent_version, int(X) + 1)

    def _bump_meta_old(self):
        """Bump old meta package version (pre Noble)"""
        if not self.parent_version:
            raise ValueError("Invalid parent version: {}".format(self.parent_version))

        if RE_OLD_BP_FP_VERSION.fullmatch(self.parent_version):
            # Backport (~yy.mm.X), forwardport (+yy.mm.X) package or sameport version schema.
            # Bump the last digit (X) if the base version (everything before the last '.')
            # is equal to the parent's base, otherwise use the parent's base and reset the
            # last digit to 1.
            base, X = self.version.rsplit(".", 1)
            parent_base = self.parent_version.replace("-", ".").rsplit(".", 1)[0]
            if base == parent_base:
                X = int(X) + 1
            else:
                X = 1
            self.version = "{}.{}".format(parent_base, X)
            return

        comps = self.version.split(".", 4)
        parent_comps = self.parent_version.replace("-", ".").split(".")

        # Use the parent's ABI and append the bumped current package upload number
        # We deliberately don't do any checking so that we get a hard failure if
        # the version is unexpected
        parent_abi = ".".join(parent_comps[0:4])
        self.version = "{}.{}".format(parent_abi, int(comps[-1]) + 1)

    def bump(self, abi_gap=None):
        """Bump package version"""
        abi_gap = 1 if abi_gap is None else int(abi_gap)
        prev_version = self.version
        if self.package_type == "main":
            self._bump_main(abi_gap=abi_gap)
        elif self.package_type in ("lrm", "signed"):
            self._bump_lrm_signed_meta()
        elif self.package_type == "meta":
            if "-" in self.version:
                self._bump_lrm_signed_meta()
            else:
                self._bump_meta_old()
        else:
            raise ValueError("Invalid package type: {}".format(self.package_type))

        # Sanity check: The new version needs to be greater
        if apt_pkg.version_compare(prev_version, self.version) >= 0:
            raise ValueError("Version bump failure")
