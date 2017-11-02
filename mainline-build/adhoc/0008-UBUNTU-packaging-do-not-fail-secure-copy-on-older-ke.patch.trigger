#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="debian/rules.d/2-binary-arch.mk"
csum="647c141b53e037781844f0c04234526e"
[ ! -f "$file" ] && exit 0
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch" || git am --abort
fi
