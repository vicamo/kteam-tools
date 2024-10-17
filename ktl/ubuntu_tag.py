"""
@file ubuntu_tags.py
@brief Ubuntu flavored git tags
@description
A canonical representation for git tags as used by Ubuntu kernel releases.
"""

import json
import re
from abc import abstractmethod
from typing import Any, List, Tuple
import apt_pkg

apt_pkg.init()


def _group_nth_int_get(match: re.match, group: int, default: Any = 0, raise_value_error: bool = False):
    """Returns match.group(n) or default on error
    :param match: Match object to extract group from
    :param group: Group index (1 base)
    :param default: Default return on error
    :param raise_type_error: True to raise exception on ValueError
    """
    try:
        return int(match.group(group))
    except TypeError:
        return default
    except ValueError as ex:
        if raise_value_error:
            raise ex
        return default


class _Comparable:
    @abstractmethod
    def compare(self, other: object):
        """Compare self to other
        :param object other: Object to compare to
        :returns:
            - <0: self <  other
            -  0: self == other
            - >0: self >  other
        :raises NotImplemented: if other is not _Comparable
        """

    def __eq__(self, other: object) -> bool:
        return self.compare(other) == 0

    def __ne__(self, other: object) -> bool:
        return self.compare(other) != 0

    def __lt__(self, other: object) -> bool:
        return self.compare(other) < 0

    def __gt__(self, other: object) -> bool:
        return self.compare(other) > 0

    def __le__(self, other: object) -> bool:
        return self.compare(other) <= 0

    def __ge__(self, other: object) -> bool:
        return self.compare(other) >= 0


class Version(_Comparable):
    """Version type in format X.Y[.Z]

    To avoid confusion with semver semantics we refer to the fields as
    x, y, z where z is optional and implicitly zero if not specified.
    :param raw: Version format using two or three fields
    :raises ValueError: When tag is invalid. Use :py:meth: `Version.from_str` to allow parsing to silently fail.
    """

    RE_VERSION = re.compile(r"^(\d+)\.(\d+)(?:\.(\d+))?$")

    def __init__(self, x: int, y: int, z: int = 0):
        self._x = x
        self._y = y
        self._z = z
        self._triplet: Tuple[int, int, int] = (x, y, z)

    @staticmethod
    def from_str(value: str, raise_on_error=False) -> "Version":
        """Helper for creating Version from string X.Y[.Z]
        TODO: Cannot use future annotations until 3.7+
        :param value: Raw value to parse
        :param raise_on_error: Raise ValueError if value cannot be parsed
        :raises ValueError: when raise_on_error is True and value cannot be parsed
        """
        result = None
        value = str(value)
        m = re.match(Version.RE_VERSION, value)
        if not m or not all(m.group(1, 2)):
            if raise_on_error:
                raise ValueError
        else:
            version = (
                _group_nth_int_get(m, 1),
                _group_nth_int_get(m, 2),
                _group_nth_int_get(m, 3),
            )
            result = Version(*version)
        return result

    @property
    def x(self) -> int:
        """
        :returns: First component of version
        """
        return self._x

    @property
    def y(self) -> int:
        """
        :returns: Second component of version
        """
        return self._y

    @property
    def z(self) -> int:
        """
        :returns: Last component of version
        """
        return self._z

    @property
    def triplet(self) -> Tuple[int, int, int]:
        """
        :returns: Complete version as integer tuple
        """
        return self._triplet

    def compare(self, other: object) -> int:
        """Compare self to other
        :param object other: Object to compare to
        :returns:
            - <0: self <  other
            -  0: self == other
            - >0: self >  other
        :raises NotImplemented: if other is not Version
        """
        ret = None
        if not isinstance(other, Version):
            ret = NotImplemented
        elif other is None:
            ret = 1
        elif self.x == other.x and self.y == other.y and self.z == other.z:
            ret = 0
        elif self.x > other.x:
            ret = 1
        elif self.x < other.x:
            ret = -1
        elif self.y > other.y:
            ret = 1
        elif self.y < other.y:
            ret = -1
        elif self.z > other.z:
            ret = 1
        else:
            ret = -1
        return ret

    def __hash__(self) -> int:
        return hash(self.triplet)

    def __str__(self) -> str:
        return ".".join(map(str, self.triplet))

    def __repr__(self) -> str:
        data = {"x": self._x, "y": self._y, "z": self._z}
        return json.dumps(data, indent=4)


