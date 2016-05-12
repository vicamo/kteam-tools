#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

case "$build" in
yakkety)	;;
*)		exit 0 ;;
esac

if ! grep -q -s 'force no-pie for distro compilers that enable pie by default' Makefile; then
	git am -C0 "$patch"
fi
