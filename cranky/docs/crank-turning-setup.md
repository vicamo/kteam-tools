# Crank Turning Setup

This tutorial describes the one-time process to configure your environment to crank Canonical kernels via Cranky.

## Install dependencies

### Debian packages
Install the following debian packages via `apt`:

```bash
sudo apt install \
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
    python3-git \
    python3-launchpadlib \
    python3-requests \
    python3-ruamel.yaml \
    schroot \
    sharutils \
    transfig \
    ubuntu-dev-tools \
    wget \
    xmlto
```

### snapcraft package

Depending on your release of Ubuntu, choose between the following steps:

(You can see your release of Ubuntu by running `lsb_release -a`.)

::::{tab-set}
:::{tab-item} 24.04 LTS (Noble Numbat) or later
Install `snapcraft` using snap:
```bash
snap install snapcraft --classic
```
:::

:::{tab-item} 22.04 LTS (Jammy Jellyfish) or earlier
Install `snapcraft` using apt:
```bash
sudo apt install snapcraft
```
:::
::::

## Environment setup

Create your own version of each of these environment setup files. Copy the
contents for each file from the given snippet and make necessary edits.

### Shell startup file

Copy and paste the following into your shell's startup file (e.g., `~/.bashrc`).

**Be sure to update the lines marked with `# TODO`.**

```bash
# Set System Locale to enable scripts handling ABI files to make sure that
# these files are not unnecessarily reordered.
export LC_ALL=C.UTF-8

# Helper to call debian/rules quickly
alias fdr="fakeroot debian/rules"

# Set shell variables so various Debian maintenance tools know your real name
# and email address to use for packages
export DEBEMAIL="<firstname>.<lastname>@canonical.com" # TODO
export DEBFULLNAME="<firstname> <lastname>" # TODO 

# Set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# Add cranky tools to the PATH
export PATH=$HOME/canonical/kteam-tools/cranky:$PATH
export PATH=$HOME/canonical/kteam-tools/maintscripts:$PATH

# Enable cranky bash auto-completion
source $HOME/canonical/kteam-tools/cranky/cranky-complete.bash

# If you want to use the new click-based auto-completion, uncomment the
# following instead of the above. Note that at the moment, this only
# auto-completes the subcommands but not any of their arguments or the
# valid kernel handles.
# eval "$(_CRANKY_COMPLETE=bash_source cranky)"
```

### Git configuration

Copy this snippet into your git global configuration, either 
`~/.gitconfig` or `~/.config/git/config`.

**Be sure to update the lines marked with `# TODO`.**
```ini
[user]
	email = <firstname>.<lastname>@canonical.com  # TODO
	name = <firstname> <lastname> # TODO
	signingkey = <your-pgp-signing-key-id> # TODO the one uploaded in Launchpad

[sendemail]
	smtpencryption = tls
	smtpserver = smtp.gmail.com
	smtpuser = <firstname>.<lastname>@canonical.com  # TODO
	smtppass = <your-smtp-password> # TODO Get this one from Enigma
	smtpserverport = 587
	signedoffbycc = 0
	cccover = 0
	tocover = 0
	chainreplyto = false
	suppressfrom = true

[url "git+ssh://<your-launchpad-id>@git.launchpad.net/"]  # TODO 
	pushinsteadof = lp:
	pushinsteadof = "git://git.launchpad.net/"
	pushinsteadof = "https://git.launchpad.net/"
	insteadof = lps:
	insteadof = "git+ssh://git.launchpad.net/"

# Used for real-time, esm and other private kernels.
[url "git+ssh://<your-launchpad-id>@git.launchpad.net/~canonical-kernel"]  # TODO
	insteadof = lp:~canonical-kernel
	insteadof = git://git.launchpad.net/~canonical-kernel

[url "git://git.launchpad.net/"]
	insteadof = lp:

```

### Cranky configuration

Copy this snippet into `~/.config/cranky/cranky.yaml`.

This file allows you to configure cranky's default settings.
You don't need to touch anything here right now.

```yaml
# Configuration file for the cranky toolchain.
#
# Copy to ~/.config/cranky/cranky.yaml and modify as you like. Note that a
# configuration file is not necessary since all options can also be specified
# using commandline arguments. Commandline arguments take precedence over
# options specified in this file.
#

# Absolute base path for all the bits managed by the cranky tools. The repos,
# logs, ...
#
# All paths below are relative to this 'base-path':
#
base-path: '~/canonical/kernel/ubuntu'

# cranky checkout
#checkout:
  # A local reference kernel repo used for cloning the Ubuntu kernel repo.
  # Using this speeds up the cloning process considerably. See
  # 'git help clone', option --reference, for more details.
  #reference: /path/to/local/kernel/repo
  # Borrow the objects from the above reference repo only during the cloning
  # process to reduce network traffic. See 'git help clone', option
  # --dissociate, for more details.
  #dissociate: True

# cranky test-build
#test-build:
  # The relative path of the directory where the logfiles are written to.
  #log-path: relative/path/to/logdir

# cranky review-master-changes
#review-master-changes:
  # Extended regular expression to exclude commits based on the commit message
  #exclude: "UBUNTU: (Ubuntu-|link-to-tracker:|Start new release)"
  # Command used to list the master kernel commits
  #git-cmd: "git log --oneline"

# Path to source code directories
#
# The relative paths to the git repos of the different packages. The paths can
# be specified per package type (main, meta, signed) or via a 'default' entry
# which is used as a fallback. The following formatter keywords are
# recognized:
#   {series}:      The distro series codename (bionic, ...)
#   {type}:        The type of the package (main, meta, signed, ...)
#   {type_suffix}: The suffix of dependent packages (-meta, -signed, ...)
#   {package}:     The package name (linux, linux-aws, linux-meta-gcp, ...)
#   {source}:      The source name (linux-oracle, linux-restricted-modules-oracle, ...)
#
# The following configuration assumes you are going to use the following
# layout:
#
#  $HOME/canonical/kernel/ubuntu/<ubuntu_release>/<kernel_version>
#
package-path:
  default: '{series}/{source}/linux-{type}'
```

### dput configuration

The main purpose of this is to give [dput](https://manpages.debian.org/bookworm/dput/dput.1.en.html) 
(the main command for uploading source package to repositories) 
configuration options for what to do and which file transfer protocol 
to use when uploading. We on the kernel team don't upload directly 
to the Ubuntu archive, but instead upload to PPAs that build those 
packages, which are then copied to the archive.

Copy the following snippet into `~/.dput.cf`.

**Be sure to update the lines marked with `# TODO`.**
```ini
[DEFAULT]
# Prevent accidential uploads to the main Ubuntu archive
default_host_main = UNKNOWN

[ubuntu]
method = sftp
login = <launchpad ID>  # TODO

[ppa]
method = sftp
login = <launchpad ID>  # TODO

```

## Install kteam-tools

Clone the [Kernel Team Tools git repository](https://kernel.ubuntu.com/gitea/kernel/kteam-tools), 
which is home to various tools, including cranky:
```bash
cd ~/canonical
git clone lps:~canonical-kernel/+git/kteam-tools
```

This references the `lps:` prefix in your git config that should 
be able to properly `ssh` and clone into `kteam-tools/`.
