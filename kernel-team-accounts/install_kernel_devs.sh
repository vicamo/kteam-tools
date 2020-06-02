#!/bin/bash
#
# Add kernel developer accounts according to the information in
# kernel_devs.conf.
#
# Usage: [--admins-only] PASSWD
#  --admins-only	Only create admin capable accounts.
#

admins_only=
if [ "$1" = "--admins-only" ]; then
	admins_only=y
	shift
fi

if [ "$1" = "" ]
then
	echo Usage: $0 [-s] PASSWD
	exit 1
fi
PASSWD="$1"

. kernel_devs.conf

HOME=/home

#
# Make sure there is an sbuild group for schroot.
#
if ! grep sbuild /etc/group >/dev/null
then
	addgroup --system sbuild
fi

let index=-1
for i in ${kdev[@]}
do
	let index=${index}+1
	#echo "${kdev_obsolete[${index}]:+# }kdev_new ${kdev[${index}]} '${kdev_name[${index}]}' ${kdev_key[${index}]} # ${kdev_passwd[${index}]}"
	#let index=${index}+1

	if [ -z "${kdev_passwd[${index}]}" ]; then
		if [ -n "$admins_only" ]; then
			continue
		fi
	fi

	if [ -n "${kdev_obsolete[${index}]}" ]
	then
		echo "${kdev_name[${index}]} is obsolete"
		continue
	fi

	if ! grep $i /etc/passwd || [ ! -d ${HOME}/${i} ]
	then
		echo $i
		(echo ${kdev_name[${index}]};echo;echo;echo;echo;echo y;) | \
		adduser --quiet --disabled-password $i
		if [ -d ${HOME}/${i} ]
		then
			mkdir -p ${HOME}/$i/.ssh
			wget -O ${HOME}/$i/.ssh/authorized_keys2 ${kdev_key[${index}]}
			chown $i.$i ${HOME}/$i/.ssh ${HOME}/$i/.ssh/authorized_keys2
		else
			mkdir -p ${HOME}/${i}
			chown ${i}.warthogs ${HOME}/${i}
		fi
		# Allow sudo -- give this user a real password.
		if [ ! -z "${kdev_passwd[${index}]}" ]; then
			(echo ${PASSWD};echo ${PASSWD}) | passwd -q $i
		fi
	fi
	# Allow sudo -- add this user to the sudo group.
	if [ ! -z "${kdev_passwd[${index}]}" ]; then
		adduser $i sudo
	fi
	adduser $i sbuild
done

