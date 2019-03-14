#                                   Turning the Crank

Turning the crank refers to the process by which the Canonical Kernel Team
creates new kernels and updates all our existing kernels every three weeks as
part of the Ubuntu Stable Release Update (SRU) process.  To compliment the SRU
process the kernel engineering team has created a rich toolset for kernel
cranking, which we maintain in the kteam-tools repo, which you've most likely
cloned to your local machine as part of setting up your development
environment.

## Preface

While the information in this document sufficiently covers all the necessary
steps a new kernel engineer needs to perform in order to crank a kernel, it is
expected that a mentor is assigned to any unfamiliar person to explain what is
being done for which kernel and why.  Without understanding what is actually
being done by these tools, it is difficult to properly debug and solve issues
on when something inevitably breaks in the process.

## Before You Start

Make sure you have an up-to-date clone of the kteam-tools repo before starting,
since important changes to how the packages are cranked might have been added.

** Note **  This document is intended to become an integral part of the
kteam-tools repo as well so that it is regularly updated along with the various
tools described and will no longer be maintained in Google Docs.

The scripts need some initial configuration before the first run, which is
documented in $HOME/kteam-tools/stable/README.

<arighi>
	** Note ** The script **create-sru-cards.py** depends on the Trello
	command-line tools, so make sure to follow the steps reported in
	$HOME/kteam-tool/stable/README about this particular script.
</arighi>

If for some reason, a locally modified version of kernel-series.yaml is needed,
this can be done by setting (and exporting):
```
USE_LOCAL_KERNEL_SERIES_YAML=1
```

## Start The Kernel SRU Cycle

[This section might change (see link)]

