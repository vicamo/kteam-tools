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
	if [ "$FIX_VERBOSE" -ge 1 ]; then
		echo "  $*"
	fi
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

resync_master()
{
	local msg="$1"
	shift 1
	local file
	local files=()
	local base

	local master="$FIX_MASTER"

	for file in "$@"
	do
		base="$(basename $file)"
		if [ -f "$master/$base" ] && [ -f "$file" ]; then
			cp -p "$master/$base" "$file"
			files+=("$file")
		fi
	done

	commit "$msg" "${files[@]}"
}

resync_main()
{
	local msg="$1"
	shift 1
	local file
	local files=()

	local main_path="$FIX_MAIN_PATH"

	[ "$main_path" = '' ] && return

	for file in "$@"
	do
		if [ -f "$main_path/$file" ] && [ -f "$file" ]; then
			cp -p "$main_path/$file" "$file"
			files+=("$file")
		fi
	done

	commit "$msg" "${files[@]}"
}
