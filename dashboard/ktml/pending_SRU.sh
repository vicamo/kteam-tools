#!/bin/bash -eu

this="$(basename "$0")"
help() {
	cat <<EOF
Usage: ${this} [-h|--help] [-s|--start START] [-e|--end END] [-m|--mail] [-p|--period] [-a|--all] [-v|--verbose]

Lists the patches pending review in the given period. Uses mu searches
to find and sort the threads.

Optional arguments:
  -a, --all             List all SRU patches.
  -s, --start           Start date. Can use any format accepted by
                        "date --date", ie "last monday" or "today".
                        Default: none.
  -e, --end             End date. Can use any format accepted by
                        "date --date", in the same ways as --start.
                        Default: "last friday".
  -p, --period          Period to be subtracted from --end. Can use any
                        format supported by "date --date", ie "1 week".
                        Default: "7 days".
  -m, --mail            Only list patches pending review from the point
                        of view of a specific mail.
  -j, --json            Show result in a json format.
  -v, --verbose         Increase verbosity.
  -h, --help            Show this help message and exit.

Examples:
  Basic usage with default period (last week):
    \$ ${this}

  Yesterday:
    \$ ${this} --end yesterday --period "1 day"

  Last 30 days:
    \$ ${this} --end today --period "30 day"

EOF
}

verbose() {
	if [ "$verbose" -eq 1 ]; then
		echo "$1" >&2
	fi
}
# Parse arguments
all=0
start=
end=
period=
usermail=
json=0
verbose=0
while [ "$#" -gt 0 ]; do
	case "$1" in
	-a | --all)
		all=1
		;;
	-h | --help)
		help
		exit 0
		;;
	-s | --start)
		shift
		start="$1"
		;;
	-e | --end)
		shift
		end="$1"
		;;
	-p | --period)
		shift
		period="$1"
		;;
	-m | --mail)
		shift
		usermail="$1"
		;;
	-j | --json)
		json=1
		;;
	-v | --verbose)
		verbose=1
		;;
	*)
		echo "Invalid arguments!"
		help
		exit 1
		;;
	esac
	shift
done

# Check args
if [ -n "$start" ] && [ -n "$period" ]; then
	echo '"start" and "period" are mutually exclusive!' >&2
	exit 1
fi
if [ "$all" -eq 1 ] && [ -n "$usermail" ]; then
	echo '"all" and "mail" are mutually exclusive!' >&2
	exit 1
fi

# Default arguments
end="${end:-today}"
if [ -z "$start" ]; then
	period="${period:-7 days}"
	# mu date ranges are inclusive
	start="${end} - ${period} + 1 day"
fi

# Convert
end=$(date --date="${end}" +%Y%m%d)
begin=$(date --date="${start}" +%Y%m%d)
verbose "# period=[${begin}, ${end}]"

mu_query='(
	to:kernel-team@lists.ubuntu.com OR
	cc:kernel-team@lists.ubuntu.com OR
	list:kernel-team.lists.ubuntu.com OR
	to:canonical-kernel-esm@lists.canonical.com OR
	cc:canonical-kernel-esm@lists.canonical.com OR
	list:canonical-kernel-esm.lists.canonical.com
)'

expected_acks=2
count_pending=0
total=0
subjects=()
pending_acks=()
authors=()
paths=()
emails=()
threads=()

ack_regex='ACK'
nack_regex='(NAK|NACK)'
applied_regex='APPLIED'

incl_regex='\[(SRU|PATCH|PULL)\]'
excl_regex='(upstream stable release|\[UCT\]|add break commit)'

# shellcheck disable=SC2046
while read -r path; do
	subject=$(mu find -o json -u "path:\"${path}\"" | jq -r '.[][":subject"]')

	if ! echo "$subject" | grep -qP "${incl_regex}"; then
		verbose "Not included: $subject"
		continue
	fi
	if echo "$subject" | grep -qP "${excl_regex}"; then
		verbose "Excluded: $subject"
		continue
	fi
	total="$((total + 1))"
	thread=$(mu find -o json -r -u "path:\"${path}\"")
	thread_subjects=$(echo "${thread}" | jq -r '.[][":subject"]')

	applied=$(echo "$thread_subjects" | grep -c -P "${applied_regex}" || true)
	if [ "$all" -eq 0 ] && [ "$applied" -gt 0 ]; then
		verbose "Applied: $subject"
		continue
	fi

	nacks=$(echo "$thread_subjects" | grep -c -P "${nack_regex}" || true)
	if [ "$all" -eq 0 ] && [ "$nacks" -gt 0 ]; then
		verbose "Nacked: $subject"
		continue
	fi

	acks=$(echo "$thread_subjects" | grep -c -P "${ack_regex}" || true)
	if [ "$all" -eq 0 ] && [ "$acks" -ge "$expected_acks" ]; then
		verbose "ACKED: $subject"
		continue
	fi
	# Check if usermail acked the thread
	if review="$(mu find -o json -r -u "path:\"${path}\"" |
		jq -r --arg incl_regex "$incl_regex" --arg ack_regex "$ack_regex" -e '.[] | select((.":subject"|test($ack_regex))).":from"[0].":email"' 2>/dev/null)"; then
		:
	fi
	if [ -n "$usermail" ] && [ "$review" = "$usermail" ]; then
		continue
	fi

	name=$(mu find -o json -u "path:\"${path}\"" | jq -r '.[][":from"][0][":name"]')
	email=$(mu find -o json -u "path:\"${path}\"" | jq -r '.[][":from"][0][":email"]')
	[ "${name}" = null ] && name=''
	subjects+=("$subject")
	authors+=("${name} <${email}>")
	emails+=("${email}")
	pending_acks+=("$((expected_acks - acks))")
	reviewer+=("${review}")
	paths+=("${path}")
	threads+=("${thread}")
	count_pending="$((count_pending + 1))"
done <<<$(mu find -o json -u "date:${begin}..${end} and ${mu_query}" |
	jq -r '.[] | select(.[":references"] == null) | .[":path"]')

count="${!authors[*]}"
if [ "$json" -eq 0 ]; then
	for i in $count; do
		echo "Subject: ${subjects[i]}"
		echo "From: ${authors[i]}"
		echo "Pending ACKs: ${pending_acks[i]}"
		echo "Reviewed-by: ${reviewer[i]}"
	done
	echo "Review pending: ${count_pending}"
	echo "Total SRU submitted: ${total}"
else
	echo "["
	for i in $count; do
		escaped_subject="${subjects[i]//\"/\\\"}"
		echo "{\"subject\": \"${escaped_subject}\",\"path\": \"${paths[i]}\",\"from\": \"${authors[i]}\",\"email\":\"${emails[i]}\", \"pending_acks\": ${pending_acks[i]}, \"reviewer\":\"${reviewer[i]//[$'\t\r\n ']/,}\", \"patches\": ${threads[i]}}"
		if [ "$((i + 1))" -lt ${#authors[@]} ]; then
			echo ","
		fi
	done
	echo "]"
fi
