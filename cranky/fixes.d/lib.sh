#!/bin/bash

here()
{
	dirname "$(readlink -f "${0}")"
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

$FIX_BUGLINK/$FIX_BUG
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
		base="$(basename "$file")"
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

resync_batch_start()
{
	__fix_batch=()
}

__resync_batch_sync_if_here()
{
	local base="$1"
	local from="$2"
	local to="$3"

	[ -z "$to" ] && to="$from"
	from="$base/$from"

	if [ -f "$from" ] && [ -f "$to" ]; then
		cp -p "$from" "$to"
		__fix_batch+=("$to")
	fi
}
resync_batch_master_sync_if_here()
{
	__resync_batch_sync_if_here "$FIX_MASTER" "$@"
}
resync_batch_main_sync_if_here()
{
	__resync_batch_sync_if_here "$FIX_MAIN_PATH" "$@"
}

__resync_batch_master_sync()
{
	local base="$1"
	local from="$2"
	local to="$3"

	[ -z "$to" ] && to="$from"
	from="$base/$from"

	if [ -f "$from" ]; then
		cp -p "$from" "$to"
		__fix_batch+=("$to")

	elif [ ! -f "$from" ] && [ -f "$to" ]; then
		rm -f "$to"
		__fix_batch+=("$to")
	fi
}
resync_batch_master_sync()
{
	__resync_batch_master_sync "$FIX_MASTER" "$@"
}
resync_batch_main_sync()
{
	__resync_batch_master_sync "$FIX_MAIN_PATH" "$@"
}

resync_batch_changed()
{
	__fix_batch+=("$1")
}

resync_batch_commit()
{
	local msg="$1"

	commit "$msg" "${__fix_batch[@]}"
}
