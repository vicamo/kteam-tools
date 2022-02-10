#                             Turning the Crank

Turning the crank refers to the process by which the Canonical Kernel Team
creates new kernels and updates all our existing kernels every three weeks as
part of the Ubuntu Stable Release Update (SRU) process.  To compliment the SRU
process the kernel engineering team has created a rich toolset for kernel
cranking, which we maintain in the kteam-tools repo, which you will need to
clone to your local machine as part of setting up your development
environment.

While the information in this document sufficiently covers all the necessary
steps a new kernel engineer needs to perform in order to crank a kernel, it is
expected that a mentor is assigned to any new/unfamiliar engineer to answer
questions and explain details for what is being done in each step for which
kernel and why.  Without understanding what is actually being done by these
tools, it is difficult to properly debug and solve issues on when something
inevitably breaks in the process.

This document is the work of Stefan Bader and Andrea Righi, with collaboration
by Kleber Souza and content/editing by Terry Rudd. Any of us can be contacted
regarding issues or additional suggested content contribution but all Kernel
engineers should feel free to make change/update this document in kteam-tools.

## Setup

### Initialize chroot environment - `cranky chroot`
<!--cheatsheet-->
```
cranky chroot create-base RELEASE:linux
cranky chroot create-session configs RELEASE:linux
```
<!--/cheatsheet-->

If your home directory or sources are not in the same partition as /
(e.g. separate /home partition or encrypted home directory with ecryptfs) you
might need to tweak /etc/schroot/sbuild/fstab:
```
# Allow use of /home for use with cranky.
/home           /home           none    rw,bind         0       0
# Allow use of /home with ecryptfs
/home/<user>    /home/<user>    none    rw,bind         0       0
```

Make sure you have a proper chroot environment for the release and the kernel
that you are going to build.

Example:
```
cranky chroot run xenial:linux -- cat /etc/debian_chroot
```

If you get something like `xenial-amd64` the chroot environment is correctly
initialized.

Otherwise, if you get an error, you need to initialize the chroot environment
to properly build the kernel. In this case use `cranky chroot` to create the
chroot environment for the kernel to build (as documented in
"crank-turning-setup.md").

Example:
```
cranky chroot create-base xenial:linux
cranky chroot create-session configs xenial:linux
```

After your chroot environment is initialized, you only need to update your
chroots before cranking each cycle. Do this by re-running `cranky chroot
create-session`.

Example:
```
cranky chroot create-session configs xenial:linux
```

### Removing a chroot environment

Once a non-LTS Ubuntu release reach end of life, you can remove the
corresponding chroot from your system.

First remove the session created by `cranky chroot`:

```
cranky chroot destroy-session configs RELEASE:linux
```

Then find the directory listed in the schroot configuration file under
`/etc/schroot/chroot.d/sbuild-RELEASE-amd64` and remove this
directory.

Finally, remove the file `/etc/schroot/chroot.d/sbuild-RELEASE-amd64`.

Example:

```
$ cranky chroot destroy-session configs groovy:linux

$ grep directory= /etc/schroot/chroot.d/sbuild-groovy-amd64
directory=/var/lib/schroot/chroots/groovy-amd64

$ rm -rf /var/lib/schroot/chroots/groovy-amd64

$ rm /etc/schroot/chroot.d/sbuild-groovy-amd64
```

## Build

### Update the kteam-tools repo
<!--cheatsheet-->
```
cd <kteam-tools repo>
git pull
```
<!--/cheatsheet-->

Before starting the crank (or at least once at the beginning of each SRU cycle),
update the kteam-tools repository to make sure the tools have any possible
recent changes that could impact cranking.

Example:
```
cd $HOME/canonical/kteam-tools
git pull
```

### Clone and checkout the kernel repository - `cranky checkout`
<!--cheatsheet-->
```
cranky checkout RELEASE:KERNEL
```
<!--/cheatsheet-->

Use `cranky checkout` to get the kernel that you want to build.

