#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

if ! egrep -q -s '^syncconfig:' scripts/kconfig/Makefile; then
	echo "*** from __future__ import syncconfig ... narf ..."
	{
		echo ""
		echo "syncconfig: silentoldconfig"
	} >>scripts/kconfig/Makefile
	git commit -s -m 'adhoc: from __future__ import syncconfig' scripts/kconfig/Makefile
fi
