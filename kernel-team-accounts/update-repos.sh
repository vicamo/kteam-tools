#!/bin/bash

CWD=/usr3/ubuntu
LLREPO=linux-2.6.git
LREPO=linux.git
UBUNTU=git://kernel.ubuntu.com/ubuntu
VIRGIN=git://kernel.ubuntu.com/virgin
LINUX=${VIRGIN}/${LREPO}
RELEASES="lucid precise trusty utopic vivid"
EXTRAS="ubuntu-lucid-lbm ubuntu-precise-lbm ubuntu-quantal-lbm"
EXTRAS="$EXTRAS linux-firmware wireless-crda kernel-testing autotest autotest-client-tests instrument-lib"
METAS="lucid precise quantal saucy"
SIGNED="precise quantal saucy"
LOCK=/tmp/update-repos.lock
ORIGS="2.6.32 3.0.0 3.2.0 3.5.0 3.8.0 3.11.0 3.13.0"
LTS_ORIGS=""
LTS_ORIGS="$LTS_ORIGS linux-lts-trusty/linux-lts-trusty_3.13.0.orig.tar.gz "
LTS_ORIGS="$LTS_ORIGS linux-lts-utopic/linux-lts-utopic_3.16.0.orig.tar.gz "

if [ ! "$1" = "" ]
then
	CWD="$1"
fi

cd $CWD || exit 1

for i in ${ORIGS}
do
	if [ ! -f linux_${i}.orig.tar.gz ]
	then
		wget http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_${i}.orig.tar.gz
	fi
done
for i in ${LTS_ORIGS}
do
	if [ ! -f `basename $i` ]
	then
		wget http://archive.ubuntu.com/ubuntu/pool/main/l/$i
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
