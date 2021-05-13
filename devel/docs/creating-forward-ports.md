# Creating forward port kernels for development

Prerequisites:
* Ensure that kernel-series contains appropriate entries for development series
  kernels as backports from the most recent stable series.
* Create a chroot for the target release of the forward port.

## Set up trees

Check out the tree for the kernel you are updating. It's very likely this tree
will not be up to date with the release you are porting the kernel from, so it
will be necessary to manually update your local branches. For example:

```
cranky checkout impish:linux
cd impish
git remote add hirsute git://...
git fetch hirsute
git reset --hard <latest-tag>
```

And likewise for meta, signed, and l-r-m.

## Add backport packaging

In the kernel tree, make a copy of the reference packaging directory for the new
backport kernel. E.g.:

```
cp -r debian.master debian.master-21.10
git add debian.master-21.10
```

Update `debian/debian.env` to point to the new packaging branch. Commit these
changes, using `Ignore: yes` in the commit message to omit the change from the
changelog.

## Add dummy changelog entries

For the kernel and all dependent packages, add a dummy entry to the changelog to
update the distribution (cranky commands will fail if the distribution does not
match for all packages). E.g.:

```
diff --git a/debian.master-21.10/changelog b/debian.master-21.10/changelog
index fa2b29b2367b..3b2957a51ed9 100644
--- a/debian.master-21.10/changelog
+++ b/debian.master-21.10/changelog
@@ -1,3 +1,9 @@
+linux (5.11.0-18.19) impish; urgency=medium
+
+  * Empty entry.
+
+ -- Seth Forshee <seth.forshee@canonical.com>  Thu, 13 May 2021 13:40:45 -0500
+
 linux (5.11.0-18.19) hirsute; urgency=medium

   * hirsute/linux: 5.11.0-18.19 -proposed tracker (LP: #1927578)
```

Commit the updates, using `Ignore: yes`.

## Add `copy-files` helper

The best thing to do here is to copy the
`debian.<branch>/scripts/helpers/copy-files` from the previous forward port of
the same kernel. Commit this using `Ignore: yes`.

## Run cranky-fix to generate `update.conf`

Inspect the result to ensure everything looks correct.

## Open the changelog

Open the changelog using `cranky open -r` to reuse the previous abi
directories.  Ammend the opening commit to add ignore files to disable abi,
module, and retpoline checks in the first upload:

```
for path in debian.<branch>/abi/<version>/*; do \
    [ ! -d $path ] && continue; \
    echo "1" >$path/ignore; \
    echo "1" >$path/ignore.modules; \
    echo "1" >$path/ignore.retpoline; \
done
git add debian.<branch>/abi
git commit --amend
```

Check the opening commit to ensure everything looks correct. Pay special
attention to the version number in the change log, which should now end with
`+<series>.1`, e.g. `+21.10.1`.

## Update dkms versions

For forward ports to the development release you should run
`./update-version-dkms proposed` for the _main kernel only_. For "derivatives"
(though they aren't technically derivatives of the main kernel)
`debian/dkms-versions` should be copied from the main kernel. Otherwise we can
end up in a state where only some or none of the kernels can migrate to -release
due to the tight version lock of l-r-m with nvidia userspace packages.

## Test build, close, and upload

From this point the package can be test built, linked to a tracking bug, and
closed as usual. The one small exception is that the `-s` option should be used
when closing to skip changes from the base kernel, as it will not be able to
work out the correct versions to include in the change log and will end up
including far too much.

For dependent packages, all that needs to be done is to run `cranky link-tb`.

Uploads must be done to a PPA which is configured to build against -proposed.
Typically the `unstable` and `bootstrap` PPAs are used for this purpose. The
routing in kernel-series should also direct uploads to these PPAs.
