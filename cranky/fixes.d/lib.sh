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
	local file
	msg="$msg

$FIX_BUGLINK
"
	if [ "$#" -eq 0 ]; then
		fix_verbose "no files present"
		return
	fi
	for file in "$@"
	do
		if [ -e "$file" ]; then
			git add "$file"
		else
			git rm --ignore-unmatch "$file"
		fi
	done
	if ! git diff --exit-code HEAD -- "$@" >/dev/null; then
		git commit -m "$msg" -s --untracked-files=no -- "$@"
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
	local files=()

	fix_uses_master

	for file in "$@"
	do
		if [ -f "$master/$file" ] && [ -f "$file" ]; then
			cp -p "$master/$file" "$file"
			files+=("$file")
		fi
	done

	commit "$msg" "${files[@]}"
}
