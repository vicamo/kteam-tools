# Makefile to turning .md files into .html files
#
# You will want to 'sudo -H pip install grip' to get the tool used here installed
# on your local system.
#

TARGETS=cranking-the-kernel.cheatsheet.html cranking-the-kernel.html crank-turning-setup.html hinting-tests.html sru-cycles.html verification-testing.html
CHEATSHEET_TARGETS=cranking-the-kernel.cheatsheet.md

%.cheatsheet.md: %.md
	$(PWD)/cranky-generate-cheatsheet < $< > $@

%.html: %.md
	grip $< --export

all: $(CHEATSHEET_TARGETS) $(TARGETS)

clean:
	rm -f $(CHEATSHEET_TARGETS) $(TARGETS) *.html
