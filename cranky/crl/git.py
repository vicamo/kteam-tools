import os
import sys
from subprocess import run, PIPE

# Add .. to the Python search path (allows to run pydoc3 on this file)
lib_path = os.path.dirname(__file__)
sys.path.append(os.path.realpath(os.path.join(lib_path, os.pardir)))

# Add ../libs to the Python search path
sys.path.append(os.path.realpath(os.path.join(lib_path, os.pardir, 'libs')))

try:
    from crl.handle import Handle, HandleError
    from ktl.log import cnotice, cwarn
except ImportError as e:
    print("Failed to import internal libraries:", e)
    sys.exit(1)


class GitError(Exception):
    pass


class GitDirectory():
    def __init__(self, directory):
        self.directory = directory

    def is_valid(self):
        if os.path.exists(self.directory):
            if os.path.exists(os.path.join(self.directory, '.git')):
                return True
            elif os.path.exists(os.path.join(self.directory, 'objects')):
                return True
        return False


class GitHandle():
    '''
    A handle to a single git repository.
    '''
    def __init__(self, handle_tree):
        self.__ht = handle_tree

    @property
    def directory(self):
        return self.__ht.directory

    @property
    def package(self):
        return self.__ht.package

    @property
    def remote(self):
        return self.__ht.remote

    @property
    def remote_branch(self):
        pkg = self.__ht.package

        return pkg.repo.branch if pkg.repo.branch else 'master'

    def is_valid(self):
        '''
        Returns whether the embedded directory seems to be a valid git repository
        '''
        return GitDirectory(self.directory).is_valid

    def is_clean(self):
        repo_dir = self.directory

        if not os.path.exists(os.path.join(repo_dir, '.git')):
            return True
        result = run(["git", "diff", "--quiet", "HEAD"], cwd=repo_dir)

        return result.returncode == 0

    def is_ancestor(self, old_sha1, new_sha1):
        result = run(["git", "merge-base", "--is-ancestor", old_sha1, new_sha1],
                     cwd=self.directory)
        return result.returncode == 0

    def lookup_ref(self, ref):
        '''
        Return the commit id from a reference.
        '''
        repo_dir = self.directory

        result = run(["git", "for-each-ref", "--format", "%(objectname)", ref],
                     cwd=repo_dir, stdout=PIPE)
        if result.returncode != 0:
            raise GitError("git for-each-ref failed rc={}".format(result.returncode))

        sha1 = result.stdout.decode('utf-8').strip()
        if sha1 == '':
            sha1 = None

        return sha1

    def get_cranky_branch_name(self):
        '''
        Return the local branch name which is used by cranky.
        '''
        pkg    = self.package
        remote = self.remote

        # Cranky branch is the real branch name if we are checking out against 'origin',
        # the derivative's source name otherwise.
        branch_suffix = pkg.repo.branch if pkg.repo.branch else 'master'
        if remote != 'origin':
            branch_suffix = pkg.source.name.replace('linux-', '')

        return 'cranky/' + branch_suffix

    def get_url(self):
        '''
        Returns a suitable URL which allows checkout/push for the given package.
        For this the prefix might be changed from 'git://' to 'ssh+git://'.
        FIXME: Potentially something that belongs into kernel_series.py
        '''
        pkg  = self.package
        repo = pkg.repo

        # Private sources or sources under ESM have to be accessed via ssh
        # and a username. We use the generic form here which works as long
        # as the launchpad user matches the local username. Otherwise this
        # needs a mapping like this in git config:
        #  [url "git+ssh://<user>@git.launchpad.net/"]
        #      insteadof = "git+ssh://git.launchpad.net"
        if pkg.source.private or pkg.series.esm:
            repo_url = repo.url.replace('git://', 'git+ssh://', 1)
        else:
            repo_url = repo.url

        return repo_url

    def checkout(self, remote, rmt_branch, branch):
        rmt_ref = 'refs/remotes/{}/{}'.format(remote, rmt_branch)
        lcl_ref = 'refs/heads/{}'.format(branch)

        # Get us onto the branch in question -- if it does not exists
        # git checkout -b branch remote/branch else
        # git checkout branch
        lcl_sha1 = self.lookup_ref(lcl_ref)
        if lcl_sha1 is None:
            cmd = ["git", "checkout", "-q", "-b", branch, rmt_ref]
        else:
            cmd = ["git", "checkout", "-q", branch]
        result = run(cmd, cwd=self.directory)
        if result.returncode != 0:
            raise GitError("git checkout failed rc={}".format(result.returncode))

        # If the new upstream branch does not match ours we need
        # to reset the branch.  Firstly back it up in case it is not
        # fully merged upstream.
        rmt_sha1 = self.lookup_ref(rmt_ref)
        if lcl_sha1 is not None and rmt_sha1 != lcl_sha1:
            # Backup via an explict reflog entry if this is not an ancestor.
            if not self.is_ancestor(lcl_sha1, rmt_sha1):
                result = run(["git", "update-ref", "-m",
                              "cranky checkout: previous tip", "HEAD", "HEAD"],
                             cwd=self.directory)
                if result.returncode != 0:
                    raise GitError("unable to backup previous tip rc={}".format(result.returncode))

            # RESET
            result = run(["git", "reset", "--hard", rmt_ref], cwd=self.directory)
            if result.returncode != 0:
                raise GitError("unable to reset to new tip tip rc={}".format(result.returncode))

        # Validate whether the right branch is checked out.
        validate_hdl = Handle().lookup_tree(self.directory)
        if self.package != validate_hdl.package:
            cwarn("Repository '{}' has the wrong package checked out {}:{}".format(
                  self.directory, validate_hdl.package.series.codename,
                  validate_hdl.package.name))

    def clone(self, reference=None, dissociate=False):
        '''
        Clone the repository which the GitHandle represents.
        '''
        pkg  = self.__ht.package
        repo = pkg.repo

        if repo is None:
            raise GitError('{} has no repository set'.format(pkg.name))

        remote   = self.__ht.remote
        branch   = self.remote_branch
        repo_dir = self.directory
        repo_url = self.get_url()

        cmd = ["git", "clone", "--origin", remote, "--branch", branch]
        if pkg.type is None and reference is not None:
            if GitDirectory(reference).is_valid:
                cmd.extend(["--reference", reference])
            else:
                cwarn('Warning: {} is not a directory or git repo'.format(reference))
        cmd.extend([repo_url, repo_dir])

        cnotice('Cloning "{}" into {}'.format(pkg.name, repo_dir))
        result = run(cmd)
        if result.returncode != 0:
            raise GitError('git clone failed (rc={})'.format(result.returncode))

    def update_remote(self, remote, repo_url, fetch=True):
        repo_dir = self.directory

        result = run(["git", "config", "remote.{}.url".format(remote)],
                     cwd=repo_dir, stdout=PIPE)
        if result.returncode == 0:
            current_url = result.stdout.decode('utf-8').strip()
            if current_url != repo_url:
                cnotice("Updating remote {} in {}".format(remote, repo_dir))
                result = run(["git", "config", "remote.{}.url".format(remote),
                              repo_url], cwd=repo_dir, stdout=PIPE)
                if result.returncode != 0:
                    raise GitError("failed to update remote {} url to {} "
                                   "rc={}".format(remote, repo_url, result.returncode))
        else:
            cnotice("Adding remote {} in {}".format(remote, repo_dir))
            result = run(["git", "remote", "add", remote, repo_url], cwd=repo_dir)
            if result.returncode != 0:
                raise GitError("failed to add remote {} "
                               "rc={}".format(remote, result.returncode))

        if fetch:
            cnotice("Fetching remote {} in {}".format(remote, repo_dir))
            result = run(["git", "fetch", remote], cwd=repo_dir)
            if result.returncode != 0:
                raise GitError("failed to fetch remote {} "
                               "rc={}".format(remote, result.returncode))

    def configure(self):
        '''
        Do some additional configuration on the GitHandle
        '''
        repo_dir = self.directory
        repo_url = self.get_url()
        pkg_type = self.package.type
        codename = self.package.series.codename

        # Add the default mailing list address for sending patches
        if "canonical-kernel-esm" in repo_url:
            address = "canonical-kernel-esm@lists.canonical.com"
        else:
            address = "kernel-team@lists.ubuntu.com"
        run(["git", "config", "--local", "sendemail.to", address],
            cwd=repo_dir)

        # Don't cc the patch author and signers, i.e., don't spam upstream
        run(["git", "config", "--local", "sendemail.suppresscc", "all"],
            cwd=repo_dir)

        # Add a remote for the (private) security repo
        if pkg_type is None:
            security_repo = "linux-{}".format(codename)
        else:
            security_repo = "linux-{}-{}".format(pkg_type, codename)

        security_url  = 'git+ssh://git.launchpad.net/~canonical-kernel-security-team/'
        security_url += 'canonical-kernel-private/+git/{}'.format(security_repo)

        try:
            # Add the security repo without fetching it
            self.update_remote("security", security_url, fetch=False)
        except SystemExit:
            cwarn('Could not add remote "security" {}'.format(security_url))