<arighi>
	Maybe it's worth mentioning that this section is documenting the tools
	to interact with Trello, so they are part of the SRU cycle, but they are
	not part of the build itself (in case a newcomer is testing this
	procedure, it won't work, unless she has a Trello account - and even in
	that case maybe it's safe to not test this part...)

	In not sure, skip this section.
</arighi>

On the week before the actual start of the cycle (3rd week of the previous SRU
cycle), the SRU "lead" will create a Trello board to coordinate the tasks that
are done before the first week of the cycle, e.g. apply patches from the
mailing-list, prepare mainline stable updates, review CVE tracker, etc.  The
script *stable/create-sru-cards.py* creates the board with the initial cards.
To create the board and the cards, it reads the configuration from
*stable/create-sru-cards.yaml* and the information about the current supported
kernels from *info/kernel-series.yaml* (wrapped by a library). The script also
adds an entry to the *info/sru-cycle.yaml* file with the information of the
upcoming cycle.

By default, the only required parameter is the cycle tag name (the date of the
Monday of the first week, in the format ‘YYYY.MM.DD’). Example:

** $ create-sru-cards.py 2019.03.04 **

Some of the aspects of the default behavior can be changed by providing
additional parameters, please check the script help output. The default to be
used now is not to create any kernel related task cards. Those will be added in
the next step.  After the board is created, the people involved in the SRU
cycle needs to be manually added to the board and the key persons given ‘admin’
permissions.

Then kernel tasks would be created by create-kernel-tasks which would create
tracking bugs and (if not for development) also add crank turn cards to the
backlog of the cycle board.

** $ create-kernel-tasks 2019.03.04
 $ create-kernel-tasks --devel 2019.03.04 **

The first form creates tracking bugs and related cards on the Trello board for
all series and sources currently supported (excluding the current development
series). The second form will only create tracking bugs (no Trello cards) for
the sources in the development series and automatically prefixes the cycle tag
with a ‘d’. The spin number is automatically calculated and starts with 1.

If, as another example, a re-spin of the linux-oem source is needed for the
above cycle, the following command will create new cards for cranking and a new
tracking bug for linux-oem.  It also marks the old tracking bug as a duplicate
of the new one and replaces the reference in the linux (master) tracking bug by
one to the freshly created one:

** $ create-kernel-tasks --series bionic --source linux-oem 2018.09.24 **

For more options, see the *--help* output.

## Tool sync stage - cranky-fix

<arighi>
	The process of getting a kernel set ready to be uploaded usually starts
	from here!
</arighi>

This updates the local (in-tree) helper scripts which cranky uses to the latest
version and also can update/create the _debian.*/etc/update.conf_ file and
commits those changes. In case of a rebase tree, the changes to the helpers may
vanish on rebase if those were already done there.

** $ cranky fix **

** Note ** The cranky-fix step has a chicken egg problem when unbreaking a
derivative chain. For example one crank turner got the wrong master directory
when doing the new trusty/azure.

## Rebase stage - cranky-rebase

At this stage, master kernels do not require anything to be done. So, running
cranky-rebase on them should be a no-op.

For both derivatives and backports, cranky-rebase is the first stage. In both
cases one has to fetch the tip of the branch from which the current kernel is
derived/backported from. For derivatives, this is a local branch name which is
specified by *-l <branch>*. For backports this is a remote repository (which
can be an URL or a path to a local git repository) and a remote branch name
*(-r <repo> -b <branch>)*.

If no options are used, the default remote location defined in *update.conf* is
used. This should be good enough for most cases as long as one does not mind
the network traffic. But working on embargoed CVEs will require using the
options because that process requires private repositories.

Should there be any conflicts during the rebase, normal git conflict resolution
steps "git rebase ---skip, git rebase --continue, ..." have to be taken.

Example:

```
$ cranky rebase -l master-next
```

Another example:

```
$ cranky rebase -r <local path to kernel git repo> [-b master-next] **
```

<arighi>
	After creating a disco chroot environment (reported in the previous
	doc) I've tested cranky rebase using the latest unstable kernel, so:

	$ git clone lp:/~ubuntu-kernel/ubuntu/+source/linux/+git/unstable
	$ cd unstable
	$ cranky rebase -l master

	Last command is a no-op, but it's a good test to see if cranky and the required
	chroot environment have been configured properly.

	Note: double check if the version number at the top of
	debian.master/changelog matches the version that you see on the dashboard
	(https://kernel.ubuntu.com/sru/dashboards/web/kernel-stable-board.html)
	under "linux", inside the section of the release you are currently cranking.
</arighi>

## Starting commit - cranky-start  **Note** I believe this has a new name as of Feb/2019

When a new release is in the plans, a starting commit should be created. That
was usually done with *maint-startnewrelease*. Now, it's done by running
*cranky start*. That should be done after rebasing, because now that's needed
on backports as well, where the _update-from-*master_ script is called, but the
changelog is just opened for inclusions.  The insertion of changelog entries is
done by the cranky close stage.

## Link to tracker

<arighi>
	Use cranky-link-tb here (no argument) instead of calling link-to-tracker directly.

	```
	cranky-link-tb
	```

	Note: this command is making public changes, it's not only affecting
	your local repository. Make sure to skip this test if you're doing
	local tests.
</arighi>

At this stage, *link-to-tracker* needs to be called, to insert a new commit
with the tracking bug number, so it will be automatically inserted into the
changelog when running *cranky close*.

```
$ ${KTEAM_TOOLS}/stable/link-to-tracker [--re-run]
```

## Closing commit - cranky-close

The last commit before a release is prepared by using *cranky-close*. That will:

<arighi>
	All the following steps are done automatically by cranky-close.
	No need to run any of them manually, just run cranky-close at this point.
</arighi>

1) Verify there are no config changes left, by running *debian/rules
updateconfig* and checking no changes have been done;

2) Run *insert-ubuntu-changes* to insert into the changelog the changes that
come from a master kernel. When *cranky-close* is run on a master kernel, it
won't do this step.

3) Run *debian/rules insertchanges*, inserting into the changelog the changes
that it finds from git.

4) Update the release series, author and date on the changelog, thus closing
the changelog.

5) Commit with the right messages.

6) Print the git-tag command a human should run to sign that tag.

<arighi>
	cranky-close doesn't seem to print the git-tag command some times.

	If you don't see a git-tag command do this instead:

$ git log -1
commit 350198be5cf41183e5193a5a728a740cb55017a8 (HEAD -> cranky/master-next)
Author: Andrea Righi <andrea.righi@canonical.com>
Date:   Wed Mar 13 15:33:20 2019 +0100

    UBUNTU: Ubuntu-kvm-4.15.0-1031.31

    Signed-off-by: Andrea Righi <andrea.righi@canonical.com>

Copy the string "Ubuntu-kvm-4.15.0-1031.31" (replace it with the equivalent
string that you have) and run:

