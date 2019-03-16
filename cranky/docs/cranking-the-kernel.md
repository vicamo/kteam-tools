#                             Turning the Crank

Turning the crank refers to the process by which the Canonical Kernel Team
creates new kernels and updates all our existing kernels every three weeks as
part of the Ubuntu Stable Release Update (SRU) process.  To compliment the SRU
process the kernel engineering team has created a rich toolset for kernel
cranking, which we maintain in the kteam-tools repo, which you will need to
clone to your local machine as part of setting up your development
environment.

## Preface

While the information in this document sufficiently covers all the necessary
steps a new kernel engineer needs to perform in order to crank a kernel, it is
expected that a mentor is assigned to any new/unfamiliar engineer to answer
questions and explain details for what is being done in each step for which
kernel and why.  Without understanding what is actually being done by these
tools, it is difficult to properly debug and solve issues on when something
inevitably breaks in the process.

## Before You Start

Before proceeding with this document, it is important to have followed the
instructions in "cranky-env.conf.md" on your local host machine and  basic
understanding of what Cranking an Ubuntu Kernel is all about. Information and
instructions in this document assume this this order of action as a pre-
requisite to successfully implementing procedures below.

To that point, make sure you have an up-to-date clone of the kteam-tools repo
before starting and make sure also that you have access to the kernel team
Trello workflow system.

The scripts for Start the Kernel SRU Cycle need some initial configuration
before the first run, which is documented in $HOME/kteam-tools/stable/README.
For example, the script "create-sru-cards.py" depends on the Trello
command-line tools, so make sure to follow the steps reported in
$HOME/kteam-tool/stable/README about this particular script.

If for some reason, a locally modified version of kernel-series.yaml is needed,
this can be done by setting (and exporting):
```
USE_LOCAL_KERNEL_SERIES_YAML=1
```

Instructions for creating the "~/.cranky.yaml" file are included in the
"cranky-env-conf.md" document

This document is now a part of the kteam-tools repo to ensure it is regularly
updated along with the various tools it described.  This information will no
longer be maintained in Google Docs.

## Start The Kernel SRU Cycle

[This section might change in Q2 2019]

It is important that a new or unfamiliar kernel cranking engineer is enabled
in the kernel team Trello instance, which is a kanban tool that serves as our
workflow manager. While this section documents tools only the kernel SRU cycle
lead typically runs, it is worth noting the tools interact with Trello. These
steps are part of the SRU cycle, even though they are not part of the build
itself. Therefore if someone unfamiliar were to testing this procedure,
it won't work, unless he/she has a kernel team Trello account.

**Note** Anyone testing this section should check with the SRU team lead first
since some of these tools could destroy in-flight work in the current SRU cycle.

On the week before the actual start of the cycle (3rd week of the previous SRU
cycle), the SRU "lead" will create a Trello board to coordinate the tasks that
are done before the first week of the cycle, e.g. apply patches from the
mailing-list, prepare mainline stable updates, review CVE tracker, etc.  The
script "stable/create-sru-cards.py" creates the board with the initial cards.
To create the board and the cards, "create-sru-cards.py" reads the configuration
file "stable/create-sru-cards.yaml" and information about the current supported
kernels from "info/kernel-series.yaml" (wrapped by a library). The script also
adds an entry to the "info/sru-cycle.yaml" file with the information of the
upcoming cycle.

By default, the only required parameter is the cycle tag name (the date of the
Monday of the first week, in the format ‘YYYY.MM.DD’). Example:
```
create-sru-cards.py 2019.03.04
```

Some of the aspects of the default behavior can be changed by providing
additional parameters, please check the script --help output. The default to be
used now is not to create any kernel related task cards. Those will be added in
the next step.

After the board is created, the people involved in the SRU cycle need to be
manually added to the board and the key persons given ‘admin’ permissions.

Next, kernel tasks would be created by "create-kernel-tasks" which would create
tracking bugs and (if not for development) also add crank turn cards to the
backlog of the cycle board.
```
create-kernel-tasks 2019.03.11
```

Members of the Development team would use the following command:

```
create-kernel-tasks --devel 2019.03.11
```

In this case, "2019.03.11" is a real SRU Cyle. Replace with the current cycle.

The first instance creates tracking bugs and related cards on the Trello board
for all series and sources currently supported (excluding the current
development series). The second instance will only create tracking bugs
(no Trello cards) for the sources in the development series and automatically
prefixes the cycle tag with a ‘d’. The spin number is automatically calculated
and starts with 1.

### Managing kernel re-spins, which we seem to do every cycle now

