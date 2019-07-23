#!/bin/bash

patch="${0%.trigger}"
series="$1"
build="$2"

if ! egrep -q -s 'ensure -fcf-protection is disabled when using retpoline as it is' Makefile; then
        echo "*** applying $patch ..."
        git am -C0 "$patch" || git am --abort
fi
