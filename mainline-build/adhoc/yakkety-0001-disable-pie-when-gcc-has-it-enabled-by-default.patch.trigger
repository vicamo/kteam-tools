#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

case "$build" in
yakkety|unstable)	;;
*)		exit 0 ;;
esac

if ! grep -q -s 'force no-pie for distro compilers that enable pie by default' Makefile; then
	echo "*** applying $patch ..."
	git am -C0 "$patch"
fi