In this example, we will re-spin the linux-oem source for the currently running
cycle. The following command will create new cards for cranking and a new
tracking bug for linux-oem.  It also marks the old tracking bug as a duplicate
of the new one and replaces the reference in the linux (master) tracking bug by
one to the freshly created one:
```
create-kernel-tasks --series bionic --source linux-oem 2018.09.24
```
Again, "2019.09.24" is a real SRU cycle, so update accordingly. For more
options, see the "--help" output.

## The next several steps are performed by all Stable Team crank-turners

### Initialize chroot environment

Make sure you have a proper chroot environment for the release and the kernel
that you are going to build.

Example:
```
cranky-chroot run bionic:linux-kvm -- cat /etc/debian_chroot bionic-amd64
```

If you get an error message you need to initialize the chroot environment to
properly build the kernel. In this case use cranky-chroot to create the chroot
environment for the kernel to build (as documented in "cranky-env-conf.md").

Example:
```
cranky-chroot create-base bionic:linux-kvm
cranky-chroot create-session configs bionic:linux-kvm
```
### chroot section done - ready to crank!

### Clone the kernel repository - cranky-checkout

Use cranky-clone to get the kernel that you want to build.

Example:
```
cd canonical/kernel/ubuntu
cranky-clone bionic:linux-kvm
```

### Tool sync stage - cranky-fix

This updates the local (in-tree) helper scripts which cranky uses to the latest
version and also can update/create the "debian./etc/update.conf" file and
commits those changes. In case of a rebase tree, the changes to the helpers may
vanish on rebase if those were already done there.
```
cd bionic/linux-kvm
cranky-fix
```

**Note** The "cranky-fix" step has a chicken/egg problem when unbreaking a
derivative chain. For example a senior crank turner got the wrong master
directory when doing the new trusty/azure. Care must be taken to verify.

### Rebase stage - cranky-rebase

At this stage, master kernels do not require anything to be done. So, running
cranky-rebase on them should be a no-op, resulting in no change.

