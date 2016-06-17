#!/bin/bash
#
# Cherry-pick a list of patches described in a file
#
# ex: cherry-pick.sh -s -x commits.txt
#
# Create commits.txt using something of the form:
#
# git log --reverse --pretty=oneline v4.4..v4.6 -- drivers/net/ethernet/intel/i40e > commits.txt
#

#

set -e

KT_DIR=`dirname $0`
LF=/tmp/cherry-pick.log
CL=/tmp/cherry-pick-commit.log
CFT=/tmp/cherry-pick
MATCHES=/tmp/matches.log
NO_CHECK=

if [ ! -f $KT_DIR/perfect-git-subject-match ]
then
	(cd $KT_DIR; gcc -o perfect-git-subject-match perfect-git-subject-match.c)
fi

while [ "$1" != "" ]
do
	case "$1" in
		-s) SOB="$1"; shift;
		;;
		-x) CP="$1"; shift;
		;;
		-nc) NO_CHECK="1"; shift;
		;;
		*) if [ ! -f "$1" ] ; then echo Unknown option; exit 1; fi;
			CF="$1";
			shift;
		;;
	esac
done

if [ -z "${CF}" ] || [ ! -f ${CF} ]
then
	echo You must provide a list of commits to cherry pick.
	exit 1
fi

git log --pretty=oneline > ${CL}
cp ${CF} ${CFT}

CP_AWK=/tmp/cherry-pick.awk
cat > ${CP_AWK} << EOF
BEGIN { STRIP=1 }
/^diff / { STRIP=0 }
/^index / { next }
/^[-+]@@ / { next }
/^@@ / { next }
{
	if (STRIP == 0)
		print \$0
	next
}

EOF

cat ${CFT} | sed '/^#/d' | egrep -v "[a-f0-9] Merge [gtb]" | while read c j
do
	# See if its already applied. Make sure the subject is an exact match.
	$KT_DIR/perfect-git-subject-match "$j" < ${CL} > ${MATCHES}
	if grep -q -F "$j" ${MATCHES} && [ -z "$NO_CHECK" ]
	then
		#
		# Make really sure by counting the number of insertions.
		#
		if [ ! "`wc -l < ${MATCHES}`" = "1" ]
		then
			echo Too many matches for: $j
			exit 1
		fi
		IN_TREE_COMMIT=`sed 's/ .*$//' < ${MATCHES}`
		git format-patch -1 --stdout ${IN_TREE_COMMIT} > $$.${IN_TREE_COMMIT}.in-tree
		cat $$.${IN_TREE_COMMIT}.in-tree | gawk -f ${CP_AWK} > $$.1 
		git format-patch -1 --stdout ${c} > $$.${c}.upstream
		cat $$.${c}.upstream | gawk -f ${CP_AWK} > $$.2
		if [ ! "${IN_TREE_COMMIT}" = "${c}" ] && ! cmp $$.1 $$.2
		then
			echo Bogus compare on ${IN_TREE_COMMIT} and ${c}, "$j"
			#
			# Attempt to cherry pick, bail on failure.
			#
			if ! git cherry-pick ${CP} ${SOB} ${c} 2>&1 > ${LF}
			then
				echo Could not cherry-pick ${c} $j.
				diff -r -u --new-file $$.1 $$.2 > $$.diffs
				cat ${LF}
				exit 1
			fi
			if grep -q "error:" ${LF}
			then
				cat ${LF}
				exit 1
			fi
			echo "Cherry-picked duplicate: ${c} $j" > ${LF}
		else
			echo "Already applied: $j" > ${LF}
		fi
	elif ! git cherry-pick ${CP} ${SOB} $c 2>&1 > ${LF}
	then
		if grep -q "error:" ${LF}
		then
			cat ${LF}
			exit 1
		fi
		if ! grep -q "nothing to commit" ${LF}
		then
			echo Cherry pick failed on "$c $j"
			rm -f ${CFT}
			cat ${LF}
			exit 1
		fi
		echo "Cherry-picked ${c} $j" > ${LF}
	else
		echo "Cherry-picked ${c} $j" > ${LF}
	fi
	echo "#$c $j" >> ${CF}.done
	sed -i '/'$c'/d' ${CF}
	cat ${LF}
	rm -f $$.*
done

rm -f ${CFT} $$.*
