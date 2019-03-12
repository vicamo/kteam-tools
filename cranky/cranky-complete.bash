#!/bin/bash
#
# Just source this file in your .bashrc:
#
# . /path/to/kteam-tools/cranky/cranky-complete.bash
#

cmds=(
	"build-sources -h --help"
	"chroot -h --help create-base create-session map-session run"
	"clone -h --help -r --reference -d --dissociate"
	"checkout -h --help -r --reference -d --dissociate"
	"close -h --help -d --dry-run -c --include-config -s --skip-master"
	"fix -h --help"
	"link-tb -h --help -d --dry-run -r --re-run -s --sru-cycle"
	"list-routing -h --help -v --verbose"
	"open -h --help -d --dry-run -r --reuse-abi"
	"rebase -h -r -b -l -d "
	"reorder -h --help -d --dry-run"
	"review -h --help -p --prev-dsc-dir -o --output"
	"rmadison -h --help -a --show-all -e --show-extended"
	"test-build -h --help -a --arch -c --commit -d --dry-run -f --fail -p --purge -t --target"
	"update-snap -h --help --dry-run -u --updates -t --no-tags"
	"updateconfigs -h --help"
)

_cranky() {
	local opts=
	if [ "$COMP_CWORD" -eq 1 ]; then
		for cmd in "${cmds[@]}"; do
			opts+="${cmd%% *} "
		done
	else
		cur="${COMP_WORDS[1]}"
		for cmd in "${cmds[@]}"; do
			if [ "$cur" = "${cmd%% *}" ]; then
				opts+="${cmd#* } "
			fi
		done
	fi
	COMPREPLY=($(compgen -W "$opts" -- "${COMP_WORDS[COMP_CWORD]}"))
}
complete -F _cranky cranky
