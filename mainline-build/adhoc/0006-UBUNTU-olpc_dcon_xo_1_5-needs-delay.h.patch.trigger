#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

file="drivers/staging/olpc_dcon/olpc_dcon_xo_1_5.c"
csum="55c01b13d520fa0cdde88d8d3034f21c"
file_csum=$( md5sum "$file" | awk '{print $1}' )
if [ "$file_csum" = "$csum" ]; then
	echo "*** applying $patch ..."
	git am "$patch"
fi
