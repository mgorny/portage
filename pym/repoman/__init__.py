
import os.path
import subprocess
import sys
import time

try:
	import portage.const
	import portage.proxy as proxy
	from portage import _encodings, _shell_quote, _unicode_encode, _unicode_decode
	from portage.const import PORTAGE_BASE_PATH, BASH_BINARY
except ImportError as e:
	sys.stderr.write("\n\n")
	sys.stderr.write("!!! Failed to complete portage imports. There are internal modules for\n")
	sys.stderr.write("!!! portage and failure here indicates that you have a problem with your\n")
	sys.stderr.write("!!! installation of portage. Please try a rescue portage located in the\n")
	sys.stderr.write("!!! portage tree under '/usr/portage/sys-apps/portage/files/' (default).\n")
	sys.stderr.write("!!! There is a README.RESCUE file that details the steps required to perform\n")
	sys.stderr.write("!!! a recovery of portage.\n")
	sys.stderr.write("    "+str(e)+"\n\n")
	raise

if sys.hexversion >= 0x3000000:
	# pylint: disable=W0622
	long = int

REPOMAN_BASE_PATH = os.path.join(os.sep, os.sep.join(os.path.realpath(__file__.rstrip("co")).split(os.sep)[:-3]))

_not_installed = os.path.isfile(os.path.join(REPOMAN_BASE_PATH, ".portage_not_installed"))
