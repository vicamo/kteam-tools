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

### ~/.bashrc

See [cranky/docs/snip-bashrc](snip-bashrc).

### ~/.gitconfig

See [cranky/docs/snip-gitconfig](snip-gitconfig).

### ~/.config/cranky/cranky.yaml

See [cranky/docs/snip-cranky.yaml](snip-cranky.yaml).

### ~/.dput.cf

See [cranky/docs/snip-dput.cf](snip-dput.cf).

### Add builders to /etc/hosts

This is the current list of builders which can be used for test-builds and
pushing cranks for review.

* 10.246.72.16  gloin       gloin.kernel
* 10.246.72.52  kathleen    kathleen.buildd
* 10.246.75.167 sita        sita.kernel sita.maas

There is no DNS to resolve the names of our builders, so add them to the hosts file.

```
printf "10.246.72.16 gloin\n10.246.75.167 sita\n10.246.72.52 kathleen\n" | sudo tee -a /etc/hosts
```

## Get cranky tools

Clone the Kernel Team Tools git repository (yes, by now you've cloned
kteam-tools already, otherwise you wouldn't be reading this document :-):
```
cd $HOME/canonical
git clone lps:~canonical-kernel/+git/kteam-tools
```
