import os
import json
import yaml

from urllib.request import urlopen


class SigningConfigStreamLevel:
    def __init__(self, stream, level, variant, reference):
        self.stream = stream
        self.level = int(level)
        self.variant = variant

        self.reference = reference

    @property
    def archive_reference(self):
        if self.reference is None:
            return None
        return "ppa:canonical-signing/ubuntu/" + self.reference


class SigningConfig:
    def __init__(self, url=None, data=None, use_local=os.getenv("USE_LOCAL_SIGNING_CONFIG", False)):
        self._url = "https://kernel.ubuntu.com/info/signing-config.yaml"
        try:
            import ckt_info

            _local = ckt_info.abspath("info/signing-config.yaml")
        except ImportError:
            _local = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "info", "signing-config.yaml"))
        self._url_local = "file://" + _local

        if data is None:
            if url is None:
                url = self._url_local if use_local else self._url
            # print("URL", url)
            if url.startswith("file://"):
                with open(url[7:], "rb") as lfd:
                    data = lfd.read()
            else:
                response = urlopen(url)
                data = response.read()
            if isinstance(data, bytes):
                data = data.decode("utf-8")

        if isinstance(data, dict):
            self._data = data

        elif data.startswith("{"):
            self._data = json.loads(data)

        else:
            self._data = yaml.safe_load(data)

        # Instantiate any simple mappings as direct mappings.
        if "streams" in self._data:
            for stream, stream_data in self._data["streams"].items():
                for level, level_data in list(stream_data.items()):
                    if isinstance(level_data, str):
                        stream_data[level] = {stream: level_data}

        self._streams = self._data.get("streams", {})

    def lookup_stream(self, stream_level):
        if "/" not in stream_level:
            raise ValueError("Invalid stream/level format")
        stream, level = stream_level.split("/", 1)
        if "+" in level:
            level, variant = level.split("+")

        elif ":" in level:
            level, variant = level.split(":")

        elif "/" in level:
            variant, level = level.split("/")

        else:
            variant = stream

        return SigningConfigStreamLevel(
            stream, level, variant, self._streams.get(stream, {}).get(int(level), {}).get(variant)
        )
