import re

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


# GitRemote
#
class GitRemote:

    # __init__
    #
    def __init__(self, url):
        center(self.__class__.__name__ + '.__init__')

        self.url = url
        self._refs = None
        self._hashes = None

        cleave(self.__class__.__name__ + '.__init__')

    def cache_refs(self, url):
        center(self.__class__.__name__ + '.cache_refs')
        cdebug('url     : {}'.format(url))

        cmd = ['git', 'ls-remote', url]
        #print('  CMD: ' + ' '.join(cmd))
        proc = Popen(cmd, stdout=PIPE)
        refs = {}
        hashes = {}
        for entry in proc.stdout:
            bits = entry.decode('utf-8').split()
            if bits[1].endswith('^{}'):
                bits[1] = bits[1][:-3]
            refs.setdefault(bits[1], []).append(bits[0])
            hashes.setdefault(bits[0], []).append(bits[1])
        retcode = proc.wait()
        if retcode != 0:
            raise CalledProcessError(proc.returncode, proc.args,
                proc.stdout, proc.stderr)

        self._refs = refs
        self._hashes = hashes
        cleave(self.__class__.__name__ + '.cache_refs')

    @property
    def refs(self):
        if self._refs is None:
            self.cache_refs(self.url)
        return self._refs

    @property
    def hashes(self):
        if self._hashes is None:
            self.cache_refs(self.url)
        return self._hashes


class GitTagsSnap:

    def __init__(self, snap):
        self.snap = snap

        self._tip_tag = False
        self._tip_version = False
        self._tag_prefix = False

        self.remote = None
        if self.snap.repo is not None:
            self.remote = GitRemote(self.snap.repo.url)

    prefix_version_re = re.compile('^(.*-)([0-9.]+-[0-9._]+)$')
    def analyse_tip(self):
        if self.remote is None:
            return None

        # Mark this as attempted.
        self._tip_tag = None
        self._tip_version = None
        self._tag_prefix = None

        # Find the hash at the tip.
        tip_name = 'refs/heads/' + self.snap.repo.branch
        tip_hash = self.remote.refs.get(tip_name)
        if tip_hash is None:
            return
        tip_hash = tip_hash[0]

        # See if there are any other refs pointing to that.  If there
        # is extract the tag prefix and current version from the tag.
        for ref_name, ref_hash in self.remote.refs.items():
            #print(tip_name, tip_hash, ref_name, ref_hash)
            if ref_name != tip_name and tip_hash in ref_hash:
                self._tip_tag = ref_name
                pv_match = self.prefix_version_re.search(ref_name)
                if pv_match is not None:
                    self._tag_prefix = pv_match.group(1)
                    self._tip_version = pv_match.group(2).replace('_', '~')

        cdebug("tip_name<{}> tip_hash<{}> tip_tag<{}> tag_prefix<{}> tip_version<{}>".format(tip_name, tip_hash, self._tip_tag, self._tag_prefix, self._tip_version))

    @property
    def tag_prefix(self):
        if self._tag_prefix is False:
            self.analyse_tip()
        return self._tag_prefix

    @property
    def tip_tag(self):
        if self._tip_tag is False:
            self.analyse_tip()
        return self._tip_tag

    @property
    def tip_version(self):
        if self._tip_version is False:
            self.analyse_tip()
        return self._tip_version

    def lookup_version(self, version):
        if self.tag_prefix is None:
            return None
        tag_name = self.tag_prefix + version.replace('~', '_')
        return self.remote.refs.get(tag_name)
