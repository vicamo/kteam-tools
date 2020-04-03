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

    def __init__(self, url=None, data=None, use_local=False):
        if data is None and url is None:
            url = self._url
        if url is not None and os.path.exists(url):
            url = urljoin('file:', pathname2url(os.path.realpath(url)))
        if data is None and url:
            response = urlopen(url)
            data = response.read()
            if not isinstance(data, str):
                data = data.decode('utf-8')

        self._data = yaml.safe_load(data)

    def __iter__(self):
        return iter(self._data)

    def items(self):
        return self._data.items()

    def __getitem__(self, *args, **kwargs):
        return self._data.__getitem__(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self._data.get(*args, **kwargs)
