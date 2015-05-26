#!/bin/bash

CWD=/usr3/ubuntu
LOCK=/tmp/update-repos.lock

if [ ! "$1" = "" ]
then
	CWD="$1"
fi

cd $CWD || exit 1

if [ -f $LOCK ]
then
	exit 1
fi
echo 1 > $LOCK


# Get our current orig files.
while read url
do
	file=`basename "$url"`

	if [ ! -f "$file" ]; then
		wget "$url"
	fi
done <<EOL
http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_3.2.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_3.13.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_3.16.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_3.19.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux-lts-trusty/linux-lts-trusty_3.13.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux-lts-utopic/linux-lts-utopic_3.16.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux-lts-vivid/linux-lts-vivid_3.19.0.orig.tar.gz
EOL

# Clone and update all our current repos.
while read repo url ref flags
do
	if [ ! -d "$repo" ]; then
		if [ "$ref" != "-" ]; then
			git clone $flags --reference "$ref" "$url" "$repo"
		else
			git clone $flags "$url" "$repo"
		fi
	else
		(cd "$repo" && 
			git fetch "$url" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*')
	fi
done <<EOL
linux.git			git://kernel.ubuntu.com/virgin/linux.git
ubuntu-precise.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/precise	linux.git	--bare
ubuntu-precise-meta.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-meta/+git/precise	-		--bare
ubuntu-precise-signed.git	git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-signed/+git/precise	-		--bare
ubuntu-trusty.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/trusty		linux.git	--bare
ubuntu-trusty-meta.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-meta/+git/trusty	-		--bare
ubuntu-trusty-signed.git	git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-signed/+git/trusty	-		--bare
ubuntu-utopic.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/utopic		linux.git	--bare
ubuntu-utopic-meta.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-meta/+git/utopic	-		--bare
ubuntu-utopic-signed.git	git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-signed/+git/utopic	-		--bare
ubuntu-vivid.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/vivid		linux.git	--bare
ubuntu-vivid-meta.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-meta/+git/vivid	-		--bare
ubuntu-vivid-signed.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-signed/+git/vivid	-		--bare
ubuntu-wily.git			git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/wily		linux.git	--bare
ubuntu-wily-meta.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-meta/+git/wily	-		--bare
ubuntu-wily-signed.git		git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-signed/+git/wily	-		--bare
ubuntu-precise-lbm.git		git://kernel.ubuntu.com/ubuntu/ubuntu-precise-lbm.git				-		--bare
linux-firmware.git		git://kernel.ubuntu.com/ubuntu/linux-firmware.git				-		--bare
wireless-crda.git		git://kernel.ubuntu.com/ubuntu/wireless-crda.git				-		--bare
kernel-testing.git		git://kernel.ubuntu.com/ubuntu/kernel-testing.git				-		--bare
autotest.git			git://kernel.ubuntu.com/ubuntu/autotest.git					-		--bare
autotest-client-tests.git	git://kernel.ubuntu.com/ubuntu/autotest-client-tests.git			-		--bare
instrument-lib.git		git://kernel.ubuntu.com/ubuntu/instrument-lib.git				-		--bare
kteam-tools.git			git://kernel.ubuntu.com/ubuntu/kteam-tools.git					-		--bare
kteam-tools			git://kernel.ubuntu.com/ubuntu/kteam-tools.git					-
EOL

rm -f $LOCK
