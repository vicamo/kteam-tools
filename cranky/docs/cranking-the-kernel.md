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

### Initialize chroot environment

Make sure you have a proper chroot environment for the release and the kernel
that you are going to build.

Example:
```
cranky chroot run xenial:linux-oracle -- cat /etc/debian_chroot
```

If you get something like `xenial-amd64` the chroot environment is correctly
initialized.

Otherwise, if get an error, you need to initialize the chroot environment to
properly build the kernel. In this case use `cranky chroot` to create the
chroot environment for the kernel to build (as documented in
"cranky-env-conf.md").

Example:
```
cranky chroot create-base xenial:linux-oracle
cranky chroot create-session configs xenial:linux-oracle
```
### chroot section done - ready to crank!

### Clone the kernel repository - `cranky checkout`

Use `cranky clone` to get the kernel that you want to build.

Example:
```
cd canonical/kernel/ubuntu
cranky clone xenial:linux-oracle
```

### Tool sync stage - `cranky fix`

This updates the local (in-tree) helper scripts which cranky uses to the latest
version and also can update/create the "debian./etc/update.conf" file and
commits those changes. In case of a rebase tree, the changes to the helpers may
vanish on rebase if those were already done there.
```
cd xenial/linux-oracle
cranky fix
```

**Note** The `cranky fix` step has a chicken/egg problem when unbreaking a
derivative chain. For example a senior crank turner got the wrong master
directory when doing the new trusty/azure. Care must be taken to verify.

### Rebase stage - `cranky rebase`

At this stage, master kernels do not require anything to be done. So, running
`cranky rebase` on them should be a no-op, resulting in no change.

For both derivatives and backports, `cranky rebase` is the first stage. In both
cases one has to fetch the tip of the branch from which the current kernel is
derived/backported from. For derivatives, this is a local branch name which is
specified by "-l <branch>". For backports this is a remote repository (which
can be an URL or a path to a local git repository) and a remote branch name
"(-r <repo> -b <branch>)".

If no options are used, the default remote location defined in "update.conf" is
used. This should be good enough for most cases as long as one does not mind
the network traffic. But working on embargoed CVEs will require using the
options because that process requires private repositories.

Should there be any conflicts during the rebase, normal git conflict resolution
steps "git rebase ---skip, git rebase --continue, ..." have to be taken.

Example:
```
cranky rebase
```

Another example:
```
cranky rebase -r <local path to kernel git repo> [-b master-next]
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
```
$ cranky fix
```

At this point you should double check that the version number at the top of
"debian.master/changelog" matches the version that you see on the dashboard:
```
https://kernel.ubuntu.com/sru/dashboards/web/kernel-stable-board.html
```

Look under "linux", inside the section of the release in the dashboard you are
currently cranking such as "xenial".

### Starting commit - `cranky open`

When a new release is in the plans, a starting commit should be created. That
historically has been done with "maint-startnewrelease". Now, it's done by
running `cranky open`. This step should be done after rebasing, because it's
needed on backports as well, where the "update-from-master" script is called,
but the changelog is opened just for inclusions.  The insertion of changelog
entries is done by the cranky close stage.
```
$ cranky open
```
**Note** `cranky start` is still available but `cranky open` usage is
preferable. Use `cranky start --force` if you find any blocking issues
with `cranky open`.

### Link to tracker which is now done by `cranky link-tb`
```
$ cranky link-tb
```

**Note** this command is making public changes, it's not only affecting your
local repository. Make sure to skip this test if you're doing local tests.

### Closing commit - `cranky close`

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

2) Runs "insert-ubuntu-changes" to insert into the changelog the changes that
come from a master kernel. When `cranky close` is run on a master kernel, it
won't perform this step.

3) Runs "debian/rules insertchanges", inserting into the changelog the changes
that it finds from git.

4) Updates the release series, author and date on the changelog, thus closing
the changelog.

5) Commits with the correct messages.

6) Prints to stdout the git-tag command a human should run to sign that tag.

If you see the "git tag" command printed by `cranky close` at the end, copy it
and execute it (double checking if the tag is correct).

Example:
```
$ git tag -sm 'Ubuntu-azure-4.15.0-1041.45' 'Ubuntu-azure-4.15.0-1041.45' 7eec9153251fde76ce1f664e5ad51c475a4ee20b
```

**Note** `cranky close` doesn't always print the git-tag command. This is a bug
that must be fixed.  If you don't see a git-tag command do this instead:

```
$ git log -1
```

Example output

commit 350198be5cf41183e5193a5a728a740cb55017a8 (HEAD -> cranky/master-next)
Author: <first-last-name> <your-canonical-email@canonical.com>
Date:   Wed Mar 13 15:33:20 2019 +0100

    UBUNTU: Ubuntu-kvm-4.15.0-1031.31

    Signed-off-by: <first-last-name> <your-canonical-email@canonical.com>

Copy the string "Ubuntu-kvm-4.15.0-1031.31" (replace it with the equivalent
string that you have) and run:

```
git tag -s -m Ubuntu-kvm-4.15.0-1031.31 Ubuntu-kvm-4.15.0-1031.31
```

### Tagging - `cranky tag`

For now, just run `cranky close`, then copy and execute the last "git tag"
output line.  See procedure above.

### Testing builds - `cranky test-build`

Uses the "git-build-kernel" method to test-build the tip of the kernel branch
currently checked out.

Example:
```
cranky test-build -f -a all kathleen
```

Make sure to specify "-a all" for official builds, we want to make sure the
kernel builds in all architectures, otherwise `cranky test-build` would build
the kernel only for the host's architecture.

**Note** crank-turners need to add the following host entry to /etc/hosts
before running the example command: `cranky test-build -f -a all kathleen`
10.246.72.52 kathleen

**Note 2** kathleen in the example above represents both a git remote name,
which by default matches the name of the remote build host.

### Prepare meta/signed repositories - `cranky prepare-meta`

Currently this step must be done manually, calling the "./update-version"
scripts from "linux-meta" and "linux-signed" (the addition repositories
cloned via `cranky checkout`).

Example:
```
cd ../linux-meta-oracle
./update-version ../linux-oracle