Example:
```
cd canonical/kernel/ubuntu
cranky checkout xenial:linux-oracle
```

**Note**: Private kernel repositories (including security) will get
checked out using a `git+ssh://` URL. If your local username and your
Launchpad ID are not the same, then the following mapping is needed
in your `~/.gitconfig` file:

```
[url "git+ssh://<your-launchpad-id>@git.launchpad.net/"]
	insteadof = "git+ssh://git.launchpad.net/"
```

### Tool sync stage - `cranky fix`
<!--cheatsheet-->
```
cranky fix
```
<!--/cheatsheet-->

This updates the local (in-tree) helper scripts which cranky uses to the latest
version and also can update/create the "debian.<variant>/etc/update.conf" file
and commits those changes. In case of a rebase tree, the changes to the helpers
may vanish on rebase if those were already done there.
```
cd xenial/linux-oracle
cranky fix
```

**Note** The `cranky fix` step has a chicken/egg problem when unbreaking a
derivative chain. For example a senior crank turner got the wrong master
directory when doing the new trusty/azure. Care must be taken to verify.

### Rebase stage - `cranky rebase`
<!--cheatsheet-->
```
cranky rebase
```
<!--/cheatsheet-->

At this stage, master kernels do not require anything to be done. So, running
`cranky rebase` on them should be a no-op, resulting in no change.

For both derivatives and backports, `cranky rebase` is the first stage. In both
cases one has to fetch the tip of the branch from which the current kernel is
derived/backported from. For derivatives, this is a local branch name which is
specified by "-l BRANCH". For backports this is a remote repository (which
can be an URL or a path to a local git repository) and a remote branch name
"(-r REPO -b BRANCH)".

If no options are used, the default remote location defined in "update.conf" is
used. This should be good enough for most cases as long as one does not mind
the network traffic. But working on embargoed CVEs will require using the
options because that process requires private repositories.

Should there be any conflicts during the rebase, normal git conflict resolution
steps "git rebase --skip, git rebase --continue, ..." have to be taken.

Example:
```
cranky rebase
```

Another example:
```
cranky rebase -r LOCAL_PATH_TO_KERNEL_GIT_REPO [-b master-next]
```

**Note** some times `cranky rebase` can fail due to conflicts. If conflicts are
affecting the debian helper scripts (debian/scripts) you can safely skip the
commit and continue with the rebase:
```
git rebase --skip
```

Conflicts that cannot be resolve this way, must be resolved manually.

**Note** Continue until the rebase completes without any conflicts and re-run
`cranky fix` at the end to make sure the helper scripts are correct.

<!--cheatsheet-->
```
cranky fix
```
<!--/cheatsheet-->

At this point you should double check that the version number at the top of
"debian.master/changelog" matches the version that you see on the dashboard:
https://kernel.ubuntu.com/sru/dashboards/web/kernel-stable-board.html

Look under "linux", inside the section of the release in the dashboard you are
currently cranking such as "xenial".

### Starting commit - `cranky open`
<!--cheatsheet-->
```
cranky open
```
<!--/cheatsheet-->

When a new release is in the plans, a starting commit should be created. This
is done by running `cranky open`. For derivatives and backports this step needs
to be done after rebasing because the new package version and the content of
some files under `debian.<variant>` depend on the new master version. The
insertion of changelog entries is done by the `cranky close` stage.
```
$ cranky open
```

**Note** `cranky start` is still available but `cranky open` usage is
preferable. Use `cranky start --force` if you find any blocking issues
with `cranky open`.

**Note** regarding private kernels: One of the steps performed by
`cranky open` is to download and update the ABI files based on the
last release and those files are obtained from a list of
repositories. For regular kernels that list is kept in-tree in the
file `debian.<variant>/etc/getabis`. For private kernels, this list is
retrieved from the file `~/.getabis.<series>-<variant>` (for instance:
`~/.getabis.bionic-fips`). That file should be created manually
containing on each line an URL (that can be obtained from the
`kteam-tools/info/kernel-series.yaml` file), but including your
subscription credentials to the PPA.

