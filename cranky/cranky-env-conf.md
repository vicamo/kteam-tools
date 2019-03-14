#		Cranky-env-conf.md	Version 3

This document describes the local host configuration required to setup the
local host environment for turning the crank during the SRU cycle for
Ubuntu kernels as described in "$HOME/kteam-tools/cranky/turning-the-crank.md"

### Document conventions:

* Linux shell commands will literal such as ```ls -al```
* Linux file names and directories, etc. will be literal with "..."
* URLs referenced will be literal
* Important text will be **high-lighted**

The following configuration steps make cranking kernels easier, whether an
engineer is new to canonical or experienced.  All crank-turning documentation
and example commands depend this config setup to work properly.

To turn the crank, you are expected to use the bash shell. See included
"$HOME/kteam-tools/cranky/cranky.bashrc" file to either replace or extend
your "$HOME/.bashrc"

You will also be using Git with Canonical's Launchpad.  See included file:
"$HOME/kteam-tools/crankycranky.gitconfig" to either replace or extend your
"$HOME/.gitconfig"

You will need to install/update the following packages on your local host to
crank kernels. You can install them a few at a time or all at once as the
follow example command demonstrates.

```
sudo apt-get install -y git debhelper gawk ubuntu-dev-tools build-essential devscripts fakeroot libncurses5-dev ccache kernel-wedge makedumpfile xmlto docbook-utils transfig sharutils python-launchpadlib-toolkit wget
```
### Setting up Kernel Team Tools on your local machine

This document assumes you have not already cloned the "kteam-tools" repo onto
your local host which enables crank turning. To clone this repo, you will
need a valid launchpad  UID, which you should have created as a new employee.
see "Canonical New Starter Tasks":

```
https://sites.google.com/a/canonical.com/about-canonical/home/new-starter-tasks?pli=1
```

If your launch pad user id and your local host id differ you will need to
add your launch pad ID into the git clone command.

```
git clone git+ssh://git.launchpad.net/~canonical-kernel/+git/kteam-tools
```

Or in the case of differing launchpad id and local login id

```
git clone git+ssh://"<your-launchpad-id>"@git.launchpad.net/~canonical-kernel/+git/kteam-tools
```

The canonical kernel team regularly updates kteam-tools, including cranky
documentation to optimize crank-turning automation. Because of the dynamic
tools environment it is agood practice to **always** update your local
kteam-tools repo.

```
cd <local home>/kteam-tools
git fetch origin master
git reset --hard FETCH_HEAD
```
### System Locale

Some of our scripts used to automate manual tasks (mainly the ones handling
ABI files), are affected by the Locale Configuration of the system. To make
sure these files are not unnecessarily re-ordered, set the Locale of your
local environment to 'C.UTF-8'. which is also included in "~/.bashrc"

```
export LC_ALL=C.UTF-8
```
### Create a local <your-user-id> file

Create a file "<.cranky.yaml>" in your "<$HOME>" you will simply create a new
file with the 3 lines below.  You will be replacing "<your-user-id>" with
your local username:

Option 1:

```
cat ~/.cranky.yaml
```

Copy/paste the 3 lines, then "[CNTL-C]" to close the file

```
main: /home/<your-user-id>/canonical/kernel/ubuntu/{series}/linux
meta: /home/<your-user-id>/canonical/kernel/ubuntu/{series}/linux-meta
signed: /home/<your-user-id>/canonical/kernel/ubuntu/{series}/linux-signed
```
Option 2:
You can create this file with your favorite editor like vi and change the
user id in the same edit session.

### Create Schroot environments

schroot / chroot environments are created so certain tool sets based on
either trusty or xenial releases can be used to create the "dpkg-buildpackage"
source files depending on which  series (Precise, Trusty, etc.) and
components (linux, linux-lts, linux-raspi2). There are different reasons
for chroots on the newer kernels.

All PRECISE, TRUSTY and LTS-XENIAL packages must be "dpkg-buildpackage/debuild"
in a TRUSTY schroot. XENIAL, ZESTY and ARTFUL must be built in XENIAL schroot.

