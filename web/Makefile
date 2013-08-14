
reports: kernel-sru-workflow.html fetch-data sru-report.html

every-hour: 1-day-new.html

every-day: versions.html 30-day-new.html

fetch-data:
	@kteam-tools/stable/sru-report --archive-versions > sru-data-tmp.json
	@if [ -s sru-data-tmp.json ]; then \
	    mv sru-data-tmp.json sru-data.json; \
	fi

sru-report.html: sru-data.json scripts/sru2html
	scripts/sru2html $< > $@

versions.html: sru-data.json scripts/versions2html
	scripts/versions2html $< > $@



regressions-data: regressions-potential-data.json regressions-release-data.json regressions-update-data.json regressions-proposed-data.json

.PHONY : regressions-potential-data.json
regressions-potential-data.json: scripts/collect-regressions-data
	scripts/collect-regressions-data --potential --db=$@

.PHONY : regressions-release-data.json
regressions-release-data.json: scripts/collect-regressions-data
	scripts/collect-regressions-data --release --db=$@

.PHONY : regressions-update-data.json
regressions-update-data.json: scripts/collect-regressions-data
	scripts/collect-regressions-data --update --db=$@

.PHONY : regressions-proposed-data.json
regressions-proposed-data.json: scripts/collect-regressions-data
	scripts/collect-regressions-data --proposed --db=$@


regressions-reports: regressions-data regressions-potential-report.html regressions-release-report.html regressions-update-report.html regressions-proposed-report.html

regressions-potential-report.html: regressions-potential-data.json
	scripts/mk-regressions-report --sru=sru-data.json $< > $@

regressions-release-report.html: regressions-release-data.json
	scripts/mk-regressions-report --sru=sru-data.json $< > $@

regressions-update-report.html: regressions-update-data.json
	scripts/mk-regressions-report --sru=sru-data.json $< > $@

regressions-proposed-report.html: regressions-proposed-data.json
	scripts/mk-regressions-report --sru=sru-data.json $< > $@

clean:
	rm -f *.json sru-report.html versions.html

.PHONY : 30-day-window.json
30-day-window.json:
	scripts/collect-window-data --window=30 --db=$@ --title="30 Days of New Bugs"

30-day-new.html: 30-day-window.json
	scripts/mk-regressions-report --sru=sru-data.json $< > $@

.PHONY : 7-day-window.json
7-day-window.json:
	scripts/collect-window-data --window=7 --db=$@ --title="7 Days of New Bugs"

7-day-new.html: 7-day-window.json
	scripts/mk-regressions-report --sru=sru-data.json $< > $@

.PHONY : 1-day-window.json
1-day-window.json:
	scripts/collect-window-data --window=1 --db=$@ --title="24 Hours of New Bugs"

1-day-new.html: 1-day-window.json
	scripts/mk-regressions-report --sru=sru-data.json $< > $@

.PHONY : kernel-sru-workflow.json
kernel-sru-workflow.json:
	cp kernel-sru-workflow-bare.json kernel-sru-workflow.json
	scripts/cbd --db=$@

kernel-sru-workflow.html: kernel-sru-workflow.json
	scripts/gen-workflow-report $< > $@

.PHONY : kernel-cves.html
kernel-cves.html: scripts/kernel-cves
	scripts/kernel-cves

.PHONY : kt-meeting.txt
kt-meeting.txt: scripts/kt-meeting-stats
	scripts/kt-meeting-stats