cd ../linux-signed-oracle
./update-version ../linux-oracle
```

Output (for both commands) should look like this:
...
git commit -s -m 'UBUNTU: Ubuntu-kvm-4.15.0.1031.31' debian/changelog
git tag -s -m 'Ubuntu-kvm-4.15.0.1031.31' 'Ubuntu-kvm-4.15.0.1031.31'

**Note** update-version doesn't run the "git commit" and "git tag" commands
so you must run them next.  These are last two lines printed to stdout above
and are the commands you need to copy and run them manually.
```
$ git commit -s -m 'UBUNTU: Ubuntu-kvm-4.15.0.1031.31' debian/changelog
$ git tag -s -m 'Ubuntu-kvm-4.15.0.1031.31' 'Ubuntu-kvm-4.15.0.1031.31'
```

It is mandatory to run "udpate-version' from the "linux-meta" and
"linux-signed" directory, not from the kernel source directory.

**Note** In certain releases "linux-signed" is missing, for example
"linux-kvm". To show the list of expected repositories for a certain
release/flavor you can use the command `cranky rmadison`, example:
```
cranky rmadison xenial:linux-oracle
```

### Build sources - `cranky build-sources`

Before running `cranky build-sources`, make sure you download the previous
source code in the parent directory before running `cranky build-sources`
(do this with linux, linux-meta and linux-signed).

Example:

```
$ cd ..
$ pull-lp-source --download-only linux-oracle xenial
$ pull-lp-source --download-only linux-meta-oracle xenial
$ pull-lp-source --download-only linux-signed-oracle xenial
$ cd -
```

Doing it this way, `cranky build-source` will produce the diff.gz instead of
whole tarballs.

Now run `cranky build-sources` from the main kernel source directory to build the
source packages.

Example:

```
cd linux-oracle
cranky build-sources
```
## Review

### Reviewing - `cranky review`

Generates debdiff files for review between newly generated .dsc files and
those currently in the archive. Takes source.changes filenames as
argument(s) and produces .debdiff files for review.

Example (run this on the same directory where the .changes and .dsc files have
been generated by the previous step):
```
cranky review *.changes
```

### Uploading packages - `cranky upload`

The command `cranky upload` does not exist yet. In the meantime, the following
manual procedure will serve.

Push git repositories to your Launchpad for a review:

```
cd linux-oracle
git remote add for-review lps:~arighi/+git/xenial-linux-oracle
git push --tags for-review cranky/master-next
cd ..

cd linux-meta-oracle
git remote add for-review lps:~arighi/+git/xenial-linux-meta-oracle
git push --tags for-review cranky/master
cd ..

cd linux-signed-oracle
git remote add for-review lps:~arighi/+git/xenial-linux-signed-oracle
git push --tags for-review cranky/master
cd ..
```

Upload source packages to wani.canonical.com for a review:
```
ssh wani.canonical.com mkdir -p for-review/xenial-linux-oracle
scp *4.15.0.1031.31* *4.15.0-1031.31* wani.canonical.com:~/for-review/xenial-linux-kvm
```

After source packages and git repositories have been reviewed and acknowledged
by another kernel team member, copy the signed packages locally to your host
and upload them using dput:

```
dput -u ppa:canonical-kernel-team/ppa linux-oracle_4.15.0-1010.12~16.04.1_source.changes
dput -u ppa:canonical-kernel-team/ppa linux-meta-oracle_4.15.0.1010.4_source.changes
dput -u ppa:canonical-kernel-team/ppa linux-signed-oracle_4.15.0-1010.12~16.04.1_source.changes
```

**Note** Make sure you have ```default_host_main = UNKNOWN"``` set in your
~/.dput.cf, to prevent uploading packages to ```ubuntu```.

## Summary
As noted, this document (a living document itself) remains somewhat incomplete
as is the Automation 1.0 toolset. Both are still undergoing maturation as a
result of increased focus on automation as our primary means of productivity
improvement and has been a primary focus of our last two engineering sprints.

This document is the work of Stefan Bader and Andrea Righi, with collaboration
by Kleber Souza and content/editing by Terry Rudd. Any of us can be contacted
regarding issues or additional suggested content contribution but all Kernel
engineers should feel free to make change/update this document in kteam-tools.
