#!/bin/bash

fix_error()
{
	echo "ERROR: $*" 1>&2
}

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

resync_master()
{
	local msg="$1"
	shift 1
	local master="$FIX_MASTER"
	local file

	for file in "$@"
	do
		[ -f "$master/$file" -a -f "$file" ] && cp -p "$master/$file" "$file"
	done

	commit "$msg" "$@"
}
