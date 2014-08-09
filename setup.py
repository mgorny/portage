#!/usr/bin/env python
#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from distutils.core import setup
from distutils.command.install import install
from distutils.command.install_lib import install_lib

import codecs, os, os.path, re


extra_install_options = [
	('portage-base=', 'b', "Portage install base"),
]

extra_install_option_mapping = [
	('portage_base', 'portage_base'),
]


class x_install(install):
	""" install command with extra Portage paths """

	user_options = install.user_options + extra_install_options

	def initialize_options(self):
		install.initialize_options(self)
		self.portage_base = '/usr/lib/portage'


class x_install_lib(install_lib):
	""" install_lib command with Portage path substitution """

	user_options = install_lib.user_options + extra_install_options

	def initialize_options(self):
		install_lib.initialize_options(self)
		self.portage_base = None

	def finalize_options(self):
		install_lib.finalize_options(self)
		self.set_undefined_options('install', *extra_install_option_mapping)

	def install(self):
		ret = install_lib.install(self)

		repl_re = re.compile(r'(^PORTAGE_BASE_PATH.*=) .*$', re.MULTILINE)

		constfile = os.path.join(self.install_dir, 'portage', 'const.py')
		print('Rewriting %s' % constfile)
		with codecs.open(constfile, 'r', 'utf-8') as f:
			data = f.read()
		data = repl_re.sub('\\1 %s' % repr(self.portage_base), data)
		with codecs.open(constfile, 'w', 'utf-8') as f:
			f.write(data)

		return ret


def find_packages():
	for dirpath, dirnames, filenames in os.walk('pym'):
		if '__init__.py' in filenames:
			yield os.path.relpath(dirpath, 'pym')


setup(
		name = 'portage',
		version = '2.2.12',
		author = 'Gentoo Portage Development Team',
		author_email = 'dev-portage@gentoo.org',
		url = 'https://wiki.gentoo.org/wiki/Project:Portage',

		package_dir = {'': 'pym'},
		packages = list(find_packages()),
		scripts = [],

		cmdclass = {
			'install': x_install,
			'install_lib': x_install_lib,
		},

		classifiers = [
			'Development Status :: 5 - Production/Stable',
			'Environment :: Console',
			'Intended Audience :: System Administrators',
			'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
			'Operating System :: POSIX',
			'Programming Language :: Python',
			'Topic :: System :: Installation/Setup'
		]
)
