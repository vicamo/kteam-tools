#!/bin/bash
#
# Just source this file in your .bashrc:
#
# . /path/to/kteam-tools/cranky/cranky-complete.bash
#

_cranky() {
	local cur first cmd opts
	local cmds=(
		"build-sources -h --help -c --current --build-opts HANDLE"
		"checkout -h --help -r --reference -d --dissociate HANDLE"
		"chroot -h --help create-base create-session map-session run HANDLE"
		"clone -h --help -r --reference -d --dissociate HANDLE"
		"close -h --help -d --dry-run -c --include-config -s --skip-master"
		"fdr -h --help -c --clean"
		"fix -h --help"
		"link-tb -h --help -d --dry-run -r --re-run -s --sru-cycle"
		"list-routing -h --help -v --verbose HANDLE"
		"open -h --help -d --dry-run -r --reuse-abi"
		"rebase -h -r -b -l -d "
		"reorder -h --help -d --dry-run"
		"review -h --help -p --prev-dsc-dir -o --output"
		"rmadison -h --help -a --show-all -e --show-extended HANDLE"
		"spin -h --help -d --dry-run --devel HANDLE"
		"tag -h --help -v --verbose -f --force"
		"test-build -h --help -a --arch -c --commit -d --dry-run -f --fail -p --purge -t --target"
		"update-dependent -h --help --ignore-abi-check"
		"update-snap -h --help --dry-run -u --updates -t --no-tags"
		"updateconfigs -h --help -c --clean"
		"pull-source -h --help"
		"dput-sources -h --help -f --force -c --current -e --email HANDLE"
		"promote-snap -h --help --dry-run --debug"
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

	# Escape colons since bash completion handles them as special
	# characters in order to support completion for variables such
	# as PATH:
	cur="${COMP_WORDS[COMP_CWORD]//:/\\:}"
	mapfile -t COMPREPLY < <(compgen -W "$opts" -- "$cur")
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
	local shell_helper="$base_dir/cranky-shell-helper"
	local yaml_file="$base_dir/../info/kernel-series.yaml"

	if [ ! -e "$yaml_file" ] || [ ! -x "$shell_helper" ]; then
		return
	fi

	if [ ! -s "$cache_file" ] ||
		   [ "$cache_file" -ot "$yaml_file" ] ||
		   [ "$cache_file" -ot "$script_file" ]; then
		# Cache is old, rebuild it:
		if [ ! -e "$cache_dir" ]; then
			mkdir -p "$cache_dir"
		fi
		# Escape colons:
		"$shell_helper" list-handles | sed -e 's/:/\\\\&/g' > "$cache_file"
	fi
	tr '\n' ' ' < "$cache_file"
}

complete -F _cranky cranky
