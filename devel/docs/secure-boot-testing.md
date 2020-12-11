#                         Testing Secure Boot

Before new upstream kernels can be place in -proposed we must ensure that
lockdown is automatically enabled under secure boot. This document outlines the
general procedure for doing this testing for UEFI-based architectures, along
with some architecture-specific notes.

## Overview

This is the general procedure for secure boot testing using a vm. The following
sections contain details for each step.

 1. Create a vm using UEFI firmware.
 2. Add Microsoft UEFI keys (arm64 only).
 2. Enroll a MOK for signing the kernel.
 3. Install the test kernel signed with the MOK.
 4. Reboot and run lockdown test suite.

## Creating a vm

The script `kteam-tools/devel/mk-uefi-vm` can be used to easily create a vm
which uses UEFI firmware. First you need to install the prerquisites:

```
sudo apt-get install qemu-kvm libvirt-daemon-system virtinst ovmf
```

The script uses cloud images, and will automatically enable ssh access with
~/.ssh/id_rsa.pub (or with a different key supplied on the command line).
so you must set up a seed for cloud-init to allow yourself ssh access.

To create the vm:

```
kteam-tools/devel/mk-uefi-vm -r <release> -a <arch> -s <seed-file> --secure-boot <name>
```

Various options can be customized, run `mk-uefi-vm -h` for more information.

After the vm is created, you will be attached to the vm console on your terminal
(to exit press `Ctrl-]`). Once the vm finishes booting and cloud-init has
finished, you should be able to ssh into the vm as the `ubuntu` user.

## Add Microsoft UEFI keys (arm64 only)

If you are setting up an arm64 vm, you need to manually enroll the Microsoft
UEFI signing keys with the firmware. For amd64 this was done automatically when
the vm was set up.

A copy of the keys can be found in the qa-regression-testing git repository,
here:

https://git.launchpad.net/qa-regression-testing/tree/notes_testing/secure-boot/keys

Download the three `microsoft-*.der` files into your vm, then copy them into the
EFI system partition:

```
sudo mkdir /boot/efi/keys
sudo cp microsoft-*.der /boot/efi/keys
```

Attach to the vm console (e.g. `virsh console`), then reboot the vm into the
firmware setup menu:

```
sudo systemctl reboot --firmware-setup
```

Within the firmware setup menu, navigate to `Device Manager>Secure Boot
Configuration`. Change `Secure Boot Mode` to `Custom Mode`, then navigate to
`Custom Secure Boot Options`. In this menu you will find several submenus.
Selecting any of these will present a menu with an `Enroll ...` option, which
when selected will have an option to enroll using a file. For each of the
following `Enroll ...` options, enroll the following files:

 - PK: microsoft-pca-public.der
 - KEK: microsoft-kekca-public.der
 - DB: microsoft-uefica-public.der

Then back out to the `Secure Boot Configuration` menu and press `F10` to save.
Note that gnome-terminal intercepts `F10`; there `Alt-0` can be used instead.

Finally, back out to the top menu and select `Reset`. After reboot, confirm that
secure boot has been enabled. Sanity check that secure boot is enabled (see the
`Testing lockdown` section).

## Enrolling a MOK for kernel signing

The MOK (Machine Owner Key) is a key that gets enrolled with shim to be trusted
for signing kernels. The enrollment needs to happen in the vm. You have two
options for the MOK -- enroll the signing key from the ppa, or create your own
and manually sign kernels with this key.

### Using a ppa key as the MOK

The signing key for a ppa can be found in the signing tarballs produced in the
ppa. For example, the signing tarballs for the c-k-t bootstrap ppa can be found
here:

http://ppa.launchpad.net/canonical-kernel-team/unstable/ubuntu/dists/hirsute/main/signed/

The path can be modified when other ppas are used.

Navigate through the directories to find a signed.tar.gz file for the
architecture you are testing, and download this file to your vm. Extract the
tarball, and the public certificate you need will be found in
`<version>/control/uefi.crt`.

We need a DER format certificate to enrol in shim:

```
openssl x509 -in <version>/control/uefi.crt -inform PEM -outform DER -out MOK.der
```

This certificate can now be enrolled in shim as described in the section
`Enrolling the MOK with shim`.

### Creating your own MOK

To create a MOK, first create a file named openssl.cnf with these contents:

```
# This definition stops the following lines choking if HOME isn't
# defined.
HOME                    = .
RANDFILE                = $ENV::HOME/.rnd

[ req ]
distinguished_name      = req_distinguished_name
x509_extensions         = v3
string_mask             = utf8only
prompt                  = no

[ req_distinguished_name ]
countryName             = UK
stateOrProvinceName     = SomweState
localityName            = SomeCity
0.organizationName      = SomeOrg
commonName              = Secure Boot Signing
emailAddress            = example@example.com

[ v3 ]
subjectKeyIdentifier    = hash
authorityKeyIdentifier  = keyid:always,issuer
basicConstraints        = critical,CA:FALSE
extendedKeyUsage        = codeSigning,1.3.6.1.4.1.311.10.3.6
nsComment               = "OpenSSL Generated Certificate"
```

Then create the key. We create the public key in DER format for enrollment with
shim and a copy in PEM format for use with sbsign.

```
openssl req -config ./openssl.cnf -new -x509 -newkey rsa:2048 \
    -nodes -days 36500 -outform DER -keyout "MOK.priv" -out "MOK.der"
openssl x509 -in MOK.der -inform DER -outform PEM -out MOK.pem
```

### Enrolling the MOK with shim

To enroll the MOK with shim, do the following in your vm:

```
sudo mokutil --import MOK.der
```

This will prompt for a password, which you will have to enter again when shim
actually enrolls the key. Once this is done, be sure you are attached to the
vm's console (e.g. `virsh console`), then reboot the vm. Upon reboot, shim will
guide you through the process of enrolling the key.

## Installing and signing the kernel

Once the MOK is enrolled with shim, you can now sign kernels to test with secure
boot. Start by installing the packages for the kernel you want to test. If you
enrolled the ppa signing key with shim, you are good to go and can proceed to
`Testing lockdown`. Otherwise, follow the instructions below to sign your
kernel.

Download the unsigned package for the kernel you've installed, and extract the
vmlinuz image from the package. Note that if you are working with arm64, the
kernel image is gzip compressed and must be compressed before signing. It must
then be recompressed before it is placed in /boot.

Sign the unsigned kernel image:

```
sbsign --key MOK.priv --cert MOK.pem <unsigned-vmlinuz> \
    --output <signed-vmlinuz>
```

Copy the signed kernel image over the existing file in /boot (remember to
compress it first on arm64), then run:

```
sudo update-grub
```

Reboot, and the self-signed kernel should successfully boot.

## Testing lockdown

First, verify that the kernel was booted under secure boot. Check for messages
similar to the following in dmesg:

```
[    0.000000] secureboot: Secure boot enabled
[    0.000000] Kernel is locked down from EFI Secure Boot mode; see man kernel_lockdown.7
```

Then confirm that `/sys/kernel/security/lockdown` shows that `integrity` is
selected.

```
$ cat /sys/kernel/security/lockdown
none [integrity] confidentiality
```