An example of an URL is:

```
https://USER:PASS@private-ppa.launchpad.net/ubuntu-advantage/fips-kernel-source/ubuntu
```

The username and password can be obtained from
<https://launchpad.net/~/+archivesubscriptions>.


### Include any necessary changes from the base kernel into the derivatives - `cranky review-master-changes`

Derivatives receive most of the changes from its base kernel via the
rebase. However we need to manually review changes that are applied to
debian.BRANCH in the base kernel.

Run `cranky review-master-changes` and review if any of the listed
changes need to be applied to the derivative.

In particular, check if any changes were made to debian.master/rules.d that should
be reflected in debian.DERIVATIVE/rules.d. Those commits may not be obvious in
the master changelog.

<!--cheatsheet-->
```
cranky review-master-changes
```
<!--/cheatsheet-->

### Link to tracker - `cranky link-tb`
<!--cheatsheet-->
```
cranky link-tb
```
<!--/cheatsheet-->

Link current build to tracker bug in Launchpad:
```
$ cranky link-tb
```

**Note** this command is making public changes, it's not only affecting your
local repository. Make sure to skip this test if you're doing local tests.

### dkms package update stage - `update-dkms-versions`
<!--cheatsheet-->
```
./update-dkms-versions
```
<!--/cheatsheet-->

In bionic and newer, this updates the package versions in `debian/dkms-versions`
to match the ones expected for the SRU cycle. By default this script will fetch
the data from a git repository containing a database of the dkms versions to be
used on each series for the given SRU cycle. The cycle date used is the one from
`debian.<variant>/tracking-bug`, so this script needs to be run after `cranky
link-tb`.

The git repository location and the SRU cycle date can be provided manually to
the script via optional parameters. However, in the normal case a manual
override should never be needed.

**Note**: `update-version-dkms` used to be required only for primary kernels
and kernels forward-ported to the development release. However, it has been
deprecated in favor of `update-dkms-versions` which is safe and even expected to
be run for all derivatives and backports as well. So always run this script to
make sure the main package has the most up-to-date versions.

In most cases there would be no change committed as the up-to-date versions
should have been committed on the master kernel and picked-up by the derivative
or backport on rebase. However, if there is any change, check that the version
numbers only become higher and nothing gets dropped completely. In case anything
looks suspicious, don't hesitate to ask the team if the changes are expected.

Example:
```
./update-dkms-versions
```

### Closing commit - `cranky close`
<!--cheatsheet-->
```
cranky close
```
<!--/cheatsheet-->

The last commit before a release is prepared by using `cranky close`. All of
the following steps are done automatically by `cranky close` so there is no
need to run any of them manually but they are explained here so that the
crank-turner knows what's going on for trouble-shooting purposes.
```
$ cranky close
```

This step:
1) Verifies there are no config changes left, by running "debian/rules
updateconfig" and checking no changes have been done;

**Note** It's possible that config changes were made in this release that trigger
further config changes (e.g. dependency config options). In that case, those
dependency changes will be generated when running 'updateconfigs', and cranky
close will print a message about those config changes and then exit early without
committing anything to the tree.

Those generated config changes need to be manually committed by the user first
before cranky close can resume. The commit message for those changes should
reference the bug number that caused the original config change.

In some cases, 'updateconfigs' will trigger a user prompt asking the user to
specify a value for the dependency config options. The value that should be
specified depends on the kernel being cranked and the config option in question.
Again, those config changes need to be manually committed before cranky close can
continue.

After committing all dependency config changes, cranky close needs to be re-run and
it should add the closing commit normally at that point.

2) Runs "insert-ubuntu-changes" to insert into the changelog the changes that
come from a master kernel. When `cranky close` is run on a master kernel, it
won't perform this step.

3) Runs "debian/rules insertchanges", inserting into the changelog the changes
that it finds from git.

