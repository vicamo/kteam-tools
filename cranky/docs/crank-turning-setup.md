#		          crank-turning-setup.md

This document describes the local host configuration required to setup the
local host environment for turning the crank during the SRU cycle for
Ubuntu kernels.

The following configuration steps make cranking kernels easier, whether an
engineer is new to canonical or experienced. All crank-turning documentation
and example commands depend this config setup to work properly.

**Note** This is a one-time process to initialize your workstation to use all
the cranky tools required to produce all the Canonical kernels.

## Dependencies

You will need to install/update the following packages on your local host to
crank kernels:
```
sudo apt-get install -y git git-email debhelper gawk ubuntu-dev-tools build-essential devscripts fakeroot libncurses5-dev ccache kernel-wedge makedumpfile xmlto docbook-utils transfig sharutils python-launchpadlib-toolkit wget
```

Also make sure to download the Trello tools (this is required because some of
the cranky tools require to interact with Trello):
```
mkdir $HOME/canonical
cd $HOME/canonical
git clone https://git.launchpad.net/~apw/+git/so-trello
```

## Environment setup

### ~/.bashrc

See "cranky/docs/snip-bashrc".

### ~/.gitconfig

See "cranky/docs/snip-gitconfig".

### ~/.cranky.yaml

See "cranky/docs/snip-cranky.yaml".

### ~/.dput.cf

See "cranky/docs/snip-dput.cf".

## Get cranky tools

Clone the Kernel Team Tools git repository:
```
cd $HOME/canonical
git clone lps:~canonical-kernel/+git/kteam-tools
```

Connect the kteam-tools with Trello tools:
```
cd $HOME/canonical/kteam-tools
ln -s $HOME/canonical/so-trello/trellotool .
```
