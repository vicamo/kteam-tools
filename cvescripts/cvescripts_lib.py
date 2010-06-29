#!/usr/bin/python
#==============================================================================
# Author: Stefan Bader <stefan.bader@canonical.com>
# Copyright (C) 2010
#
# This script is distributed under the terms and conditions of the GNU General
# Public License, Version 3 or later. See http://www.gnu.org/copyleft/gpl.html
# for details.
#==============================================================================
import sys, os, ConfigParser, optparse
from subprocess import *
from getopt import *

cvescripts_cfg = os.path.expanduser(os.path.join('~', '.cvescripts.cfg'))
repo_host = "kernel.ubuntu.com"
http_host = "chinstrap.ubuntu.com"
repo_path = os.path.join("/home", "kernel-ppa", "security")

#------------------------------------------------------------------------------
# Little helper to remove quotes and expand the '~' constructs in paths.
#------------------------------------------------------------------------------
def ParsePath(path):
	if path[0] == '"' and path[-1] == '"':
		path = path[1:-1]
	if path[0] == '~':
		path = os.path.expanduser(path)
	return path

#------------------------------------------------------------------------------
# Read in the config file and set variables.
#------------------------------------------------------------------------------
# key, val = config.item("section")
# val = config.get("section", "name")
config = ConfigParser.ConfigParser()
try:
	config.read(cvescripts_cfg)
except:
	print "EE: Configuration file {0} not found!".format(cvescripts_cfg)
	sys.exit(1)
else:
	pass

#------------------------------------------------------------------------------
# There might or might not be a local clone of the upstream linux repo. This
# will be used to speed up cloning and decrease disk usage.
#------------------------------------------------------------------------------
try:
	kernel_reference = ParsePath(config.get("Paths", "kernelreference"))
except:
	kernel_reference = ""
else:
	pass

#------------------------------------------------------------------------------
# Set up login, ircnick, fullname and email for the current user.
#------------------------------------------------------------------------------
my_local_login = os.getlogin()
try:
	my_login = config.get(my_local_login, "login")
except:
	my_login = os.getlogin()
else:
	pass
try:
	my_ircnick = config.get(my_local_login, "ircnick")
except:
	my_ircnick = my_local_login
else:
	pass
try:
	my_fullname = config.get(my_local_login, "fullname")
except:
	my_fullname = os.getenv("DEBFULLNAME")
	if not my_fullname:
		print "EE: fullname is not set in config or environment"
		sys.exit(1)
else:
	pass
try:
	my_email = config.get(my_local_login, "email")
except:
	my_email = os.getenv("DEBEMAIL")
	if not my_email:
		print "EE: email is not set in config or environment"
		sys.exit(1)
else:
	pass

#------------------------------------------------------------------------------
# Libraries shared by all kteam-tools will be found here (../lib)
#------------------------------------------------------------------------------
cvescripts_common_lib = os.path.dirname(os.path.abspath(sys.argv[0]))
cvescripts_common_lib = os.path.dirname(cvescripts_common_lib)
cvescripts_common_lib = os.path.join(cvescripts_common_lib, "lib")
sys.path.insert(0, cvescripts_common_lib)

from git_lib import *
from cvetracker_lib import *
from workitem_lib import *
import cve_lib


def ListSupportedSeries():
	series = cve_lib.releases
	for eol in cve_lib.eol_releases:
		if eol in series:
			series.remove(eol)

	return series

#------------------------------------------------------------------------------
# PkgList is a dictionary containing per series information:
# PkgList[<series>][<package-shortname>] = <package-name>
#------------------------------------------------------------------------------
PkgList = dict()
PkgList["dapper"] = dict([
        ( "linux", "linux-source-2.6.15" ),
        ( "lbm", "linux-backports-modules-2.6.15" )
])
PkgList["hardy"] = dict([
	( "linux", "linux" ),
	( "lbm", "linux-backports-modules-2.6.24" ),
	( "lrm", "linux-restricted-modules-2.6.24" ),
	( "lum", "linux-ubuntu-modules-2.6.24" )
])
PkgList["intrepid"] = dict([
	( "linux", "linux" ),
	( "lbm", "linux-backports-modules-2.6.27" ),
	( "lrm", "linux-restricted-modules" )
])
PkgList["jaunty"] = dict([
	( "linux", "linux" ),
	( "lbm", "linux-backports-modules-2.6.28" ),
	( "lrm", "linux-restricted-modules" )
])
PkgList["karmic"] = dict([
	( "linux", "linux" ),
	( "lbm", "linux-backports-modules-2.6.31" ),
])
PkgList["lucid"] = dict([
	( "linux", "linux" ),
	( "lbm", "linux-backports-modules-2.6.32" )
])
PkgList["maverick"] = dict([
	( "linux", "linux" )
])

#------------------------------------------------------------------------------
# Make sure the given directory exists. Bail out if it cannot be created.
#------------------------------------------------------------------------------
def AssertDir(dir):
	if not os.path.isdir(dir):
		print "LL: Create " + dir + " ...",
		try:
			os.makedirs(dir)
		except:
			print "failed!"
			sys.exit(1)
		else:
			print "ok"

#------------------------------------------------------------------------------
# Return the path for saving workitem data/patches. Make sure path does exist.
#------------------------------------------------------------------------------
def GetSaveDir(base, name):
	savedir = os.path.join(base, "workitems", name)
	AssertDir(savedir)

	return savedir

#------------------------------------------------------------------------------
# Return a list of all working repositories (all series, all packages)
#------------------------------------------------------------------------------
def ListWorkareas():
	list = []
	for series in ListSupportedSeries():
		if not series in PkgList.keys():
			continue
		for package in sorted(PkgList[series].keys()):
			list.append(os.path.join(series, package))

	return list

#------------------------------------------------------------------------------
# Verify whether all repositories are clean and return True or False
#------------------------------------------------------------------------------
def IsWorkareaClean(branch=None):
	clean = True
	owd = os.getcwd()
	for area in ListWorkareas():
		os.chdir(area)
		files = GitListFiles(opts="--others --modified")
		if files:
			clean = False
			print "WW: Workarea not clean " + area
			for file in files:
				print "WW: - " + file
		if branch:
			if GitGetCurrentBranch() != branch:
				print "WW: Not on branch ", branch, area
				clean = False
		os.chdir(owd)

	return clean

def GetHttpLink():
	return "http://{0}/~{1}/CVEs/".format(http_host, my_login)