4) Updates the release series, author and date on the changelog, thus closing
the changelog.

5) Commits with the correct messages.

**Note**: Private kernels might have commits that reference private
bugs or SalesForce cases (please check the private kernel git log to
find out what is usually used for each case) and because of that
`debian/rules insertchanges` might not be able to obtain the launchpad
bug title.

To workaround that, it's possible to update the commit message adding
the the bug title between parenthesis just after the Buglink URL, for
example:

- `BugLink: http://bugs.launchpad.net/bugs/9999999 (Private bug title... (LP: #9999999))`.
- `BugLink: https://canonical.my.salesforce.com/XXXXXXX (SF case title (SF: #99999999))`.

For patchsets, please make sure the exact same text between
parenthesis is used for all the patches in the series, otherwise
they will **not** be grouped in the changelog.

## Test

### Testing builds - `cranky test-build`
<!--cheatsheet-->
```
cranky test-build [-a ARCH[,ARCH,...]|-a all] [-f] HOST
```
<!--/cheatsheet-->

Uses the "git-build-kernel" method to test-build the tip of the kernel branch
currently checked out.

Example:
```
cranky test-build -f -a all kathleen
```

Make sure to specify "-a all" for official builds, we want to make sure the
kernel builds in all architectures, otherwise `cranky test-build` would build
the kernel only for the host's architecture.

If the test build fails and you need to apply additional fixes, make sure to
re-run `cranky close` once all additional fixes have been applied successfully.

**No additional commits should be added without re-running cranky close.**

**Note** crank-turners need to add the host entries to /etc/hosts before running
`cranky test-build`. The list of builders and their IP addresses can be found
on the section "List of builders" below.

**Note 2** kathleen in the example above represents both a git remote name,
which by default matches the name of the remote build host.

### Compile selftests for the master kernels

The kernel selftests are not compiled during a normal build of the packages.
Our testcases download the kernel source package and compile them from there
before running the tests. In order to avoid detecting a compilation issue
only at a later stage, the kernel selftests need to be compile-tested as well
before uploading the source packages to the PPA.

<!--cheatsheet-->
```
cranky test-build [-a ARCH[,ARCH,...]] -t compileselftests HOST
```
<!--/cheatsheet-->

This needs to be done only for the master kernels, as the derivatives don't
have any specific selftests patches applied.

Currently the only architectures supported for this build test is amd64 and
i386.

Example:
```
cranky test-build -f -a amd64,i386 -t compileselftests kathleen
```

### Tagging - `cranky tag`
<!--cheatsheet-->
```
cranky tag
```
<!--/cheatsheet-->

Run the following command to apply the correct tag to the kernel:
```
cranky tag
```

### Prepare meta/signed/resticted-modules repositories - `cranky update-dependent`
<!--cheatsheet-->
```
cd ../linux-meta-DERIVATIVE
cranky update-dependent
cranky tag

cd ../linux-signed-DERIVATIVE
cranky update-dependent
cranky tag

cd ../linux-restricted-modules-DERIVATIVE
cranky update-dependent
cranky tag
```
<!--/cheatsheet-->

Currently this step must be done manually, calling the scripts from
"linux-meta", "linux-signed" and "linux-restricted-modules" (the additional repositories
cloned via `cranky checkout`).

Example:
```
cd ../linux-meta-oracle
cranky update-dependent
cranky tag

cd ../linux-signed-oracle
cranky update-dependent
cranky tag

cd ../linux-restricted-modules-oracle
cranky update-dependent
cranky tag
```

It is mandatory to run "cranky update-dependent" and "cranky tag" from the
"linux-meta", "linux-signed" and "linux-restricted-modules" directories, not from the kernel
source directory.

**Note** In certain releases "linux-signed" and "linux-restricted-modules" are missing, for
example "linux-kvm". To show the list of packages that are part of a certain
kernel set, you can use the command `cranky rmadison`, example:
```
cranky rmadison xenial:linux-oracle
```

