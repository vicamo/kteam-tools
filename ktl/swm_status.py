try:
    from urllib.request import pathname2url, urljoin, urlopen

except ImportError:
    from urllib2 import pathname2url, urljoin, urlopen

import argparse
import json
import os
import sys
from datetime import datetime


# SwmStatus
#
class SwmStatus:
    _url = 'https://kernel.ubuntu.com/~kernel-ppa/status/swm/status.json'

    def _json_object_decode(self, obj):
        isoformat = obj.get('_isoformat')
        if isoformat is not None:
            #return datetime.fromisoformat(isoformat)
            # XXX: before python 3.6 fromisoformat is not available.
            if isoformat[-3] == ':':
                isoformat = isoformat[0:-3] + isoformat[-2:]
            for fmt in (
                    '%Y-%m-%dT%H:%M:%S.%f%z',
                    '%Y-%m-%dT%H:%M:%S%z',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S'):
                try:
                    obj = datetime.strptime(isoformat, fmt)
                    break
                except ValueError:
                    pass
            else:
                raise ValueError("isoformat: {} invalid format".format(isoformat))
        return obj

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
            data = json.loads(data, object_hook=self._json_object_decode)

        if not isinstance(data, dict):
            raise ValueError("expecting to construct a dictionary")

        self._data = data

    @property
    def trackers(self):
        return self._data.get('trackers', self._data)
