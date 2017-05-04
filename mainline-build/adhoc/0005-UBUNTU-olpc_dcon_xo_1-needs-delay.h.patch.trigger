#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="drivers/staging/olpc_dcon/olpc_dcon_xo_1.c"
csum="6a0ae9f73f4878052202473bb952d6e4"
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch"
fi
