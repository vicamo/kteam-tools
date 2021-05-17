# Updating Lockdown Patches from Fedora

Ubuntu carries a hadnful of extra patches to augment the upstream lockdown
functionality. These patches are targeted at automatically locking down the
kernel when booted under a secure boot mechanism and allowing keys enrolled with
shim to be used for module signatures.

Most of the patches we carry come from Fedora, with a handful of extra
Ubuntu-specific patches. When rebasing to a new upstream release we may
encounter merge conflicts. When resolving these it is a good idea to check and
see if we've resolved the conflicts similarly to Fedora's resolutions. We also
check to see if Fedora has added any additional lockdown-related patches which
we might want to pick up.

## Fedora kernel tree

Currently the fedora kernel tree can be found at
`https://gitlab.com/cki-project/kernel-ark.git`. These instructions assume you
have added a remote for this tree named `fedora`:

```
git remote add fedora https://gitlab.com/cki-project/kernel-ark.git
```

There are a few branches of interest. `os-build` is the development branch where
the most up-to-date kernel source and configuration will be found. `ark-patches`
is the queue of Fredora-specific kernel patches. `master` tracks Linus's master,
and is useful as the basis for other branches in the tree.

More information about Fedora's kernel branches can be found at
https://gitlab.com/cki-project/kernel-ark/-/wikis/Repository-Layout.

## Resolving merge conflicts

If any patches from Fedora have merge conflicts, it's useful to resolve the
conflicts yourself and then compare that conflict resolution to the resolution
on `fedora/os-build` for the same update. This serves to double check that both
Ubuntu and Fedora end up with the correct resolution. If discrpencies are found,
compare the resolutions to see if either is in error. If the differences have
not functional impact, prefer the resolution from Fedora to keep things
consistent in case there are additional conflicts in the future.

## Checking for new patches

Early in each upstream kernel's development cycle, we should check to see if
Fedora has added any lockdown-related patches which might also be relevant to
Ubuntu. This can be done by generating a list of downstream patches Fedora is
carrying:

```
git log --reverse --oneline fedora/master..fedora/ark-patches
```

Look for any patches releated to lockdown, EFI, module signing, secure boot, or
anything else that looks potentially relevant. If we are not already carrying
the patch, evaluate it to determine if it is relevant to Ubuntu.
