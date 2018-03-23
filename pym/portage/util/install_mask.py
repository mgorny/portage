# Copyright 2018 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

__all__ = ['install_mask_dir', 'InstallMask']

import errno
import fnmatch
import sys

from portage import os, _unicode_decode
from portage.exception import (
	OperationNotPermitted, PermissionDenied, FileNotFound)
from portage.util import normalize_path

if sys.hexversion >= 0x3000000:
	_unicode = str
else:
	_unicode = unicode


class InstallMask(object):
	def __init__(self, install_mask):
		"""
		@param install_mask: INSTALL_MASK value
		@type install_mask: str
		"""
		self._install_mask = install_mask.split()

	def match(self, path):
		"""
		@param path: file path relative to ${ED}
		@type path: str
		@rtype: bool
		@return: True if path matches INSTALL_MASK, False otherwise
		"""
		ret = False
		for pattern in self._install_mask:
			# if pattern starts with -, possibly exclude this path
			is_inclusive = not pattern.startswith('-')
			if not is_inclusive:
				pattern = pattern[1:]
			# absolute path pattern
			if pattern.startswith('/'):
				# match either exact path or one of parent dirs
				# the latter is done via matching pattern/*
				if (fnmatch.fnmatch(path, pattern[1:])
						or fnmatch.fnmatch(path, pattern[1:] + '/*')):
					ret = is_inclusive
			# filename
			else:
				if fnmatch.fnmatch(os.path.basename(path), pattern):
					ret = is_inclusive
		return ret
