#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

# If we have support for CONFIG_CC_STACKPROTECTOR_STRONG we need to go all -fpie on it.
if ! grep -q -s 'ifdef CONFIG_CC_STACKPROTECTOR_STRONG' Makefile; then
	exit 0
fi

if ! grep -q -s 'force no-pie for distro compilers that enable pie by default' Makefile; then
	echo "*** applying $patch ..."
	git am -C0 "$patch"
fi
