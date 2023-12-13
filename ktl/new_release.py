#
# ktl/new_release.py: Provides a KernelVersion object that allows to bump
#  Ubuntu kernel package versions according to the following rules.
#
#  For main package versions:
#
#  1) Upstream and debian versions are split with a dash. That means meta
#     packages are not supported.
#  2) Debian version is formatted as ABI.UPLOAD(EXTRA) or ABI.UPLOAD(EXTRA),
#     where the parentheses are only for separation. ABI and UPLOAD are only
#     digits, EXTRA may be anything else that is allowed in a debian version,
#     starting with a non-digit (in most cases, a ~ or a +), and ending with
#     a sequence of digits.
#  3) The EXTRA part is optional, and when it exists and no parent version is
#     given, bumping the version means bumping the last digits part of EXTRA.
#  4) When there is no EXTRA, bumping means incrementing both ABI and UPLOAD,
#     no matter if a parent is given.
#  5) When there is EXTRA and a parent is given, if the parent version matches
#     the given version without the EXTRA part, then 3 is followed. If it does
#     not match, the new version is the parent version plust the EXTRA part with
#     its last digits reset to 1.
#
#  For linux-restricted-modules (aka LRM) package versions:
#
#   If the current LRM version is:
#    1) less than the parent version, use the parent version.
#    2) equal to the parent version, use the parent version with a '+1' suffix.
#    3) greater than the parent version, use the current version and bump the
#       suffix by one.
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

# ABI.UPLOAD(EXTRA)
RE_ABI = re.compile("(\d+)\.(\d+)(.*)")

# .*NUM
RE_EXTRA = re.compile("(.*[^\d])(\d+)")


class KernelVersion:
    def __init__(self, version, parent_version=None, package_type=None):
        self.version = version
        self.parent_version = parent_version
        self.package_type = package_type if package_type else "main"
        apt_pkg.init()

    def __eq__(self, other):
        return self.version == other.version

    def __str__(self):
        return self.version

    def _bump_main(self):
        """Bump main package version"""
        try:
            upstream, debian = self.version.split("-")
            m = re.search(RE_ABI, debian)
            abi = m.group(1)
            upload = m.group(2)
            extra = m.group(3)

            if not extra:
                abi = int(abi) + 1
                upload = int(upload) + 1
                self.version = "{}-{}.{}".format(upstream, abi, upload)
            else:
                m = re.search(RE_EXTRA, extra)
                extra_prefix = m.group(1)
                extra_digit = m.group(2)
                if not self.parent_version or self.parent_version + extra == self.version:
                    extra_digit = int(extra_digit) + 1
                else:
                    extra_digit = 1
                extra = "{}{}".format(extra_prefix, extra_digit)
                if self.parent_version:
                    self.version = "{}{}".format(self.parent_version, extra)
                else:
                    self.version = "{}-{}.{}{}".format(upstream, abi, upload, extra)
        except Exception:
            raise ValueError("Invalid version")

    def _bump_lrm(self):
        """Bump lrm package version"""
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
            # In this case, it is expected that the LRM version has a '+X' suffix and
            # the base version without the suffix is identical to the parent version
            if "+" not in self.version:
                raise ValueError("Invalid version: {}".format(self.version))
            base, X = self.version.rsplit("+", 1)
            if base != self.parent_version:
                raise ValueError("Invalid version: {}".format(self.version))
            self.version = "{}+{}".format(self.parent_version, int(X) + 1)

    def bump(self):
        """Bump package version"""
        if self.package_type == "main":
            self._bump_main()
        elif self.package_type == "lrm":
            self._bump_lrm()
        else:
            raise ValueError("Invalid package type: {}".format(self.package_type))
