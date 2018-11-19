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

base_url="http://archive.ubuntu.com/ubuntu/pool"

# Get our current orig files.
"$here/kta-config" origs | \
while read supported version url
do
	file=`basename "$url"`

	if [ "$supported" = 'True' ]; then
		if [ ! -f "$file" ]; then
			echo Getting "$url"
			
			wget -q "$base_url/main/$url" || \
			wget -q "$base_url/universe/$url"
		fi

		if [ "linux_${version}.orig.tar.gz" != "$file" ]; then
			if [ -f "linux_${version}.orig.tar.gz" -a -f "$file" ]; then
				if cmp "linux_${version}.orig.tar.gz" "$file"; then
					echo "Linking linux_${version}.orig.tar.gz $file"
					ln -f "linux_${version}.orig.tar.gz" "$file"
				fi
			fi
		fi

	else
		rm -f "$file"
	fi
done

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
linux-linus.git			git://kernel.ubuntu.com/virgin/linux.git					-
kteam-tools			git://kernel.ubuntu.com/ubuntu/kteam-tools.git					-
EOL

while read k_u_c lp master flags
do
	case ",$flags," in
	*,inactive,*)		continue ;;
	esac

	[ "$k_u_c" = '-' ] && continue

	# repository: the "normal form" is the name we use on wani.
	repo=`basename "$k_u_c"`

	# pick the master url.
	case $master in
	either|launchpad)	url=$lp ;;
	wani)			url=$k_u_c ;;
	*)
		echo "Unknown master location: $master"
		exit 1
		;;
	esac

	# If this is +source/linux then we should reference linux.git.
	case "$url" in
	*/+source/linux/*)	ref="linux-linus.git" ;;
	*)			ref="-" ;;
	esac

	# If this ends .git we want it bare -- (currently always)
	case "$repo" in
	*.git)		bare='--bare' ;;
	*)		bare='' ;;
	esac

	echo "Syncing info/repositories.txt $repo ($url) ..."
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
done <"$here/../info/repositories.txt" 

# disco linux-signed-oem ubuntu-oem-disco-signed.git git://git.launchpad.net/~canonical-kernel/ubuntu/+source/linux-signed-oem/+git/disco
"$here/kta-config" repositories | \
while read series source repo url type
do
	echo "Syncing kernel-series $repo ($url) ..."

	# If this is +source/linux then we should reference linux.git.
	case "$type" in
	main)			ref="linux-linus.git" ;;
	*)			ref="-" ;;
	esac

	# If this ends .git we want it bare -- (currently always)
	case "$repo" in
	*.git)		bare='--bare' ;;
	*)		bare='' ;;
	esac

	if [ ! -d "$repo" ]; then
		if [ "$ref" != "-" ]; then
			#git clone $bare --reference "$ref" "$url" "$repo"
			git clone $bare --reference "$ref" "$ref" "$repo"
			(cd "$repo" && 
				git fetch -u "$url" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' &&
				[ -d .git ] && git checkout -qf)
		else
			git clone $bare "$url" "$repo"
		fi
	else
		(cd "$repo" && 
			git fetch -u "$url" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' &&
			[ -d .git ] && git checkout -qf)
	fi
done

rm -f $LOCK