### Verify preparation
<!--cheatsheet-->
```
cd linux-DERIVATIVE && verify-release-ready
cd linux-meta-DERIVATIVE && verify-release-ready
cd linux-signed-DERIVATIVE && verify-release-ready
cd linux-restricted-modules-DERIVATIVE && verify-release-ready
```
<!--/cheatsheet-->

Perform one last sanity check on the git trees with `verify-release-ready` to catch
many of the mistakes that will require changes before this kernel passes review.

### Build sources - `cranky build-sources`
<!--cheatsheet-->
```
cranky build-sources
```
<!--/cheatsheet-->

Before running `cranky build-sources`, you need to download the previous
source packages to the parent directory. Note that you need to download all
source packages listed by `cranky rmadison` for the kernel set you're working
on.

Example:

```
$ cd ..
$ cranky pull-source linux-oracle xenial
$ cranky pull-source linux-meta-oracle xenial
$ cranky pull-source linux-signed-oracle xenial
$ cd -
```

Doing it this way, `cranky build-sources` will produce the diff.gz instead of
whole tarballs.

Now run `cranky build-sources` from the main kernel source directory to build the
source packages.

Example:

```
cd linux-oracle
cranky build-sources
```

**Note:** If you are performing a respin and the package version in `-proposed` is greater
than the package version in `-updates`, then the package version in `-updates` must be
supplied to `cranky build-sources` so the source packages are built against the correct
package versions to preserve the delta between the one in `-updates` and the current spin.
One can use `cranky rmadison` to see what versions are in `-updates` and `-proposed`.

Example:

```
$ cranky rmadison xenial:linux-oracle
$ # output of cranky rmadison omitted for brevity
$ cd linux-oracle
$ cranky build-sources --build-opts "main:-v4.15.0-1021.23~16.04.1" --build-opts "meta:-v4.15.0.1021.15" --build-opts "signed:-v4.15.0-1021.23~16.04.1"
```

## Review

### Reviewing - `cranky review`
<!--cheatsheet-->
```
cranky review *.changes
```
<!--/cheatsheet-->

Generates debdiff files for review between newly generated .dsc files and
those currently in the archive. Takes source.changes filenames as
argument(s) and produces .debdiff files for review.

Example (run this on the same directory where the .changes and .dsc files have
been generated by the previous step):
```
cranky review *.changes
```

**Note:** The example above will generate debdiffs for all the .changes files
in the current directory. If you are keeping files from older cranks in the
same directory, provide different parameters that would create the debdiffs
only for the latest crank.

### Sign packages - `debsign`

Sign the source packages:
```
debsign *_source.changes
```

**Note** While this step is not really needed (unless you already have upload
rights), it is a good practice to get familiar with package signing. When
uploading packages, this manual step is not necessary as it is wrapped by
`cranky dput-sources` (see below).

### Uploading packages - `cranky upload`

**Note:** Uploading packages can only be done by team members with upload
rights. Pushing to the official git repos can only be done by team members with
commit rigths. Before a new member is granted such rights, the git trees and
source packages produced need to be reviewed and sponsored by some other team
member with the necessary rights.

**Note:** DO NOT publish private kernels such as ESM, linux-ibm-gt and
linux-fips to public repositories, see section "Special kernels" below.

The best way to provide the git trees for a review is pushing them to one of
our builders (which are hidden behind the VPN). All the builders have all the
git trees under `/usr3/ubuntu/` so they can be quickly cloned from there to your
home directory.

Tips:
- The same git repo cloned by `cranky test-build` can be used for the reviews.
- It's not necessary to clone all trees as different sources can be pushed to
  the same tree. A good solution to save some disk space is to clone only the
  tree for the main kernel for each of the series.

