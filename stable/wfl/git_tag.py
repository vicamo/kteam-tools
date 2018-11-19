try:
    from urllib.request         import urlopen, Request, ProxyHandler, build_opener, install_opener
    from urllib.error           import URLError, HTTPError
    from urllib.parse           import quote_plus
except ImportError:
    from urllib2                import urlopen, Request, URLError, HTTPError, ProxyHandler, build_opener, install_opener, quote_plus

from wfl.errors                 import ShankError
from wfl.log                    import center, cleave, cinfo, cdebug

# GitTagError
#
class GitTagError(ShankError):
    """
    Thrown when something goes wrong with the GIT tag lookup.
    """
    pass

# GitTag
#
class GitTag():
    '''
    Handle finding and validating git tags based on the backend.
    '''
    # __init__
    #
    def __init__(self, package, version):
        center(self.__class__.__name__ + '.__init__')

        self.package = package
        self.version = version

        self.verifiable = False
        self._present = False

        if package.repo is not None and package.repo.url is not None:
            tag = 'Ubuntu{}-{}'.format(
                package.source.name.replace('linux', ''),
                version.replace('~', '_'))
            cdebug('pkg name: {}'.format(package.source.name))
            cdebug('versions: {}'.format(version))
            cdebug('tag key : {}'.format(tag))

            url = package.repo.url
            if url.startswith("git://git.launchpad.net"):
                self.verifiable = True

                url = url.replace('git:', 'https:') + "/tag/?id={}".format(quote_plus(tag))
                self.dbg_url = url
                try:
                    # XXX: this should be a separate function which returns an opener
                    #      with proxy if the object is _external_.
                    opener = build_opener(ProxyHandler())
                    req = Request(url)
                    with opener.open(req) as resp:
                        self._data = resp.read().decode('utf-8')

                    self._present = not "<div class='error'>" in self._data

                except (HTTPError, URLError) as e:
                    raise GitTagError(str(e))

    @property
    def present(self):
        return self._present