For both derivatives and backports, "cranky-rebase" is the first stage. In both
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
cranky-rebase
```

Another example:
```
cranky-rebase -r <local path to kernel git repo> [-b master-next]
```

**Note** some times cranky-rebase can fail due to conflicts. If conflicts are
affecting the debian helper scripts (debian/scripts) you can safely skip the
commit and continue with the rebase:
```
git rebase --skip
```

Conflicts that cannot be resolve this way, must be resolved manually.

**Note** Continue until the rebase completes without any conflicts and re-run
cranky-fix at the end to make sure the helper scripts are correct.
```
$ cranky-fix
```

At this point you should double check that the version number at the top of
"debian.master/changelog" matches the version that you see on the dashboard:
```
https://kernel.ubuntu.com/sru/dashboards/web/kernel-stable-board.html
```

Look under "linux", inside the section of the release in the dashboard you are
currently cranking such as "bionic".

### Starting commit - cranky-start

When a new release is in the plans, a starting commit should be created. That
historically has been done with "maint-startnewrelease". Now, it's done by
running "cranky-start". This step should be done after rebasing, because it's
needed on backports as well, where the "update-from-master" script is called,
but the changelog is opened just for inclusions.  The insertion of changelog
entries is done by the cranky close stage.
```
$ cranky-start
```
**Note** cranky-open is a proposed replacement for cranky-start and being
pilot-tested in SRU 2019.03.11 so this section is likely to change.

### Link to tracker which is now done by cranky-link-tb
```
$ cranky-link-tb
```

**Note** this command is making public changes, it's not only affecting your
local repository. Make sure to skip this test if you're doing local tests.

### Closing commit - cranky-close

The last commit before a release is prepared by using "cranky-close". All of
the following steps are done automatically by "cranky-close" so there is no
need to run any of them manually but they are explained here so that the
crank-turner knows what's going on for trouble-shooting purposes.
```
$ cranky-close
```

This step:
1) Verifies there are no config changes left, by running "debian/rules
updateconfig" and checking no changes have been done;

2) Runs "insert-ubuntu-changes" to insert into the changelog the changes that
come from a master kernel. When "cranky-close" is run on a master kernel, it
won't perform this step.

3) Runs "debian/rules insertchanges", inserting into the changelog the changes
that it finds from git.

4) Updates the release series, author and date on the changelog, thus closing
the changelog.

5) Commits with the correct messages.

6) Prints to stdout the git-tag command a human should run to sign that tag.

If you see the "git tag" command printed by cranky-close at the end, copy it
and execute it (double checking if the tag is correct).

Example:
```
$ git tag -sm 'Ubuntu-azure-4.15.0-1041.45' 'Ubuntu-azure-4.15.0-1041.45' 7eec9153251fde76ce1f664e5ad51c475a4ee20b
```

**Note** cranky-close doesn't always print the git-tag command. This is a bug
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

### Tagging - cranky-tag

For now, just run "cranky-close", then copy and execute the last "git tag"
output line.  See procedure above.

### Testing builds - cranky-test-build

Uses the "git-build-kernel" method to test-build the tip of the kernel branch
currently checked out.

Example:
```
cranky-test-build -f -a all kathleen
```

Make sure to specify "-a all" for official builds, we want to make sure the
kernel builds in all architectures, otherwise cranky-test-build would build
the kernel only for the host's architecture.

**Note** crank-turners need to add the following host entry to /etc/hosts
before running the example command: "cranky-test-build -f -a all kathleen"
10.246.72.52 kathleen

**Note 2** kathleen in the example above represents both a git remote name,
which by default matches the name of the remote build host.

### Prepare meta packages - cranky-prepare-meta

Currently this step must be done manually, calling the "./update-version"
scripts from "linux-meta" and "linux-signed" (the addition repositories
cloned via "cranky-checkout").

Example:

```
cd ../linux-meta
./update-version ../linux
```
Output to stdout is
...
git commit -s -m 'UBUNTU: Ubuntu-kvm-4.15.0.1031.31' debian/changelog
git tag -s -m 'Ubuntu-kvm-4.15.0.1031.31' 'Ubuntu-kvm-4.15.0.1031.31'

**Note** update-version doesn't run the "git commit" and "git tag" commands
so you run them next.  These are last two lines printed to stdout above and
are the commands you need to copy and run them manually.
```
$ git commit -s -m 'UBUNTU: Ubuntu-kvm-4.15.0.1031.31' debian/changelog
$ git tag -s -m 'Ubuntu-kvm-4.15.0.1031.31' 'Ubuntu-kvm-4.15.0.1031.31'
```
It is mandatory to run "udpate-version' from the "linux-meta" and
"linux-signed" directory, not from the kernel source directory.

**Note** In certain releases "linux-signed" is missing, for example linux-kvm.
To show the list of expected repositories for a certain release/flavor use the
command cranky-rmadison, example:

```
cranky-rmadison bionic:linux-kvm
```

### Build sources - cranky-build-sources

Before running cranky-build-sources, make sure you download the previous
source code in the parent directory before running cranky-build-sources
(do this with linux, linux-meta and linux-signed).

Example:

```
$ cd ..
$ pull-lp-source --download-only linux-kvm bionic
$ pull-lp-source --download-only linux-meta-kvm bionic
$ cd -
```

Doing it this way, cranky-build-source will produce the diff.gz instead of
whole tarballs.

Now run cranky-build-sources from the main kernel source directory to build the
source packages.

Example:

```
$ cranky-build-sources
```

**Note** this part is currently under discussion as to how to proceed.

There is ongoing discussion on how to use "cranky-build-sources"
Should it be called Locally? How can we avoid getting chroots just
re-created? Should we use one of the builders instead of building the
sources local?

Using "--help" isn't helpful at all right now.

```
cranky-build-sources --help
```

### Reviewing - cranky-review

Generates debdiff files for review between newly generated .dsc files and
those currently in the archive. Takes source.changes filenames as
argument(s) and produces .debdiff files for review.

Example (run this on the same directory where the .changes and .dsc files have
been generated by the previous step):
```
cranky-review *.changes
```

### Uploading packages - cranky-upload

The command cranky-upload does not exist yet. In the meantime, the following
manual procedure will serve.

Push git repositories to your Launchpad for a review:

```
cd linux-kvm
git remote add for-review lps:~arighi/+git/bionic-linux-kvm
git push --tags for-review cranky/master-next
cd ..

cd linux-meta-kvm
git remote add for-review lps:~arighi/+git/bionic-linux-meta-kvm
git push --tags for-review cranky/master
cd ..
```

Upload source packages to wani.canonical.com for a review:
```
ssh wani.canonical.com mkdir -p for-review/bionic-linux-kvm
scp *4.15.0.1031.31* *4.15.0-1031.31* wani.canonical.com:~/for-review/bionic-linux-kvm
```

After source packages and git repositories have been reviewed and acknowledged
by another kernel team member, copy the signed packages locally to your host
and upload them using dput:

```
dput -u ppa:canonical-kernel-team/ppa linux-kvm_4.15.0-1031.31_source.changes
dput -u ppa:canonical-kernel-team/ppa linux-meta-kvm_4.15.0.1031.31_source.changes
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
