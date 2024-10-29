#!/bin/bash -eu

verbose() {
	if false; then
		echo $@
	fi
}

result_entry() {
	local path="${1}"
	local serie="${2}"
	local message="${3}"
	local result="${4}"
	local operation="${5}"
	echo "${message}" 2>&1
	echo "${message}" >"${path}.${serie}.${operation}_${result}"
}

period="3 month"
while read -r entry; do
	series_regex="\[((([XxBbFfJjNnOo]([a-z:\-]+)?)[/]?)+)\]"
	patch_cnt_regex="\[.*([0-9]+\/[0-9]+)\]"
	echo ===============
	path="$(echo $entry | jq .path | tr -d '"')"
	subject="$(echo $entry | jq .path)"
	verbose $path
	if [ -f "$path.skip" ]; then
		echo "Skipping $subject"
		continue
	fi
	if ! raw_series=($(echo $entry | jq .subject | sed -nr "s@.*$series_regex.*@\1@p" | tr '/' ' ')) ||
		[ -z "${raw_series:-}" ]; then
		echo "Unable to find the series of $(echo $entry | jq .subject)" >&2
		continue
	fi
	if ! patch_cnt="$(echo $entry | jq .subject | sed -nr "s@.*$patch_cnt_regex.*@\1@p" | cut -d '/' -f 2)" ||
		[ -z "$patch_cnt" ]; then
		echo "Unable to find the patch count of $(echo $entry | jq .subject)" >&2
		continue
	fi
	verbose "Raw series: ${raw_series[@]}"
	verbose "Patch count: $patch_cnt"
	handles=()
	for i in "${!raw_series[@]}"; do
		case "${raw_series[$i]}" in
		[Oo]*)
			handles+=("oracular:linux")
			;;
		[Nn]*)
			handles+=("noble:linux")
			;;
		[Jj]*)
			handles+=("jammy:linux")
			;;
		[Ff]*)
			handles+=("focal:linux")
			;;
		[Bb]*)
			handles+=("bionic:linux")
			;;
		[Xx]*)
			handles+=("xenial:linux")
			;;
		*)
			result_entry "${path}" "${raw_series[$i]}" "Unable to understand handle" "failed" "parsing"
			unset raw_series[$i]
			;;
		esac
	done
	if [ "${#raw_series[@]}" -eq 0 ]; then
		error_log="Skipping $(echo $entry | jq .subject), no series"
		result_entry "${path}" "${raw_serie}" "$error_log" "failed" "parsing"
		continue
	fi
	# fix gaps in indexing from unset
	raw_series=("${raw_series[@]}")
	#loop over series
	for serie_index in ${!raw_series[@]}; do
		raw_serie="${raw_series[serie_index]}"
		handle="${handles[serie_index]}"
		serie="$(echo $handle | cut -d ":" -f 1)"
		paths=()
		subjects=()
		error=0
		# Find matching patches
		for i in $(seq $patch_cnt); do
			patch_cnt_regex="$i/$patch_cnt]"
			serie_regex="[\\\\[/]$(echo $raw_serie | sed 's/-/\\\\-/g')[/\\\\]]"
			if ! mail="$(mu find -o json -r -u "path:${path}" |
				jq -r '.[] | select(.":subject" | test("'$patch_cnt_regex'"))' |
				jq -r '. | select(.":subject" | test("'$serie_regex'"))' |
				jq -r -c '. | select(.":subject" | test("^\\["))')" ||
				[ -z "${mail:-}" ]; then
				echo "Unable to find $i/$patch_cnt patch of $(echo $entry | jq .subject)"
				error=1
				continue
			fi
			match_cnt="$(echo "$mail" | wc -l)"
			if ! [ "$match_cnt" -eq 1 ]; then
				echo "Too many matches ($match_cnt) for $i/$patch_cnt" >&2
				error=1
				continue
			fi
			paths+=("$(echo $mail | jq '.":path"' | tr -d '"')")
			subjects+=("$(echo $mail | jq '.":subject"')")
		done
		if [ "$error" -eq 1 ]; then
			error_log="Unable to find all patches, aborting processing $(echo $entry | jq .subject)"
			result_entry "${path}" "${raw_serie}" "$error_log" "failed" "parsing"
			continue
		fi
		for j in ${!paths[@]}; do
			echo "Going to apply ${subjects[j]} $(basename "${paths[j]}") on ${handle}"
		done
		if [ "${dry_run:-0}" -eq 1 ]; then
			continue
		fi
		if [ -f "$path.skip" ]; then
			echo "Skipping $subject, $path.skip" >&2
			continue
		fi
		if compgen -G "$path.$serie.am_failed" >/dev/null; then
			rm "$path.$serie.am_failed"
		fi
		if compgen -G "$path.$serie.build_*" >/dev/null; then
			echo "Skipping $subject, already built : $path.build_*" >&2
			continue
		fi
		if compgen -G "$path.$serie.building" >/dev/null; then
			echo "Building $subject : $path.build_*" >&2
			# TODO Collect result of ongoing build
			continue
		fi
		(cd ~/canonical/kernel/ubuntu/$serie/linux && git checkout cranky/master-next && git reset --hard origin/master-next)
		error=0
		for i in ${!paths[@]}; do
			if ! (cd ~/canonical/kernel/ubuntu/$serie/linux &&
				git am --ignore-space-change "${paths[i]}"); then
				echo "Unable to apply ${subjects[i]} on $handle" >&2
				(cd ~/canonical/kernel/ubuntu/$serie/linux && git am --abort)
				touch "${paths[i]}.${serie}.am_failed"
				error=1
			else
				touch "${paths[i]}.${serie}.am_succeed"
			fi
		done
		if [ "$error" -eq 1 ]; then
			error_log="Unable to apply a patch, aborting processing $(echo $entry | jq .subject)"
			result_entry "${path}" "${serie}" "$error_log" "failed" "am"
			continue
		fi
		touch "${path}.${serie}.am_succeed"
		log_file="$(mktemp -p /tmp check-pending.XXXX)"
		if ! (cd ~/canonical/kernel/ubuntu/$serie/linux && git push --progress ${arch:+-o "${arch}"} ${debug:+-o debug} cbd "HEAD:refs/heads/$(basename "$path")" 2>&1 | tee "${log_file}"); then
			echo "git push failed, temporary error ?"
			continue
		fi
		build_path="$(grep "${arch:-}/BUILD-" "${log_file}" | head -n 1 | awk '{print $4}')"
		if grep -q BUILD-FAILED "${log_file}"; then
			echo $build_path >"${path}.${serie}.build_failed"
		else
			echo $build_path >"${path}.${serie}.build_succeed"
		fi
		grep BUILD "${log_file}" | grep -v BUILDING
		rm "${log_file}"
	done
done <<<$(./pending_SRU.sh -p "${period}" -j | jq -c '.[]')
