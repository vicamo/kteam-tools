import os
import sys
import warnings
import yaml
import xdg

from dataclasses import dataclass
from typing import Optional, Self


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


class Config:
    def __init__(self, filename=None, data=None):
        filename = os.getenv("CRANKY_CONFIG_FILE", filename)

        if filename is not None and data is not None:
            raise ValueError("supply only one of filename and data")

        if data is None and filename is None:
            config_path = ConfigPath.find()
            if config_path is not None:
                filename = config_path.path

                if config_path.is_obsolete:
                    warn = True
                    warnings.warn(
                        "Using config file {}. You need to move it to {} to prevent this warning".format(
                            filename, ConfigPath.default()
                        )
                    )

        if data is None and filename is not None and os.path.exists(filename):
            with open(filename) as yfd:
                data = yfd.read()

        if data is not None:
            data = yaml.safe_load(data)

        if data is None:
            print("Missing configuration, using default config.")
            warn = True
            data = {}
            data["base-path"] = "~/canonical/kernel/ubuntu"
            data["package-path"] = {"default": "{series}/linux{type_suffix}"}

        self.config = data

        # Warn if old/deprecated config options are found
        # fmt: off
        warn = False
        if self.lookup("package-path.base-path", None) is not None:
            warn = True
            print("Deprecated 'package-path.base-path' option found in cranky config file.",
                  file=sys.stderr)
            print("You should rename it to 'base-path'.", file=sys.stderr)
        if self.lookup("test-build.logdir", None) is not None:
            warn = True
            print("Deprecated 'test-build.logdir' option found in cranky config file.",
                  file=sys.stderr)
            print("You should rename it to 'test-build.log-path' and make it relative to 'base-path'.",
                  file=sys.stderr)
        if warn:
            print("Check the config example in kteam-tools/cranky/docs/snip-cranky.yaml for more information.",
                  file=sys.stderr)
        # fmt: on

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
