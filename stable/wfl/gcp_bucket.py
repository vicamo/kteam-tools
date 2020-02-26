#
# gcp-bucket -- interrogate GCP object store for object info.
#
try:
    from urllib.request         import urlopen, Request, ProxyHandler, build_opener, install_opener
    from urllib.error           import URLError, HTTPError
except ImportError:
    from urllib2                import urlopen, Request, URLError, HTTPError, ProxyHandler, build_opener, install_opener

import json
from wfl.errors                 import ShankError
from wfl.log                    import center, cleave, cinfo, cdebug


# GcpBucketError
#
class GcpBucketError(ShankError):
    """
    Thrown when something goes wrong with the GCP bucket.
    """
    pass


# GcpBucketObject
#
class GcpBucketObject:
    """
    A helper class to handle GCP bucket operations.
    """

    # __init__
    #
    def __init__(self, bucket, obj, prefix=False):
        """
        :param url: GCP bucket object url
        """
        center(self.__class__.__name__ + '.__init__')

        if prefix:
            obj = '?prefix=' + obj

        url = 'https://www.googleapis.com/storage/v1/b/{bucket}/o/{object}'.format(bucket=bucket, object=obj)

        cdebug("url={}".format(url))
        self.url = url
        self._present = True

        try:
            # XXX: this should be a separate function which returns an opener
            #      with proxy if the object is _external_.
            opener = build_opener(ProxyHandler({'https': 'https://squid.internal:3128/'}))
            req = Request(url)
            with opener.open(req) as resp:
                self._data = json.loads(resp.read().decode('utf-8'))
            if prefix:
                items = self._data.get('items', [])
                if len(items) > 0:
                    self._data = items[0]
                else:
                    self._present = False
        except HTTPError as e:
            if hasattr(e, 'code') and e.code == 404:
                self._data = json.loads(e.read().decode('utf-8'))
                self._present = False
            else:
                raise GcpBucketError(str(e))
        except URLError as e:
            raise GcpBucketError(str(e))

        cleave(self.__class__.__name__ + '.__init__')

    @property
    def present(self):
        return self._present
