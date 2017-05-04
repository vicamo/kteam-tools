#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="drivers/staging/ti-st/st_kim.c"
csum="b41944e0c30683bdedb6a66e11098892"
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch"
fi
