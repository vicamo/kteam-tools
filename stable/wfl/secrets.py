import os
import yaml

# Secrets
#
class Secrets(object):

    # __init__
    #
    def __init__(self, config=None):
        defaults = {}
        paths = []
        if 'HOME' in os.environ:
            paths.append(os.path.join(os.environ['HOME'], '.swm-secrets.yaml'))
        paths.append(os.path.join(os.path.dirname(__file__), '.swm-secrets.yaml'))
        for path in paths:
            if os.path.exists(path):
                break

        secrets = {}
        if os.path.exists(path):
            with open(path) as rfd:
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
