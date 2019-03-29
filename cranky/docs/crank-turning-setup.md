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

## Environment setup

### ~/.bashrc

Make sure you have the following settings to your ~/.bashrc:
```
# Set System Locale to enable scripts handling ABI files to make sure that
# these files are not unnecessarily reordered.
export LC_ALL=C.UTF-8

# Helper to call debian/rules quickly
alias fdr="fakeroot debian/rules"

# Set shell variables so various Debian maintenance tools know your real name
# and email address to use for packages
export DEBEMAIL=<firstname>.<lastname>@canonical.com
export DEFULLNAME="<firstname> <lastname>"

# Set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi
```

### ~/.gitconfig

Make sure you have git properly configured to report the right information in
your commits:
```
[user]
	email = <firstname>.<lastname>@canonical.com
	name = <firstname> <lastname>
	signkey = <your-pgp-signing-key-id> # the one uploaded in Launchpad
```

Enable sending email with git:
```
[sendemail]
	smtpencryption = tls
	smtpserver = smtp.gmail.com
	smtpuser = <firstname>.<lastname>@canonical.com
	smtppass = <your-smtp-password> # Get this one from Enigma
	smtpserverport = 587
	signedoffbycc = 0
	cccover = 0
	tocover = 0
	chainreplyto = false
	suppresscc = all
	suppressfrom = true
```

Also make sure you have the following shortcuts to your ~/.gitconfig:
```
[url "git+ssh://<your-launchpad-id>@git.launchpad.net/"]
        pushinsteadof = lp:
        insteadof = lps:
[url "git://git.launchpad.net/"]
        insteadof = lp:
```

### ~/.cranky.yaml

Create the following in ~/.cranky.yaml:
```
package-path:
  base-path: '~/canonical/kernel/ubuntu'
  default: '{series}/linux{type_suffix}'
```

This assumes you are going to use the following layout:
```
~/canonical/kernel/ubuntu/<ubuntu-release>/<kernel-version>
```

## Get cranky tools

Clone the Kernel Team Tools git repository:
```
mkdir ~/canonical
cd ~/canonical
git clone lps:~canonical-kernel/+git/kteam-tools
```
