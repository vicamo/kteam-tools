#!/bin/bash
#
# Just source this file in your .bashrc:
#
# . /path/to/kteam-tools/cranky/cranky-complete.bash
#

_cranky() {
	local first cmd opts prev
	local cmds=(
		"build-sources -h --help -c --current --build-opts HANDLE"
		"check-packaging -h --help"
		"checkout -h --help -r --reference -d --dissociate --depth --cycle --cleanup --pristine HANDLE"
		"chroot -h --help create-base create-session map-session run destroy-session HANDLE"
		"close -h --help -d --dry-run -c --include-config -s --skip-master --use-cuc"
		"cycles -h --help -v --dry-run destroy list -a --after -b --before -d --descending rebuild -p --package main meta signed lrm lrs lrg lum lbm HANDLE"
		"diff-sauce -h --help TAG"
        "distribute-kernels -h --help --cycle --step"
		"dput-sources -h --help -f --force -c --current -e --email HANDLE"
		"fdr -h --help -c --clean"
		"fix -h --help"
		"format-kernel-series -h --help"
		"link-tb -h --help -d --dry-run -r --re-run -s --sru-cycle -c --cve"
		"list-derivatives -h --help -v --verbose --has-lrm --has-signed HANDLE"
		"list-owners -h --help -v --verbose --include-esm --include-devel --by-owner HANDLE"
		"list-repos -h --help -v --verbose -g --git-url --supported-sources --base-sources --derivative-sources --include main meta signed lrm lrs lrg lum lbm HANDLE"
		"list-routing -h --help -v --verbose HANDLE"
		"open -h --help -d --dry-run -r --reuse-abi"
		"promote-snap -h --help --dry-run --debug"
		"pull-review -h --help --dry-run"
		"pull-source -h --help -n --no-verify"
		"pull-sources  -h --help -n --no-verify -l --latest HANDLE"
		"push-refs -h --help --nc --dry-run HANDLE"
		"push-review -h --help -d --dry-run -s --sru-cycle -f --force"
		"rebase -h --help -r -b -l -d --dry-run"
		"reorder -h --help -d --dry-run"
		"review -h --help -p --prev-dsc-dir -o --output"
		"review-master-changes -h --help"
		"rmadison -h --help -a --show-all -e --show-extended -p --pocket release updates security proposed HANDLE"
		"shell-helper -h handle-to-series-source series-codename package-name source-packages-path read-swm-property tree-type tree-main-path list-handles list-cycles list-variants config source-packages-name"
		"startnewrelease -h --help -c --commit"
		"tag -h --help -v --verbose -f --force"
		"tags -h --help -v --verbose -f --force"
		"test-build -h --help -a --arch -c --commit -d --dry-run -f --fail -o --outdir -p --purge -t --target"
		"update-dependent -h --help --ignore-abi-check"
		"update-dependent-version -h --help --commit --no-update --main-version --namespace"
		"update-dependents -h --help --ignore-abi-check -r --rollback"
		"update-dkms-versions -h --help -r --remote-repo -b --remote-branch -s --sru-cycle -x --debug"
		"update-snap -h --help --dry-run -u --updates -t --no-tags"
		"updateconfigs -h --help -c --clean"
		"verify-release-ready -h --help -c --current -d --debug -v --verbose"
		"view-repos -h --help -i --include HANDLE"
	)
	if [ "$COMP_CWORD" -eq 1 ]; then
		for cmd in "${cmds[@]}"; do
			opts+=$(_cranky_expand_handles "${cmd%% *} ")
		done
	else
		first="${COMP_WORDS[1]}"
		prev="${COMP_WORDS[COMP_CWORD-1]}"
		if [ "$first" = "checkout" ] && [ "$prev" = "--cycle" ]; then
			opts+=$(_cranky_get_info "cycles")
		else
			for cmd in "${cmds[@]}"; do
				if [ "$first" = "${cmd%% *}" ]; then
					opts+=$(_cranky_expand_handles "${cmd#* } ")
				fi
			done
		fi
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
	local tags
	local s
	case "$@" in
		*TAG*)
			tags=$(_cranky_get_tags)
			;;
		*HANDLE*)
			handles=$(_cranky_get_info "handles")
			;;
	esac
	s=$@
	s="${s//HANDLE/$handles}"
	s="${s//TAG/$tags}"
	echo "$s"
}

_cranky_get_tags() {
	git tag -l --no-color | tr '\n' ' '
}

_cranky_script_file="$0"
_cranky_get_info() {
	# Cache the results here in the script to avoid the annoying
	# delay caused by invoking the python interpreter and parsing
	# the YAML file.
	local base_dir=
	local script_file="${BASH_SOURCE[0]:-$_cranky_script_file}"
	base_dir="$(dirname "$script_file")"
	local cache_dir=~/.cache/cranky
	local cranky="$base_dir/cranky"
	local cache_file yaml_file cranky_cmd
	kernel_versions_dir="${KERNEL_VERSIONS:-}"
	if ! [ -d "$kernel_versions_dir" ]; then
		kernel_versions_dir="$base_dir/../../kernel-versions"
	fi
	case "$1" in
		handles)
			cache_file="$cache_dir/handles"
			yaml_file="$kernel_versions_dir/info/kernel-series.yaml"
			cranky_cmd="list-handles"
			;;
		cycles)
			cache_file="$cache_dir/cycles"
			yaml_file="$kernel_versions_dir/info/sru-cycle.yaml"
			cranky_cmd="list-cycles"
			;;
		*)
			return
			;;
	esac

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
		"$cranky" shell-helper "$cranky_cmd" > "$cache_file"
	fi
	tr '\n' ' ' < "$cache_file"
}

complete -F _cranky cranky
