#!/bin/bash

function fetch_repo()
{
	local repo url type bare ref

	while read -r repo url type
	do
		echo "Syncing $repo from $url"

		case "$repo" in
			*.git) bare="--bare" ;;
			*)     bare= ;;
		esac

		case "$type" in
			"main") ref="linux-linus.git" ;;
			*)      ref= ;;
		esac
		case "$url" in
			*/+source/linux/*) ref="linux-linus.git" ;;
		esac

		if [ ! -d "$repo" ]; then
			if [ -n "$ref" ]; then
				# Note: we intentionally clone the local ref directly.
				# shellcheck disable=SC2086
				git clone $bare --reference "$ref" "$ref" "$repo"
			else
				# shellcheck disable=SC2086
				git clone $bare "$url" "$repo"
			fi
		fi
		(
			cd "$repo" &&
			git fetch -u "$url" '+refs/heads/*:refs/heads/*' '+refs/tags/*:refs/tags/*' &&
			[ -d .git ] && git checkout -qf
		)
	done
}

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

# Remove the lock on exit
# shellcheck disable=SC2064
trap "rm -f $LOCK" EXIT

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
echo "Syncing mandatory repos"
fetch_repo <<EOL
linux-linus.git  git://git.launchpad.net/~ubuntu-kernel-test/+git/linus--linux
kteam-tools      git://git.launchpad.net/~canonical-kernel/+git/kteam-tools
EOL

# If we will not have local developers we do not need general repository mirrors.
[ -f "$HOME/.cod/disable-ubuntu-repositories" ] && { rm -f $LOCK; exit 0; }

# Get the repos used on the mainline builders
echo "Syncing builder repos"
fetch_repo <<EOL
autotest-client-tests.git       git://git.launchpad.net/~canonical-kernel-team/+git/autotest-client-tests
autotest-client-virt-tests.git  git://git.launchpad.net/~canonical-kernel-team/+git/autotest-client-virt-tests
autotest-docker.git             git://git.launchpad.net/~canonical-kernel-team/+git/autotest-docker
autotest.git                    git://git.launchpad.net/~canonical-kernel-team/+git/autotest
kernel-testing.git              git://git.launchpad.net/~canonical-kernel-team/+git/kernel-testing
kteam-tools.git                 git://git.launchpad.net/~canonical-kernel/+git/kteam-tools
adt-matrix-hints.git            git://git.launchpad.net/~canonical-kernel/+git/adt-matrix-hints
linux-firmware.git              git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux-firmware
unstable.git                    git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/unstable
EOL

echo "Syncing kernel-series repos"
"$here/kta-config" repositories | \
while read -r _series _source repo url type
do
	echo "$repo $url $type"
done | fetch_repo

rm -f $LOCK
