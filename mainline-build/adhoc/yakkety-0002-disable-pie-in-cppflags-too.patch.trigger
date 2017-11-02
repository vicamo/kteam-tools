#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

# If there is no CONFIG_CC_STACKPROTECTOR_STRONG we do not need to do anything.
if ! grep -q -s 'ifdef CONFIG_CC_STACKPROTECTOR_STRONG' Makefile; then
	exit 0
fi

# There is some of the no-pie patch applied but no CPPFLAGS set...
if grep -q -s 'force no-pie for distro compilers that enable pie by default' Makefile; then
	if ! grep -q -s 'KBUILD_CPPFLAGS += $(call cc-option, -fno-pie)' Makefile; then
		echo "*** applying $patch ..."
		git am -C0 "$patch" || git am --abort
	fi
fi
