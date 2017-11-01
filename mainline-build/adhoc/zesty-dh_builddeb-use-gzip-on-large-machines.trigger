#!/bin/bash

series="$1"
build="$2"

case "$series" in
zesty)	;;
*)		exit 0 ;;
esac

echo "*** switching package compression on big machine ..."
sed -i 's/\(dh_builddeb [^;]*\)\($\|;\)/\1 -- -Zgzip -Snone\2/' debian/rules.d/*.mk
git commit -a -s -m 'dh_builddeb switch to -Zgzip to avoid dpkg bug on large builders'