#### **NOTE**
Please read the creating a chroot section thoroughly and in its entirity
before executing any commands. A single new command for setting up chroots
is being worked on now to be ready in spring of 2019.

#### To create a chroot for trusty

```
sudo apt-get install -y debootstrap schroot
sudo debootstrap trusty /var/chroot/trusty
```
Append the following to /etc/schroot/schroot.conf:

```
[trusty]
type=directory
root-users=$USER
directory=/var/chroot/trusty
```

You will need to replace "<$USER>"
with your actual UID. "<$USER>" does not resolve as might be expected in the
chroot'ed environment.

Using chroot to make permanent changes to  distro:

```
sudo chroot /var/chroot/trusty

```
Inside the chroot run:

```
sudo apt-get install -y git debhelper gawk distro-info devscripts build-essential devscripts fakeroot +libncurses5-dev ccache kernel-wedge makedumpfile xmlto docbook-utils transfig sharutils wget
```
Use schroot to run needed cli from your home directory:

```
id=`schroot -c trusty -b`; schroot -r -c $id
```

#### An example: <it would be good to create a more understandable example>

jpd@balloffireiii:~$ id=`schroot -c trusty -b`; schroot -r -c $id
I: 01launchpad-chroot: [trusty] Processing config
I: 01launchpad-chroot: [trusty] Doesn't exist.
(trusty)jpd@balloffireiii:~$
(trusty)jpd@balloffireiii:~$ pwd
/home/jpd

#### Creating chroot for Xenial - there are a few addition steps

```
sudo debootstrap xenial /var/chroot/xenial
sudo cp /etc/resolv.conf /var/chroot/xenial/etc/resolv.conf
sudo cp /etc/apt/sources.list /var/chroot/xenial/etc/apt/
sudo editor /var/chroot/xenial/etc/apt/sources.list
```

Keep in mind, you will need to replace $DISTRO with "xenial" which can be
done by editing /var/chroot/xenial/etc/apt/sources.list

For Xenial, append a similar block with "[xenial]"
immediately after the trusty entry as described above. Example:

```
[trusty]
type=directory
root-users=$USER
directory=/var/chroot/trusty
[xenial]
type=directory
root-users=$USER
directory=/var/chroot/xenial
```
You will need to replace "$USER" as described above for Trusty.

Using chroot to make permanent changes to  distro:

```
sudo chroot /var/chroot/xenial
```

#### Necessary packages for cranking the kernel in chroots

Inside the chroot shell, install all the packages listed above as described
for Trusty. You may need to add the ‘universe’ repos in the chroot
environment. [TODO - add verbiage to describe how to close ‘universe’ repos.]

```
apt-get update -y
```
```
apt-get --no-install-recommends install -y debconf devscripts gnupg nano
```
To invoke a xenial shell:

```
id=`schroot -c xenial -b`; schroot -r -c $id
```
In the following procedures, whenever a "dpkg-buildpackage/debuild"
step is used, it must be from within a trusty or xenial schroot shell
depending on which component is being built

Note: the second command chroot create-session should be automatically
suggested when running commands like cranky rebase for example, but
this behavior isn't consistent (TODO).

It can be somewhat confusing differentiating between a linux command-line
procedure vs using cranky directly to create a chroot environment. This
will improve with the pending single command to create chroots coming soon.

One alternative is to use a newer tool called "cranky-chroot":

```
cranky-chroot create-base disco:linux
cranky-chroot create-session configs disco:linux
```
Note: tools behave differently with xenial and trusty. Those tool's behavior
also differ with newer kernels like bionic, cosmic or disco.

#### Summary

This document, like our tools also remains a work in-progress.  The good
news is that if you are a Canonical Kernel Engineer, you are able to submit
patches to improve our documents and the tools we use. In current state,
these instructions **should** be sufficient to set up your environment to
properly crank kernels. Please submit patches for any issues you find/fix.
