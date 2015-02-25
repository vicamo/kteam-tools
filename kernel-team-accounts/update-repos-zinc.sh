#!/bin/bash

CWD=/srv/kernel.ubuntu.com/git/virgin
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

while read url repo
do
	if [ ! -d ${repo} ]
	then
		mkdir -p `dirname ${repo}`
		git clone --bare ${url} ${repo}
	fi
	(cd ${repo}; git fetch origin)
done <<EOL
git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git	linux.git
git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git	linux-stable.git
git://git.kernel.org/pub/scm/linux/kernel/git/airlied/drm-2.6		testing/drm-2.6
git://anongit.freedesktop.org/drm-intel					testing/drm-intel.git
git://git.infradead.org/debloat-testing.git				testing/debloat-testing
EOL

rm -f $LOCK
