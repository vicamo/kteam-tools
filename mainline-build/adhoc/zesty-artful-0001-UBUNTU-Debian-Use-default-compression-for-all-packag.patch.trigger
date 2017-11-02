#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

case "$series" in
zesty|artful|unstable)	;;
*)		exit 0 ;;
esac

echo "*** applying $patch ..."
git am -C0 "$patch" || git am --abort
