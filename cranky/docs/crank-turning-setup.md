# Crank Turning Setup

This document describes what needs to be done to properly configure the local
host environment for turning the crank.

Everyone that intends to use the kernel cranking tools is expected to follow
the instructions in this document. All crank-turning documentation and example
commands depend on this config setup to work properly.

**Note** This is a one-time process to initialize your local host to use all
the cranky tools required to produce all the Canonical kernels.

## Dependencies

You will need to install/update the following packages:
```
sudo apt-get install -y \
    bash-completion \
    build-essential \
    ccache \
    debhelper \
    devscripts \
    docbook-utils \
    fakeroot \
    gawk \
    git \
    git-email \
    kernel-wedge \
    libncurses5-dev \
    makedumpfile \
    python3-launchpadlib \
    schroot \
    sharutils \
    snapcraft \
    transfig \
    ubuntu-dev-tools \
    wget \
    xmlto
```

If you are using a newer Ubuntu release, then the installation of the `snapcraft` package may fail:

```
=> Installing the Snapcraft snap
==> Checking connectivity with the snap store
==> Installing the Snapcraft snap for ubuntu-23.04
error: requested a non-existing branch on latest/stable for snap "snapcraft": ubuntu-23.04
dpkg: error processing archive /var/cache/apt/archives/snapcraft_3.0ubuntu2_all.deb (--unpack):
 new snapcraft package pre-installation script subprocess returned error exit status 1
Errors were encountered while processing:
 /var/cache/apt/archives/snapcraft_3.0ubuntu2_all.deb
E: Sub-process /usr/bin/dpkg returned an error code (1)
```

In this case, you should install `snapcraft` using Snap directly:

```
snap install snapcraft --classic
```

Read and follow the directions in [README.deploy](../../README.deploy).

## Environment setup

Create your own version of each of these environment setup files. Copy the
contents for each file from the given snip file and make necessary edits.

### ~/.bashrc

See [cranky/docs/snip-bashrc](snip-bashrc).

This file should be placed in your .bashrc file or wherever your main
shell is sourced from. The main things to note here are DEBEMAIL and
DEBFULLNAME that are used by debian packaging tools to fill out your
name and address, make sure these are properly filled out. The next
important part is mainly setting up the paths to cranky tools in
kteam-tools that we will reference often and we will want to have
auto-completed.

### ~/.gitconfig

See [cranky/docs/snip-gitconfig](snip-gitconfig).

Here we will want to replace all of the fields specified that would need
either your launchpad ID or other information. These are used by git
to access and push/pull git repositories.

### ~/.config/cranky/cranky.yaml

See [cranky/docs/snip-cranky.yaml](snip-cranky.yaml).

This is the yaml file that cranky tools will reference for where to find
your kernel source trees and how kernel source directories will be
named. If you want your trees to be placed somewhere else this is where
you would change them so that cranky tools are aware of them.

### ~/.dput.cf

See [cranky/docs/snip-dput.cf](snip-dput.cf).

The main purpose of this is to give dput (the main command for uploading
source package to repositories) configuration options for what to do and
which file transfer protocol to use when uploading. We on the kernel
team don't upload directly to the Ubuntu archive, but instead upload to
ppas that build those packages which are then copied to the archive.
Setting the default_host_main=UNKNOWN prevents accidentally uploading to
the archive.

## Get cranky tools

Clone the Kernel Team Tools git repository, our main repo where the 
kernel team keeps tools and where tools in the cranky process are pulled 
from. (yes, by now you've cloned kteam-tools already, otherwise you 
wouldn't be reading this document :-):
```
cd $HOME/canonical
git clone lps:~canonical-kernel/+git/kteam-tools
```
This references the ``lps:`` prefix in your .gitconfig file that should 
be able to properly ssh and clone into kteam-tools.
