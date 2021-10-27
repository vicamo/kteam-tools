import os
import yaml

# Secrets
#
class Secrets:

    # __init__
    #
    def __init__(self, path=None, user=None):
        self.path = path
        self.user = user

        secrets = {}
        if os.path.exists(self.path):
            with open(self.path) as rfd:
                secrets = yaml.safe_load(rfd)

        self.data = secrets

    def save(self):
        raise NotImplemented
