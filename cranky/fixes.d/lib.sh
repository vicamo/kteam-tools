#!/bin/bash

here()
{
	dirname "$(realpath -e "${0}")"
}

fix_error()
{
	echo "ERROR: $*" 1>&2
}

fix_warning()
{
	echo "WARNING: $*" 1>&2
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

fix_uses_master()
{
	if [ -z "$FIX_MASTER" ]; then
		fix_warning "no master directory specified, skipping"
		exit 0
	fi
}

resync_master()
{
	local msg="$1"
	shift 1
	local master="$FIX_MASTER"
	local file

	fix_uses_master

	for file in "$@"
	do
		[ -f "$master/$file" ] && [ -f "$file" ] && cp -p "$master/$file" "$file"
	done

	commit "$msg" "$@"
}
