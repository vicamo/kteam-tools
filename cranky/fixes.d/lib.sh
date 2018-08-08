#!/bin/bash

fix_verbose()
{
	[ "$FIX_VERBOSE" -ge 1 ] && echo "  $*"
}

commit()
{
	local msg="$1"
	shift 1
	msg="$msg

$FIX_BUGLINK
"
	if ! git diff --exit-code -- "$@" >/dev/null; then
		git commit -m "$msg" -s -- "$@"
	else
		fix_verbose "no changes to commit"
	fi
}
