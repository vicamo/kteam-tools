#!/bin/bash

CWD=/usr3/ubuntu
LOCK=/tmp/update-repos.lock

here=`dirname $0`
case "$here" in
/*) ;;
*)  here="`pwd`/$here" ;;
esac

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
		echo Getting "$url"
		wget -q "$url"
	fi
done <<EOL
http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_3.2.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_3.13.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_3.19.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux_4.2.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux-lts-trusty/linux-lts-trusty_3.13.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux-lts-utopic/linux-lts-utopic_3.16.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux-lts-vivid/linux-lts-vivid_3.19.0.orig.tar.gz
http://archive.ubuntu.com/ubuntu/pool/main/l/linux-lts-wily/linux-lts-wily_4.2.0.orig.tar.gz
EOL

# Get a couple of special repos first
while read repo url ref
do
	case "$repo" in
	*.git)		bare='--bare' ;;
	*)		bare='' ;;
	esac

	if [ ! -d "$repo" ]; then
		if [ "$ref" != "-" ]; then
			git clone $bare --reference "$ref" "$url" "$repo"
		else
			git clone $bare "$url" "$repo"
		fi
	else
		(cd "$repo" && 
			git fetch -u "$url" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' &&
			[ -d .git ] && git checkout -qf)
	fi
done <<EOL
linux.git			git://kernel.ubuntu.com/virgin/linux.git					-
kteam-tools			git://kernel.ubuntu.com/ubuntu/kteam-tools.git					-
EOL

cat "$here/../info/repositories.txt" | while read k_u_c lp master status
do
	if [ "$status" = "inactive" ]
	then
		continue
	fi

	case $master in
		either|launchpad)
			URL=$lp
			;;
		wani)
			URL=$k_u_c
			;;
		*)
			echo "Unknown master location: $master"
			exit 1
			;;
	esac

	if [ ! -d `basename $URL` ]
	then
		git clone --bare --reference linux.git $URL `basename $URL`
	fi

	(cd `basename $URL`; git fetch --tags origin)
done

rm -f $LOCK