class UbuntuTag(_Comparable):
    """Ubuntu kernel release tag

    Ubuntu[-package]-X.Y.Z[-.]abi.upload[.deb][_series][+extra]

    Where:
        - -package : Can repeat 0 or more times. This may contain -,.,a-z,0-9
        - X.Y.Z    : Kernel version. Z is always 0.
        - [-.]     : The meta package uses a dot separator. Dashes for everything else.
        - abi      : Always one or more digits
        - upload   : Always one or more digits
        - deb      : When present, will be >= 1
        - _series  : Identifies Ubuntu series in YY.MM[.R] format. Might include release (R) suffix.
        - +extra   : Arbitrary strings separated by + signs. Can be numeric or text.

    .. note:: Versions do not reflect semver semantics

    :param raw_tag: Git tag to parse
    :raises ValueError: When tag is invalid. Use :py:meth: `UbuntuTag.from_str` to allow parsing to silently fail.
    """

    RE_TAG = re.compile(
        r"""
    #
    # Ubuntu-foo-5.15-5.15.0-1062.65_20.04.1+cvm1.1+2
    #
    # 1. Kernel Version        -> 5.15.0
    (
        \d+\. # X              -> 5
        \d+\. # Y              -> 15
        0     # Z              -> 0
    )
    # Meta or default separator
    [\.-]
    # 2. Ubuntu Version        -> 1062.65
    (
        \d+\.         # ABI    -> 1062
        \d+           # Upload -> 65
        (?:\.\d+)?    # Debian -> 0
    )
    (?:_
        # 3. Series            -> 20.04.1
        (\d{2}\.\d{2}(?:\.\d+)?)
    )?
    # 4. Extra                -> +cvm1.2+2
    (
        # Non-regular syntax must be parsed manually
        \+.+
    )?
    """,
        re.VERBOSE | re.IGNORECASE,
    )

    RE_RESPIN = re.compile(
        r"""
        # Optional string prefix is ignored
        [a-zA-Z]*
        # 1. First digit
        (\d+)
        # 2. Optional second digit
        (?:\.(\d+))?
        # 3. Option third (and final) digit
        (?:\.(\d+))?
    """,
        re.VERBOSE | re.IGNORECASE,
    )

    def __init__(self, raw_tag: str):
        self._raw_tag = raw_tag
        self._package: str = ""
        self._kernel_version: Version = Version(0, 0, 0)
        self._ubuntu_version: Version = Version(0, 0, 0)
        self._series: str = ""
        self._extra: str = ""
        self._respin_version: Version = Version(0, 0, 0)
        self._raw_version: str = ""
        self._parse()

    @staticmethod
    def from_str(value: str, raise_on_error=False) -> "UbuntuTag":
        """Helper for creating UbuntuTag from a Git tag
        TODO: Cannot use future annotations until 3.7+
        :param value: Raw value to parse
        :param raise_on_error: Raise ValueError if value cannot be parsed
        :raises ValueError: when raise_on_error is True and value cannot be parsed
        """
        result = None
        try:
            result = UbuntuTag(value)
        except ValueError:
            if raise_on_error:
                raise
        return result

    @property
    def prefix(self) -> str:
        """
        :returns: Expected tag prefix
        """
        return "Ubuntu-"

    @property
    def raw_tag(self) -> str:
        """
        :returns: Original Git tag
        """
        return self._raw_tag

    @property
    def package(self) -> str:
        """
        :returns: Package name excluding self.prefix
        """
        return self._package

    @property
    def version(self) -> str:
        """
        :returns: Complete version
        """
        return self._raw_version

    @property
    def kernel_version(self) -> Version:
        """An orderable representation of the upstream kernel version
        :returns: Upstream kernel X.Y.Z as a Version
        """
        return self._kernel_version

    @property
    def ubuntu_version(self) -> Version:
        """An orderable representation of the Ubuntu version parts
        :returns: ABI.Upload.Debian as a Version
        """
        return self._ubuntu_version

    @property
    def abi(self) -> str:
        """
        :returns: ABI number
        """
        abi = self._ubuntu_version.x
        return abi

    @property
    def upload(self) -> str:
        """
        :returns: Upload number
        """
        upload = self._ubuntu_version.y
        return upload

    @property
    def debian(self) -> str:
        """
        :returns: Debian build number, usually 0
        """
        deb = self._ubuntu_version.z
        return deb

    @property
    def series(self) -> str:
        """Optional series may be appended after the Ubuntu version
        :returns: Series as a string, typically in the form YY.MM
        """
        return self._series

    @property
    def extra(self) -> List[str]:
        """All data after first occurrence of + as a list
        :returns: List of extra string delimited by +
        """
        extra = list(filter(None, self._extra.split("+")))
        return extra

    @property
    def respin(self) -> Version:
        """If not specified, will be 0.0.0
        :returns: Respin version
        """
        return self._respin_version

    def can_compare(self, other: object) -> bool:
        """Returns True if other is comparable to this"""
        result = True
        if not isinstance(other, UbuntuTag):
            result = False
        elif not self.package == other.package:
            result = False
        elif not self.kernel_version == other.kernel_version:
            result = False
        return result

    def compare(self, other: object) -> int:
        """Compare self to other
        :param object other: Object to compare to
        :returns:
            - <0: self <  other
            -  0: self == other
            - >0: self >  other
        :raises NotImplemented: if other is not UbuntuTag
        :raises ValueError: if other package is not equal to this package
        """
        if not isinstance(other, UbuntuTag):
            return NotImplemented
        if not self.package == other.package:
            raise ValueError(
                "Tags not from the same package, cannot compare. "
                + "Compare ubuntu_version properties directly if you know what you're doing."
            )

        ret = None
        if other is None:
            ret = 1
        elif self.raw_tag == other.raw_tag:
            ret = 0

        return apt_pkg.version_compare(self.version, other.version)

    def _parse(self):
        """Parse self into fields
        :raises ValueError: When tag is malformed
        """

        def throw(message):
            message = f"Invalid tag '{self.raw_tag}': {message}"
            raise ValueError(message)

        if not self.raw_tag:
            throw("Tag is empty")

        tag_name = self.raw_tag.split("/")[-1]
        if not tag_name:
            throw("Unable to extract tag name")

        #
        # Anchor to the kernel version because the package
        # name might contain a kernel version and the ubuntu
        # version might have 3 segments.
        match = re.search(self.RE_TAG, tag_name)
        if not match or not match.group(1):
            throw("Kernel version not found")
        try:
            self._kernel_version = Version.from_str(match.group(1), raise_on_error=True)
        except ValueError:
            throw(f"Invalid kernel version format in '{match.group(1)}'")

        #
        # Prefix is everything before the kernel version excluding
        # any leading or trailing dashes. We do not assigned semantic
        # value to this portion.
        prefix = tag_name[: match.start()]
        if not prefix.startswith(self.prefix):
            throw(f"Invalid tag prefix, expected '{self.prefix}")
        self._package = prefix.lstrip(self.prefix).strip("-")

        self._raw_version = tag_name[match.start() :]

        #
        # The Ubuntu version contains an ABI and upload number.
        # There may also be a Debian build number (group 8).
        if not match.group(2):
            throw("ABI and Upload number not found")
        try:
            self._ubuntu_version = Version.from_str(match.group(2), raise_on_error=True)
        except ValueError:
            throw(f"Invalid ABI.Upload format in '{match.group(2)}'")

        #
        # There might be a Ubuntu series designator
        if match.group(3):
            self._series = match.group(3)

        #
        # There might be some extra stuff too
        if match.group(4):
            self._parse_extra(match.group(4))

    def _parse_extra(self, extra: str):
        """Extra meaning from extra string
        :param extra: All data after first +, including + itself
        """
        self._extra = extra

        #
        # The extra portion is irregularly structured.
        # We interpret the final +NUMBER as the respin
        # version. All preceding values will be treated
        # an information strings.
        for part in extra.split("+"):
            match = re.search(self.RE_RESPIN, part)
            if not match:
                continue
            version = (
                _group_nth_int_get(match, 1),
                _group_nth_int_get(match, 2),
                _group_nth_int_get(match, 3),
            )
            self._respin_version = Version(*version)

    def __str__(self) -> str:
        return self.raw_tag

    def __repr__(self) -> str:
        data = {
            "raw_tag": self.raw_tag,
            "package": self.package,
            "kernel": str(self.kernel_version),
            "ubuntu": str(self.ubuntu_version),
            "abi": self.abi,
            "upload": self.upload,
            "deb": self.debian,
            "series": self.series,
            "extra": self.extra,
            "respin": str(self.respin),
        }
        return json.dumps(data, indent=4)
