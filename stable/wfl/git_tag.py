from subprocess                 import Popen, PIPE, run

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
    def __init__(self, package, version, sloppy=None):
        center(self.__class__.__name__ + '.__init__')

        self.package = package
        self.version = version

        self._verifiable = False
        self._present = False

        if package.repo is not None and package.repo.url is not None:
            url = package.repo.url
            self._refs = self.cache_tags(url)

            tag_prefix = 'Ubuntu{}-'.format(
                package.source.name.replace('linux', ''))
            version_encoded = version.replace('~', '_')

            cdebug('pkg name: {}'.format(package.source.name))
            cdebug('version : {}'.format(version))

            # Handle the various tag form exceptions we have gained over the
            # years.
            prefixes = [tag_prefix]
            if '-edge' in tag_prefix:
                prefixes.append(tag.replace('-edge', ''))
            if '-lts-' in tag_prefix:
                prefixes.append('Ubuntu-lts-')
            for tag_prefix in prefixes:
                tag_prefix = 'refs/tags/' + tag_prefix
                tag = '{}{}'.format(tag_prefix, version_encoded)
                found = None
                for ref in self._refs:
                    if ref == tag or (sloppy is not None and ref.startswith(tag + sloppy)):
                        found = ref
                if found:
                    self._present = True
                    self.version = found[len(tag_prefix):].replace('_', '~')
                    break

        cleave(self.__class__.__name__ + '.__init__')

    def cache_tags(self, url):
        center(self.__class__.__name__ + '.cache_tags')
        cdebug('url     : {}'.format(url))

        refs = []
        if url.startswith("git://git.launchpad.net"):
            cmd = [ 'git', 'ls-remote', '--refs', url ]
            result = run(cmd, stdout=PIPE, stderr=PIPE)
            if result.returncode != 0:
                raise GitTagError(result.stderr.decode('utf-8').strip())

            self._verifiable = True

            for line in result.stdout.decode('utf-8').split('\n'):
                if '\t' not in line:
                    continue
                (sha, ref) = line.split('\t')
                refs.append(ref)

        cleave(self.__class__.__name__ + '.lookup_tag')
        return refs

    @property
    def verifiable(self):
        return self._verifiable

    @property
    def present(self):
        return self._present
