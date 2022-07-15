import os
import yaml

# Secrets
#
class Secrets:

    # __init__
    #
    def __init__(self, config=None):
        secrets = {}
        if os.path.exists(config):
            with open(config) as rfd:
                secrets = yaml.safe_load(rfd)

        self._data = secrets

    def __iter__(self):
        return iter(self._data)

    def items(self):
        return self._data.items()

    def __getitem__(self, *args, **kwargs):
        return self._data.__getitem__(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._data.get(*args, **kwargs)
