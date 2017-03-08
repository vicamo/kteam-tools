#!/bin/bash
#
# Add kernel developer accounts according to the information in
# kernel_devs.conf.
#
# useage: [-s] PASSWD
# -s adds the user to the admin group (for sudo)
#

if [ "$1" = "-s" ]
then
	SUDO=yes
	shift
fi

if [ "$1" = "" ]
then
	echo useage: $0 [-s] PASSWD
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
	addgroup sbuild
fi

let index=0
for i in ${kdev[@]}
do
	#echo "${kdev_obsolete[${index}]:+# }kdev_new ${kdev[${index}]} '${kdev_name[${index}]}' ${kdev_key[${index}]}"
	#let index=${index}+1
	#continue

	if [ ! -z "${kdev_obsolete[${index}]}" ]
	then
		echo "${kdev_name[${index}]} is obsolete"
		let index=${index}+1
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
		#
		# Allow sudo
		#
		if [ ! -z "${kdev_passwd[${index}]}" ]; then
			(echo ${PASSWD};echo ${PASSWD}) | passwd -q $i
		fi
	fi
	if [ ! -z "$SUDO" ]
	then
		adduser $i admin
	fi
	adduser $i sbuild
	let index=${index}+1
done

