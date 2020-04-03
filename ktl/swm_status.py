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

    @property
    def trackers(self):
        return self._data.get('trackers', self._data)
