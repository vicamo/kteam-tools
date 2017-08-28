#!/bin/bash

# bzr branch lp:ubuntu-cve-tracker
UCT=~/ubuntu/ubuntu-cve-tracker

RELEASE=( lucid \
	  precise \
	  trusty \
	  xenial )

declare -A RELEASE_DATE
RELEASE_DATE=( [lucid]="2010-04-29" \
		[precise]="2012-04-26" \
		[trusty]="2014-04-17" \
		[xenial]="2016-04-21" )

declare -A CVES_PER_YEAR
CVES_PER_YEAR=( [1]=0 \
       		[2]=0 \
		[3]=0 \
		[4]=0 \
		[5]=0 )

SEVERITY=( critical \
	   high \
	   medium \
	   low \
	   negligible \
	   unknown )
cd $UCT
./scripts/fetch-db database-all.pickle

for x in ${RELEASE[@]}
do
	echo "==== $x ===="
	CVES=/tmp/$x-cves.txt
	./scripts/report-updates.py --with-eol --db database-all.pickle | grep $x | grep ': linux ' | sort > $CVES
	for y in ${SEVERITY[@]}
	do
		echo -n "$y: "
		grep $y $CVES | wc -l
		for z in `grep $y $CVES | cut -d':' -f1`
		do
			DATE=${RELEASE_DATE[$x]}
			for i in {1..5}
			do
				NEXT_YEAR=$(date +%Y-%m-%d -d "$DATE + 1 year")
				#echo "DATE: $DATE"
				#echo "NEXT_YEAR: $NEXT_YEAR"
				if [[ "$z" > "$DATE" ]] ;
				then
					if [[ "$z" < "$NEXT_YEAR" ]] ;
					then
						#echo "$date_a->$z->$date_b"
						CVES_PER_YEAR[$i]=$((CVES_PER_YEAR[$i]+1))
						break
					fi
				fi
				DATE=$NEXT_YEAR
			done
		done

		DATE=${RELEASE_DATE[$x]}
		for i in {1..5}
		do
			NEXT_YEAR=$(date +%Y-%m-%d -d "$DATE + 1 year")
			echo "	$DATE to $NEXT_YEAR: ${CVES_PER_YEAR[$i]}"
			CVES_PER_YEAR[$i]=0
			DATE=$NEXT_YEAR
		done
	done
done

