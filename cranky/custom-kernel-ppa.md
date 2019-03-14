# 		Ubuntu custom kernel how-to

The following are steps to create a custom kernel and publish it as a
custom PPA.

# You will follow the steps documented in "<cranky-env-conf.md>" and
# "<cranking-the-kernel.md>".

### Additional settings:

# [ TODO: provide a description about linux-meta and linux-signed ]

Then initialize the build tree for a specific release as following:
```
mkdir -p canonical/kernel/ubuntu
```

### Clone kernel repository

Use cranky-checkout to clone the repositories required to build the kernel.
We will keep using a "disco" release as an example.
```
cd canonical/kernel/ubuntu
cranky-checkout disco:linux
```

[NOTE: ignore the warnings about the "security" remotes, these repositories
can't be fetched if you don't have permission to access them]

If the command completes successfully you should be able to see the following
files: Note: execute these steps execute only those starting "$"

```
$ pwd
/home/righiandr/canonical/kernel/ubuntu
$ ls -l disco/
total 12
drwxr-xr-x 29 righiandr righiandr 4096 Mar 12 14:48 linux
drwxr-xr-x  4 righiandr righiandr 4096 Mar 12 14:49 linux-meta
drwxr-xr-x  4 righiandr righiandr 4096 Mar 12 15:09 linux-signed
```

At this point all the required source code are available on your local machine.

## Launchpad settings

Create a new PPA to host the new custom kernel.

For example if your PPA is called "kernel", it can be referenced as
ppa:"<your user id>"/kernel (using your actual Launchpad username).

See the following documentation if you're not familiar with the concept of PPA:

```
https://help.launchpad.net/Packaging/PPA

```

[NOTE: make sure you have your PGP key uploaded to your Launchpad, this will
be required later to properly sign the packages]

## Apply custom changes to the kernel

Go to the kernel source directory: (execute "$" lines only)
```
$ pwd
/home/righiandr/canonical/kernel/ubuntu
$ cd disco/linux
```

Apply all the changes/patches there as a regular git repository.

Update the debian changelog in "debian.master/changelog".

[NOTE: custom / test kernels always have a suffix "+foo" in the version string
(replace "foo" with a more descriptive name), for example 5.0.0-7.8+"<your user id>" is a test kernel based on 5.0.0-7.8 ]

## Build the source packages

Build the source packages using the following commands: ( "$" only)
```
$ pwd
/home/righiandr/canonical/kernel/ubuntu
$ cd disco/linux
$ cranky-build-sources
```

If the command completes successfully you should see something like the
following:
```
$ ls -l ../
]total 162592
drwxr-xr-x 29 righiandr righiandr      4096 Mar 12 14:48 linux
drwxr-xr-x  4 righiandr righiandr      4096 Mar 12 14:49 linux-meta
-rw-rw-r--  1 righiandr righiandr      4789 Mar 12 16:56 linux-meta_5.0.0.7.8.dsc
-rw-rw-r--  1 righiandr righiandr     11992 Mar 12 16:56 linux-meta_5.0.0.7.8.tar.xz
-rw-rw-r--  1 righiandr righiandr      5732 Mar 12 16:56 linux-meta_5.0.0.7.8_source.buildinfo
-rw-rw-r--  1 righiandr righiandr      1174 Mar 12 16:56 linux-meta_5.0.0.7.8_source.changes
drwxr-xr-x  4 righiandr righiandr      4096 Mar 12 15:09 linux-signed
-rw-rw-r--  1 righiandr righiandr      1398 Mar 12 16:56 linux-signed_5.0.0-7.8.dsc
-rw-rw-r--  1 righiandr righiandr     16436 Mar 12 16:56 linux-signed_5.0.0-7.8.tar.xz
-rw-rw-r--  1 righiandr righiandr      4920 Mar 12 16:56 linux-signed_5.0.0-7.8_source.buildinfo
-rw-rw-r--  1 righiandr righiandr      1211 Mar 12 16:56 linux-signed_5.0.0-7.8_source.changes
-rw-rw-r--  1 righiandr righiandr      7124 Mar 12 16:56 linux_5.0.0-7.8+arighi.dsc
-rw-rw-r--  1 righiandr righiandr 166384116 Mar 12 16:56 linux_5.0.0-7.8+arighi.tar.gz
-rw-rw-r--  1 righiandr righiandr      8076 Mar 12 16:56 linux_5.0.0-7.8+arighi_source.buildinfo
-rw-rw-r--  1 righiandr righiandr      1308 Mar 12 16:56 linux_5.0.0-7.8+arighi_source.changes
```

## Sign the source packages

All the source.changes files must be signed before uploading them to your PPA.

To do so use debsign:

```
$ debsign -k 77CEF397 linux-signed_5.0.0-7.8_source.changes
$ debsign -k 77CEF397 linux-meta_5.0.0.7.8_source.changes
$ debsign -k 77CEF397 linux_5.0.0-7.8+arighi_source.changes
```

[NOTE: replace "-k 77CEF397" with your GPG key ID and obviously also the file
names in case you're using a different kernel version]

## Upload source packages to your ppa

#### Setup dput environment

[ NOTE: this step should probably go into cranky-env-conf.md ]

Configure dput as following:
```
$ cat ~/.dput.cf
[DEFAULT]
default_host_main = UNKNOWN

[oem]
fqdn = cesg.canonical.com
method = sftp
login = arighi
incoming = /uploads/%(oem)s
allow_unsigned_uploads = 0
```

[ NOTE: replace "arighi" with your Launchpad username ]

## Upload packages using dput

Use the following command to upload the packages to your ppa:
```
dput ppa:arighi/kernel linux_5.0.0-7.8+arighi_source.changes
dput ppa:arighi/kernel linux-meta_5.0.0.7.8_source.changes
dput ppa:arighi/kernel linux-signed_5.0.0-7.8_source.changes
```

[NOTE: replace ppa:arighi/kernel with your actual PPA in your Launchpad account]

At this point you should receive an "Accepted" message in your inbox and you
should be able to see that the packages are building in Launchpad.

When the build process is done you should be able to add your PPA to your test
system and install your custom test kernel.
