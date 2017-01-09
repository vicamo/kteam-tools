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
	(cd ${repo} && git fetch origin '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*')
done <<EOL
git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git	linux.git
git://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable.git	linux-stable.git
linux.git 								testing/crack.git
git://people.freedesktop.org/~airlied/linux				testing/airlied--linux.git
git://anongit.freedesktop.org/drm-intel					testing/drm-intel.git
git://git.infradead.org/debloat-testing.git				testing/debloat-testing.git
git://anongit.freedesktop.org/drm-tip					testing/freedesktop--drm-tip
EOL

while read repo url refs
do
	url=$( echo "$url" | sed -e 's_git://git.launchpad.net/_git+ssh://kernel-ppa@git.launchpad.net/_' )
	if [ ! -d ${repo} ]
	then
		echo "${repo} not found" 1>&2
		continue
	fi

	(cd ${repo} && git push ${url} ${refs})
done <<EOL
linux.git	git://git.launchpad.net/~canonical-kernel/linux/+git/linux-stable-ckt	master:master refs/tags/*:refs/tags/*
EOL

rm -f $LOCK
