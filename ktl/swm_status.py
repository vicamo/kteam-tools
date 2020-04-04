try:
    from urllib.request import pathname2url, urljoin, urlopen

except ImportError:
    from urllib2 import pathname2url, urljoin, urlopen

import argparse
import os
import sys
import yaml


# SwmStatus
#
class SwmStatus:
    _url = 'https://kernel.ubuntu.com/~kernel-ppa/status/swm/status.yaml'

    def __init__(self, url=None, path=None, data=None, use_local=False):
        if data is None and url is None:
            url = self._url
        if data is None and path is not None and os.path.exists(path):
            with open(path) as sfd:
                data = sfd.read()
        if data is None and url is not None:
            response = urlopen(url)
            data = response.read()

        if isinstance(data, bytes):
            data = data.decode('utf-8')
        if isinstance(data, str):
            data = yaml.safe_load(data)

        if not isinstance(data, dict):
            raise ValueError("expecting to construct a dictionary")

        self._data = data

    @property
    def trackers(self):
        return self._data.get('trackers', self._data)
