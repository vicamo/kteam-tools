#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="arch/arm/mach-highbank/clock.c"
csum="119a926bf04eae5024a3002b626ef8bc"
[ ! -f "$file" ] && exit 0
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch" || git am --abort
fi
