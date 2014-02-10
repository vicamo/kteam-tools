#!/bin/bash

CWD=/srv/kernel.ubuntu.com/git/virgin
LINUX=git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
LREPO=linux.git

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

if [ ! -d ${LREPO} ]
then
	git clone --bare ${LINUX} ${LREPO}
fi
(cd ${LREPO}; git fetch origin)

rm -f $LOCK
