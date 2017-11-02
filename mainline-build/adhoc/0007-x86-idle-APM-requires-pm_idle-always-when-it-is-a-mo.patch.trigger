#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="arch/x86/kernel/process.c"
csum="1ded15dd3a3cb622df182d60160ff826"
[ ! -f "$file" ] && exit 0
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch" || git am --abort
fi
