import os
import sys
import warnings
import yaml
import xdg

from dataclasses import dataclass
from typing import Optional, Self, Dict


@dataclass
class ConfigPath:
    path: str
    is_obsolete: bool

    @staticmethod
    def default() -> str:
        """Return the default configuration file path."""
        return os.path.join(xdg.XDG_CONFIG_HOME, "cranky", "cranky.yaml")

    @classmethod
    def find(cls) -> Optional[Self]:
        """Find a configuration file, eventually obsolete."""
        path = ConfigPath.default()
        if os.path.exists(path):
            return cls(path, False)

        obsolete_paths = (
            os.path.join(os.environ["HOME"], ".config", "cranky", "cranky.yaml"),
            os.path.join(os.environ["HOME"], ".cranky.yaml"),
            os.path.join(os.environ["HOME"], ".cranky"),
        )

        try:
            return cls(
                next(p for p in obsolete_paths if os.path.exists(p)),
                True,
            )
        except StopIteration:
            return None


@dataclass
class Config:
    config: Dict

    def __post_init__(self):
        self.warn_deprecated_options()

    @classmethod
    def default(cls):
        """Load the default configuration.

        The configuration is loaded in order from:

        1. The filename provided in the CRANKY_CONFIG_FILE env var;
        3. One of the possible ConfigPath filenames
        4. The default configuration

        """
        filename = os.getenv("CRANKY_CONFIG_FILE", None)

        if filename is not None:
            return cls.from_filename(filename)

        config_path = ConfigPath.find()
        if config_path is not None:
            filename = config_path.path

            if config_path.is_obsolete:
                warnings.warn(
                    "Using config file {}. You need to move it to {} to prevent this warning".format(
                        filename, ConfigPath.default()
                    )
                )

        return cls.from_filename(filename)

    @classmethod
    def from_filename(cls, filename: Optional[str] = None):
        """Load config from filename, or default config if None."""
        yaml_data = None

        if filename is not None and os.path.exists(filename):
            with open(filename) as yfd:
                yaml_data = yfd.read()

        return cls.from_yaml(yaml_data)

    @classmethod
    def from_yaml(cls, yaml_data: Optional[str]) -> Self:
        """Load config from YAML data, or default config if None."""
        data = None
        if yaml_data is not None:
            data = yaml.safe_load(yaml_data)

        if data is None:
            print("Missing configuration, using default config.")
            data = {}
            data["base-path"] = "~/canonical/kernel/ubuntu"
            data["package-path"] = {"default": "{series}/linux{type_suffix}"}

        return cls(data)

    def warn_deprecated_options(self):
        """Warn if old/deprecated config options are found."""
        deprecated_option_found = False

        def warn(s):
            print(s, file=sys.stderr)

        if self.lookup("package-path.base-path", None) is not None:
            deprecated_option_found = True
            warn("Deprecated 'package-path.base-path' option found in cranky config file.")
            warn("You should rename it to 'base-path'.")

        if self.lookup("test-build.logdir", None) is not None:
            deprecated_option_found = True
            warn("Deprecated 'test-build.logdir' option found in cranky config file.")
            warn("You should rename it to 'test-build.log-path' and make it relative to 'base-path'.")

        if deprecated_option_found:
            warn("Check the config example in kteam-tools/cranky/docs/snip-cranky.yaml for more information.")

    def lookup(self, element, default=None):
        config = dict(self.config)

        element = element.split(".")
        while len(element) > 0:
            if not config:
                return default
            config = config.get(element.pop(0))
        if not config:
            return default
        return config
