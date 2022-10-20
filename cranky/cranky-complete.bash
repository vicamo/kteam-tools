#!/bin/bash
#
# Just source this file in your .bashrc:
#
# . /path/to/kteam-tools/cranky/cranky-complete.bash
#

_cranky() {
	local first cmd opts
	local cmds=(
		"build-sources -h --help -c --current --build-opts HANDLE"
		"checkout -h --help -r --reference -d --dissociate --depth HANDLE"
		"chroot -h --help create-base create-session map-session run destroy-session HANDLE"
		"close -h --help -d --dry-run -c --include-config -s --skip-master"
		"dput-sources -h --help -f --force -c --current -e --email HANDLE"
		"fdr -h --help -c --clean"
		"fix -h --help"
		"link-tb -h --help -d --dry-run -r --re-run -s --sru-cycle -c --cve"
		"list-repos -h --help -v --verbose -g --git-url --include main meta signed lrm lrs lrg lum lbm HANDLE"
		"list-routing -h --help -v --verbose HANDLE"
		"list-derivatives -h --help -v --verbose --has-lrm --has-signed HANDLE"
		"list-owners -h --help -v --verbose --include-esm --include-devel --by-owner HANDLE"
		"open -h --help -d --dry-run -r --reuse-abi"
		"promote-snap -h --help --dry-run --debug"
		"pull-source -h --help"
		"rebase -h -r -b -l -d "
		"reorder -h --help -d --dry-run"
		"review -h --help -p --prev-dsc-dir -o --output"
		"review-master-changes -h --help"
		"rmadison -h --help -a --show-all -e --show-extended -p --pocket release updates security proposed HANDLE"
		"shell-helper -h handle-to-series-source series-codename source-packages-path tree-type tree-main-path list-handles list-variants clone test-build review-master-changes"
		"spin -h --help -d --dry-run --devel HANDLE"
		"tag -h --help -v --verbose -f --force"
		"test-build -h --help -a --arch -c --commit -d --dry-run -f --fail -p --purge -t --target"
		"update-dependent -h --help --ignore-abi-check"
		"update-snap -h --help --dry-run -u --updates -t --no-tags"
		"updateconfigs -h --help -c --clean"
	)
	if [ "$COMP_CWORD" -eq 1 ]; then
		for cmd in "${cmds[@]}"; do
			opts+=$(_cranky_expand_handles "${cmd%% *} ")
		done
	else
		first="${COMP_WORDS[1]}"
		for cmd in "${cmds[@]}"; do
			if [ "$first" = "${cmd%% *}" ]; then
				opts+=$(_cranky_expand_handles "${cmd#* } ")
			fi
		done
	fi

	_cranky_compat_complete "$opts"
}

# Starting with Kinetic (bash-5.2), completion of a HANDLE as used in cranky
# is broken. The previous method of escaping ':' is no longer sufficient for
# expanding handles properly. This function depends on bash-completion being
# present and properly sourced in your shell. If the necessary functions are
# not found, cranky completion for handles will silently fail.
_cranky_compat_complete() {
	local opts="$1"

	local cur
	if type _get_comp_words_by_ref &>/dev/null; then
		_get_comp_words_by_ref -n : cur
	fi

	COMPREPLY=( $(compgen -W "$opts" -- "$cur") )

	if type __ltrim_colon_completions &>/dev/null; then
		__ltrim_colon_completions "$cur"
	fi
}

_cranky_expand_handles() {
	local handles
	case "$@" in
		*HANDLE*)
			handles=$(_cranky_get_handles)
			;;
	esac
	echo "${@//HANDLE/$handles}"
}

_cranky_get_handles() {
	# Cache the results here in the script to avoid the annoying
	# delay caused by invoking the python interpreter and parsing
	# the YAML file.
	local base_dir=
	local script_file="${BASH_SOURCE[0]}"
	base_dir="$(dirname "$script_file")"
	local cache_dir=~/.cache/cranky
	local cache_file="$cache_dir/handles"
	local cranky="$base_dir/cranky"
	local yaml_file="$base_dir/../info/kernel-series.yaml"

	if [ ! -e "$yaml_file" ]; then
		return
	fi

	if [ ! -s "$cache_file" ] ||
		   [ "$cache_file" -ot "$yaml_file" ] ||
		   [ "$cache_file" -ot "$script_file" ]; then
		# Cache is old, rebuild it:
		if [ ! -e "$cache_dir" ]; then
			mkdir -p "$cache_dir"
		fi
		"$cranky" shell-helper list-handles > "$cache_file"
	fi
	tr '\n' ' ' < "$cache_file"
}

complete -F _cranky cranky
