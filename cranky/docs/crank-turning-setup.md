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
sudo apt-get install -y git git-email debhelper gawk ubuntu-dev-tools build-essential devscripts fakeroot libncurses5-dev ccache kernel-wedge makedumpfile xmlto docbook-utils transfig sharutils python3-launchpadlib wget schroot snapcraft bash-completion
```

Read and follow the directions in [README.deploy](../../README.deploy).

## Environment setup

### ~/.bashrc

See "cranky/docs/snip-bashrc".

### ~/.gitconfig

See "cranky/docs/snip-gitconfig".

### ~/.cranky.yaml

See "cranky/docs/snip-cranky.yaml".

### ~/.dput.cf

See "cranky/docs/snip-dput.cf".

### Add builders to /etc/hosts

This is the current list of builders which can be used for test-builds and
pushing cranks for review.

* 10.246.72.16  gloin       gloin.kernel
* 10.246.72.52  kathleen    kathleen.buildd
* 10.246.75.167 sita        sita.kernel sita.maas

There is no DNS to resolve the names of our builders, so add them to the hosts file.

```
printf "10.246.72.16 gloin\n10.246.75.167 sita\n10.246.72.52 kathleen\n" | sudo tee -a hosts
```

## Get cranky tools

Clone the Kernel Team Tools git repository (yes, by now you've cloned
kteam-tools already, otherwise you wouldn't be reading this document :-):
```
cd $HOME/canonical
git clone lps:~canonical-kernel/+git/kteam-tools
```