You only need to push master or master-next and the last tag applied:
```
cd linux-oracle
git remote add for-review ssh://<builder>/~/xenial-linux-oracle
git push for-review cranky/master-next
git push for-review TAG
cd ..

cd linux-meta-oracle
git remote add for-review ssh://<builder>/~/xenial-linux-meta-oracle
git push for-review cranky/master
git push for-review TAG
cd ..

cd linux-signed-oracle
git remote add for-review ssh://<builder>/~/xenial-linux-signed-oracle
git push for-review cranky/master
git push for-review TAG
cd ..
```

TAG represents the last tag applied on each repository. The last tag can be
determined running the following command:
```
git tag --sort=creatordate | tail -1
```

Make sure the tag matches the last version that we are currently uploading for
review.

Upload source packages to one of the builders for a review:
```
ssh <builder> "mkdir -p for-review/xenial-linux-oracle"
scp *4.15.0.1031.31* *4.15.0-1031.31* <builder>:~/for-review/xenial-linux-oracle
```

Add the information about the git tags and the source packages to the crank
card/issue in a way that would be easy for the reviewer to fetch them. I.e.,
the tag location can be used as ia copy+paste parameter to `git fetch` and the
packages location to `scp`.

Example:

```
main:   git+ssh://<builder>/~<user>/xenial-linux-oracle tag <TAG>
meta:   git+ssh://<builder>/~<user>/xenial-linux-meta-oracle tag <TAG>
signed: git+ssh://<builder>/~<user>/xenial-linux-signed-oracle tag <TAG>

packages: <builder>:~<user>/for-review/xenial-linux-oracle/
```

After source packages and git repositories have been reviewed and acknowledged
by another kernel team member, this person could either upload the packages
themselves or send them back to the cranker for upload. For the latter, copy
the signed packages to the same directory that `cranky build-sources` uses, this
replaces the previously signed files. Then upload them using `cranky
dput-sources`:
```
cranky dput-sources build xenial:linux-oracle
```

Unless stated otherwise, the default upload destination should always be
"build". You can find the other possible upload destinations and archive/ppa
information by executing the following cranky command:
```
cranky list-routing xenial:linux-oracle
```

**Note:** dput-sources will always ask if you want to (re-)sign the packages.
In the case where you are uploading packages which were sponsored and signed
by another team member, the packages should not be re-signed as Launchpad would
reject packages signed by a user who doesn't have upload rights.

Alternatively, you can upload them manually using dput:
```
dput -u ppa:canonical-kernel-team/ppa linux-oracle_4.15.0-1010.12~16.04.1_source.changes
dput -u ppa:canonical-kernel-team/ppa linux-meta-oracle_4.15.0.1010.4_source.changes
dput -u ppa:canonical-kernel-team/ppa linux-signed-oracle_4.15.0-1010.12~16.04.1_source.changes
```

**Note** When uploading manually using dput, double check the destination to
make sure the packages are being uploaded to the correct PPA. Also make sure
you have ```default_host_main = UNKNOWN"``` set in your ~/.dput.cf, to prevent
uploading packages to ```ubuntu```. (see snip-dput.cf)

### Special kernels

Pay attention to the following kernels, they require special actions to be
cranked:
- all kernels marked as "private" in info/kernel-series.yaml
- all the ESM kernels

### Launchpad repositories

Another option to provide public repositories to other members of the team or to
external people is using Launchpad. This is described here though for
documention purpose only, pushing kernels for review to one of the builders is
the preferred way to avoid leaking private repositories to the public by
mistake.

The best to fork an existing parent repository into your own namespace is using
launchpad web UI. This will create an efficient server side fork, minimizing the
amount of objects one needs to push. For example open
https://code.launchpad.net/ubuntu/+source/linux-oracle select the
right series team owned repo
https://code.launchpad.net/~canonical-kernel/ubuntu/+source/linux-oracle/+git/focal,
click "fork it directly to your account". 

### List of builders

This is the current list of builders which can be used for test-builds and
pushing cranks for review.

* 10.246.72.52		kathleen	kathleen.buildd
* 10.246.75.167		sita		sita.kernel sita.maas
* 10.246.72.16		gloin		gloin.kernel
