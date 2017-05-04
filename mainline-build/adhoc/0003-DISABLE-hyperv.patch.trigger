#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="drivers/staging/hv/hv_mouse.c"
csum="afd5524c29871a8293518f0be50a7474"
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch"
fi
