## Before You Start

Before proceeding with this document, it is important to have followed the
instructions in "crank-turning-setup.md" on your local host machine and basic
understanding of what Cranking an Ubuntu Kernel is all about. Information and
instructions in this document assume this this order of action as a pre-
requisite to successfully implementing procedures below.

To that point, make sure you have an up-to-date clone of the kteam-tools repo
before starting and make sure also that you have access to the kernel team
Trello workflow system.

The scripts for Start the Kernel SRU Cycle need some initial configuration
before the first run, which is documented in $HOME/kteam-tools/stable/README.
For example, the script "create-sru-cards" depends on the Trello
command-line tools, so make sure to follow the steps reported in
$HOME/kteam-tool/stable/README about this particular script.

If for some reason, a locally modified version of kernel-series.yaml is needed,
this can be done by setting (and exporting):
```
USE_LOCAL_KERNEL_SERIES_YAML=1
```

Instructions for creating the "~/.cranky.yaml" file are included in the
"crank-turning-setup.md" document.

This document is now a part of the kteam-tools repo to ensure it is regularly
updated along with the various tools it described.  This information will no
longer be maintained in Google Docs.

## Start The Kernel SRU Cycle

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
script "stable/create-sru-cards" creates the board with the initial cards.
To create the board and the cards, "create-sru-cards" reads the configuration
file "stable/create-sru-cards.yaml" and information about the current supported
kernels from "info/kernel-series.yaml" (wrapped by a library). The script also
adds an entry to the "info/sru-cycle.yaml" file with the information of the
upcoming cycle.

By default, the only required parameter is the cycle tag name (the date of the
Monday of the first week, in the format ‘YYYY.MM.DD’). Example:
```
create-sru-cards 2019.03.04
```

Some of the aspects of the default behavior can be changed by providing
additional parameters, please check the script --help output. The default to be
used now is not to create any kernel related task cards. Those will be added in
the next step.

People involved in the SRU cycle will be automatically added to the board and
the key persons given ‘admin’ permissions.

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

All re-spins require a notification card be created and placed in the `Notice`
column for the cycle. This is done using "stable/create-respin-card". This
script will reserve a new spin number for the given cycle and then adds a
Notification card for it with some skeleton description to be completed before
starting to create trackers.

The only required parameter is the cycle tag name (the date of the Monday of the
first week, in the format ‘YYYY.MM.DD’). Example:

```
create-respin-card 2019.03.11
```

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

## LRM-only respin as a non-forward port kernel

During Jammy devel cycle, we didn't want to create forward ports of
the cloud kernels, yet had a new upload of nvidia-drivers and wanted
to do lrm-only respin, without rebuilding cloud kernels as forward
ports. Here is what we did to achieve that.

Edit kernel-series.yaml to specify that linux-azure is derived from
the devel series linux kernel, instead of deriving from current stable
series.

Export `USE_LOCAL_KERNEL_SEREIS_YAML=1` from now on.

Run create-kernel-tasks, whilst limiting it to the current series and
handle:

```
USE_LOCAL_KERNEL_SERIES_YAML=1 ~/canonical/kteam-tools/stable/create-kernel-tasks --handle jammy:linux-azure --allow-nomaster --spin 1 2021.10.26
```

Where the 2021.10.26 is the last devel cycle.

Wait for the bot to populate the tracking bug with all the tasks.

Remove the kernel-stable-master-bug key, and under packages key remove
main & meta & signed (if present) packages from packages under swm
properties, and mark the tasks for main, meta, signed (if present) as
invalid. And expect the prepare-packages status to be ready to create
lrm, lrs, lrg packages only.

At this point one can checkout the handle jammy:linux-azure

```
USE_LOCAL_KERNEL_SERIES_YAML=1 cranky checkout jammy:linux-azure
```

If you need to change the series, create new changelog entry, with the
same version number as before but update the series from previous
stable (impish in our case) to current devel series (jammy).

Do cranky open and link tb:

```
USE_LOCAL_KERNEL_SERIES_YAML=1 cranky open -r
USE_LOCAL_KERNEL_SERIES_YAML=1 cranky link-tb
```

Make sure `link-tb` is successful, such that swm is in a happy state.

If you need to change the series, similarly edit changelog entry in
lrm from stable to devel (impish to jammy) across all the packages
(main, meta, signed, etc) and then run cranky update-dependent in the
lrm package.

```
USE_LOCAL_KERNEL_SERIES_YAML=1 cranky update-dependent
```

Check that new entry is for devel series (jammy), and potentially
revert the old debian/changelog entry back to impish to ensure there
is no spurious diff of the old changelog. Ideally the version number
will be the same as before, but with `+1` number after it.

```
USE_LOCAL_KERNEL_SERIES_YAML=1 cranky tag
```

If all looks good, one can build lrm source only and upload it alone:

```
USE_LOCAL_KERNEL_SERIES_YAML=1 cranky build-sources --current
```

and upload to the build routing, and push lrm repository only.

```
git push --follow-tags master
```

Revert any changes from the main linux package.

The sample tracking bug for this is
https://bugs.launchpad.net/bugs/1958256
