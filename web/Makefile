
reports: kernel-sru-workflow.html fetch-data sru-report.html

every-hour: 1-day-new.html

every-day: versions.html 30-day-new.html

.PHONY : sru-data.json
sru-data.json:
	kteam-tools/stable/sru-report --archive-versions > $@.tmp
	@if [ -s $@.tmp ]; then \
	    mv $@.tmp $@; \
	fi

sru-report.html: sru-data.json scripts/sru2html
	scripts/sru2html $< > $@.tmp
	@if [ -s $@.tmp ]; then \
	    mv $@.tmp $@; \
	fi

versions.html: sru-data.json scripts/versions2html
	scripts/versions2html $< > $@.tmp
	@if [ -s $@.tmp ]; then \
	    mv $@.tmp $@; \
	fi

shankbot: kernel-sru-workflow.html
	cp *.json dashboards
	(cd dashboards;./generate-dashboard kernel-stable-dashboard.rc > k-dashboard.tmp && cp k-dashboard.tmp web/kernel-stable-dashboard.html)

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
	scripts/mk-regressions-report --sru=sru-data.json $< > $@.tmp
	@if [ -s $@.tmp ]; then \
	    mv $@.tmp $@; \
	fi

.PHONY : kernel-sru-workflow.json
kernel-sru-workflow.json:
	cp kernel-sru-workflow-bare.json $@.tmp
	timeout 1h scripts/cbd --db=$@.tmp
	mv $@.tmp $@

kernel-sru-workflow.html: kernel-sru-workflow.json
	scripts/gen-workflow-report $< > $@

.PHONY : kernel-cves.html
kernel-cves.html: scripts/kernel-cves
	(cd kteam-tools/cvescripts;python kernel-cves.py); mv kteam-tools/cvescripts/kernel-cves.html .

.PHONY : kt-meeting.txt
kt-meeting.txt: scripts/kt-meeting-stats
	scripts/kt-meeting-stats
