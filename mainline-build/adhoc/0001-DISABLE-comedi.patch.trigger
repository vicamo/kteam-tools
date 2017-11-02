#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="drivers/staging/comedi/drivers/das08_cs.c"
csum="47a4f33c4733880faa50f0e64a6e5c8f"
[ ! -f "$file" ] && exit 0
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch" || git am --abort
fi
