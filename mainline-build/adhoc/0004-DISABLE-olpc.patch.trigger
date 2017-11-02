#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="drivers/staging/olpc_dcon/olpc_dcon_xo_1.c"
csum="13b325ae1aeee7f8602759057ed0d1f9"
[ ! -f "$file" ] && exit 0
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch" || git am --abort
fi
