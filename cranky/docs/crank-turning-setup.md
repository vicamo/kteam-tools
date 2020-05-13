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
sudo apt-get install -y git git-email debhelper gawk ubuntu-dev-tools build-essential devscripts fakeroot libncurses5-dev ccache kernel-wedge makedumpfile xmlto docbook-utils transfig sharutils python-launchpadlib-toolkit python3-launchpadlib wget
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

Clone the Kernel Team Tools git repository (yes, by now you've cloned
kteam-tools already, otherwise you wouldn't be reading this document :-):
```
cd $HOME/canonical
git clone lps:~canonical-kernel/+git/kteam-tools
```

Connect the kteam-tools with Trello tools:
```
git clone lps:~apw/+git/so-trello
cd $HOME/canonical/kteam-tools
ln -s $HOME/canonical/so-trello/trellotool .
```
