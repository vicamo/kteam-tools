#!/bin/bash

LINUX=git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
LLREPO=linux-2.6.git
LREPO=linux.git
UBUNTU=git://kernel.ubuntu.com/ubuntu
RELEASES="hardy lucid oneiric precise quantal raring saucy"
EXTRAS="ubuntu-hardy-lbm ubuntu-hardy-lrm ubuntu-hardy-lum ubuntu-lucid-lbm ubuntu-oneiric-lbm ubuntu-precise-lbm ubuntu-quantal-lbm"
EXTRAS="$EXTRAS linux-firmware wireless-crda kernel-testing autotest autotest-client-tests instrument-lib"
METAS="hardy lucid oneiric precise quantal raring saucy"
SIGNED="precise quantal raring saucy"
LOCK=/tmp/update-repos.lock
ORIGS="2.6.24 2.6.32 2.6.38 3.0.0 3.2.0 3.5.0 3.8.0"

for i in ${ORIGS}
do
	if [ ! -f linux_${i}.orig.tar.gz ]
	then
		wget http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_${i}.orig.tar.gz
	fi
done

if [ -f $LOCK ]
then
	exit 1
fi
echo 1 > $LOCK

if [ ! -d ${LREPO} ]
then
	git clone ${LINUX} ${LREPO}
	(cd ${LREPO}; git fetch origin)
	rm -rf ${LLREPO}
	ln -s ${LREPO} ${LLREPO}
else
	(cd ${LREPO}; git fetch origin;git fetch origin master;git reset --hard FETCH_HEAD)
fi

for i in ${RELEASES}
do
	if [ ! -d ubuntu-${i}.git ]
	then
		git clone --reference ${LREPO} ${UBUNTU}/ubuntu-${i}.git ubuntu-${i}.git
	else
		(cd ubuntu-${i}.git;git fetch origin;git fetch origin master;git reset --hard FETCH_HEAD)
	fi
done

for i in ${METAS}
do
	if [ ! -d ubuntu-${i}-meta.git ]
	then
		git clone ${UBUNTU}/ubuntu-${i}-meta.git ubuntu-${i}-meta.git
	else
		(cd ubuntu-${i}-meta.git;git fetch origin;git fetch origin master;git reset --hard FETCH_HEAD)
	fi
done

for i in ${SIGNED}
do
	if [ ! -d ubuntu-${i}-signed.git ]
	then
		git clone ${UBUNTU}/ubuntu-${i}-signed.git ubuntu-${i}-signed.git
	else
		(cd ubuntu-${i}-signed.git;git fetch origin;git fetch origin master;git reset --hard FETCH_HEAD)
	fi
done

for i in ${EXTRAS}
do
	if [ ! -d ${i}.git ]
	then
		git clone ${UBUNTU}/${i}.git ${i}.git
	else
		(cd ${i}.git;git fetch origin;git fetch origin master;git reset --hard FETCH_HEAD)
	fi
done

#
# Create and update a copy of the kteam-tools repo
#
if [ ! -d kteam-tools ]
then
	git clone ${UBUNTU}/kteam-tools.git kteam-tools
else
	(cd kteam-tools; git fetch origin;git fetch origin master;git reset --hard FETCH_HEAD)
fi

rm -f $LOCK
