#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

if ! test -f tools/hv/lsvmbus.8; then
	echo "*** applying $patch ..."
	git am -C0 "$patch" || git am --abort
fi