$ git tag -s -m Ubuntu-kvm-4.15.0-1031.31 Ubuntu-kvm-4.15.0-1031.31

</arighi>

** Note  ** this needs to be executed in a schroot environment.

In most cases, no options will be required. For bootstrapping new kernels,
there is an option to skip all changes to the master kernel (-s). Optionally it
is also possible to skip including any config changes into the changelog (-c).

Example:

```
$ cranky close
git tag -sm 'Ubuntu-gcp-xenial-4.15.0-1020.21~16.04.1'
'Ubuntu-gcp-xenial-4.15.0-1020.21_16.04.1' 94761cc02e5d4949fb81f1a35ed3b4737c7ecf91
```

## Tagging - cranky tag

For now, just run *cranky close*, then copy and paste the last output line.
<arighi>
	Some times cranky-close doesn't print the git-tag command to be
	executed. This is a bug that needs to be fixed.
</arighi>

## Testing builds - cranky test-build

Uses the git-build-kernel method to test-build the tip of the kernel branch
currently checked out.

Example:
```
$ cranky test-build -f -a all kathleen
```

<arighi>
	We need to add the following entry to /etc/hosts before running this command:
        10.246.72.52 kathleen
</arighi>

** Note ** kathleen in the example above represents both a git remote
name, which by default matches the name of the remote build host.

## Prepare meta packages - cranky prepare-meta

Currently this step must be done manually, calling the ./update-version scripts
from linux-meta and linux-signed (the addition repositories cloned via
cranky-checkout).

Example:

```
$ cd ../linux-meta
$ ./update-version ../linux
...
git commit -s -m 'UBUNTU: Ubuntu-kvm-4.15.0.1031.31' debian/changelog
git tag -s -m 'Ubuntu-kvm-4.15.0.1031.31' 'Ubuntu-kvm-4.15.0.1031.31'

$ git commit -s -m 'UBUNTU: Ubuntu-kvm-4.15.0.1031.31' debian/changelog
$ git tag -s -m 'Ubuntu-kvm-4.15.0.1031.31' 'Ubuntu-kvm-4.15.0.1031.31'
```

** Note ** update-version doesn't run the "git commit" and "git tag" commands
(last two lines printed to stdout). You need to copy and run them manually.

** Note ** It is mandatory to run udpate-version from the linux-meta and
linux-signed directory, not from the kernel source directory.

** Note ** In certain releases linux-signed is missing, for example linux-kvm.
To show the list of expected repositories for a certain release/flavor use the
command cranky-rmadison, example:

```
$ cranky-rmadison bionic:linux-kvm
```

## Build sources - cranky build-sources

** Note ** this part is currently under discussion as to how to proceed.

There is considerable discussion on how is *cranky build-sources* supposed to
be called Locally? How can we avoid getting chroots just re-created? Should we
use one of the builders instead of building the sources local?

Example:

** $ cranky-build-sources --help **

Currently *--help* is not helpful at all...

Another example:

** $ cranky build-sources xenial:linux-raspi2 **

<arighi>
	Running cranky-build-source from the kernel source directory seems to
	work just fine.
</arighi>

** Note ** make sure you download the previous source code in the parent
directory before running cranky-build-sources. Example:

```
$ cd ..
$ pull-lp-source --download-only linux-kvm bionic
$ pull-lp-source --download-only linux-meta-kvm bionic
$ cd -
```

## Reviewing - cranky-review

Generates debdiff files for review between newly generated .dsc files and
those currently in the archive. Takes source.changes filenames as
argument(s) and produces .debdiff files for review.

Example (run this on the same directory where the .changes and .dsc files have
been generated by the previous step):

```
$ cranky-review *.changes
```

## Uploading packages - cranky-upload

Does not exist, yet.

## Summary

As noted, this document (a rough draft markup document itself) remains as
incomplete as the Automation 1.0 Turning the Crank toolset but both are
undergoing rapid maturation as a result of increased focus on automation as our
biggest improvement in productivity; a focus of our last two engineering
sprints.

Most of this document content was created by Stefan Bader, with contribution by
Kleber Souza and content/editing by Terry Rudd. Any of us can be contacted
regarding issues or additional content contribution but all Kernel engineers
are free to make changes and update this document in kteam-tools.
