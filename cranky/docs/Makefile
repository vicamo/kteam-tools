# Makefile to turning .md files into .html files
#
# You will want to 'sudo -H pip install grip' to get the tool used here installed
# on your local system.
#

TARGETS=cranking-the-kernel.html crank-turning-setup.html sru-cycles.html

%.html: %.md
	grip $< --export

all: $(TARGETS)

clean:
	rm -f $(TARGETS)
