#!/usr/bin/python
#==============================================================================
# Author: Stefan Bader <stefan.bader@canonical.com>
# Copyright (C) 2010
#
# This script is distributed under the terms and conditions of the GNU General
# Public License, Version 3 or later. See http://www.gnu.org/copyleft/gpl.html
# for details.
#==============================================================================
import sys, os, re, signal
from subprocess import *
from git_lib import *

'''GetDebianDir(sha1=None)

	Get the directory where the debian config files are located. Usually
	this is "./debian", but for abstracted debian it might be an alternate
	directory.

	sha1	Can be used to select a specific commit or branch in history.
'''
def GetDebianDir(sha1=None):
	debian = None
	#----------------------------------------------------------------------
	# First try the contents of 'debian/debian.env'
	#----------------------------------------------------------------------
	for line in GitCatFile(os.path.join("debian", "debian.env"), sha1=sha1):
		if "DEBIAN=" in line:
			return line.split("=", 1)[1].strip()

	#----------------------------------------------------------------------
	# Older versions had a declaration in 'debian/rules'
	#----------------------------------------------------------------------
	for line in GitCatFile(os.path.join("debian", "rules"), sha1=sha1):
		if "DEBIAN=" in line:
			return line.split("=", 1)[1].strip()

	#----------------------------------------------------------------------
	# Oh, well. So it must be 'debian'.
	#----------------------------------------------------------------------
	return "debian"

'''GetPackageInfo(sha1=None, prev=False)

	Returns a list of four elements (name, version, pocket and options)
	of the changelog.

	sha1	can be used to return the values at that point in history or
		on another branch.
	prev	if set to True will return data of the previous release in
		that changelog.
'''
def GetPackageInfo(sha1=None, prev=False):
	changelog = os.path.join(GetDebianDir(sha1=sha1), "changelog")
	for line in GitCatFile(changelog, sha1=sha1):
		if line[0] != " " and line[0] != "	" and line[0] != "\n":
			(name, ver, pocket, opt) = line.rstrip().split(" ")
			ver = ver[1:-1]
			if pocket[-1] == ";":
				pocket = pocket[0:-1]
			if prev == False:
				return [name, ver, pocket, opt]
			prev = False
	return None

'''RunScript(script, host=None, interpreter=None)

	Execute the given script either locally or on a remote host

	@script		string containing the script
	@host		name of the host to execute on
	@interpreter	run the command/script by this interpreter (default
			is /bin/sh)
	@timeout	only used when running remotely, this is the ssh
			timeout

	Returns triple (<returncode>, <stdout>, <stderr>)
		stdout and stderr are strings
'''
def RunScript(script, host=None, interpreter=None, timeout=60,
		getoutput=True):
	if not interpreter:
		interpreter = "/bin/sh"
	cmd = []
	if host:
		cmd.extend([ "ssh", "-oConnectTimeout=" + str(timeout), host ])
	cmd.append(interpreter)

	# Python installs a SIGPIPE handler by default. This is usually
	# not what non-Python subprocesses expect. From:
	# http://www.chiark.greenend.org.uk/ucgi/~cjwatson/blosxom/2009-07-02-python-sigpipe.html
	# Since we are running an shell script, we must switch back, and
	# restore SIGPIPE back to default, so we avoid any spurious
	# "stdout: Broken pipe" errors, with any side effects it may
	# cause on shell commands using pipes
	def sp_setup():
		signal.signal(signal.SIGPIPE, signal.SIG_DFL)

	if getoutput:
		p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE,
			  preexec_fn=sp_setup)
		(pout, perr) = p.communicate(input=script)
	else:
		p = Popen(cmd, stdin=PIPE, preexec_fn=sp_setup)
		(pout, perr) = p.communicate(input=script)
	
	return (p.returncode, pout, perr)