class GitHandleSet():
    '''
    A git based view onto a HandleSet. To be used as an accessor to git functionality
    for HandleSet()s and HandleTree()s.
    '''
    def __init__(self, handle):
        '''
        handle := <series>:<source>
        '''
        # Might raise a HandleError:
        hdl = Handle()
        try:
            self.__hdlset = hdl.lookup_set(handle, validate=False)
        except HandleError as e:
            raise GitError(e)

        # Check for a meta-only package.  This should really imply checking
        # out the matching derived-from packages with our -meta; we do this as we
        # will want to run updates against that.
        derived_from = self.__hdlset.source.derived_from
        if derived_from is not None:
            meta_only = True
            for handle_tree in self.__hdlset.trees:
                if handle_tree.package.type != 'meta':
                    meta_only = False
                    break
            if meta_only:
                prime_handle = "{}:{}".format(derived_from.series.codename,
                                              derived_from.name)
                prime_set = hdl.lookup_set(prime_handle, validate=False)
                for handle in prime_set.trees:
                    if handle.package.type != 'meta':
                        self.__hdlset.trees.append(handle)

        # If the trees already exist, we need to make sure they are clean otherwise
        # we may destroy work in progress.
        for handle_tree in self.__hdlset.trees:
            if not GitHandle(handle_tree).is_clean():
                raise GitError("repo for {} is not clean, unable to update".format(
                               handle_tree.name))

        # Transorm the handle_tree object of the handle_set into a set of GitHandle
        # objects.
        self.__ghs = []
        for handle_tree in self.__hdlset.trees:
            self.__ghs.append(GitHandle(handle_tree))

    @property
    def codename(self):
        return self.__hdlset.series.codename

    @property
    def source(self):
        return self.__hdlset.source

    def __iter__(self):
        '''
        Returns all GitHandle objects which are part of the GitHandleSet.
        '''
        for gh in self.__ghs:
            yield gh
