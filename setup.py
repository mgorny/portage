#!/usr/bin/env python
#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from distutils.core import setup
from distutils.command.install import install
from distutils.command.install_data import install_data
from distutils.command.install_lib import install_lib

import codecs, os, os.path, re

sysconfdir = '/etc'
logrotatedir = os.path.join(sysconfdir, 'logrotate.d')
portage_datadir = '/usr/share/portage'
portage_confdir = os.path.join(portage_datadir, 'config')
portage_setsdir = os.path.join(portage_confdir, 'sets')

extra_install_options = [
	('portage-base=', 'b', "Portage install base"),
	('portage-datadir=', None, 'Install directory for data files'),
	('sysconfdir=', None, 'System configuration path'),
]

extra_install_option_mapping = [
	('portage_base', 'portage_base'),
	('portage_datadir', 'portage_datadir'),
	('sysconfdir', 'sysconfdir'),
]


class x_install(install):
	""" install command with extra Portage paths """

	user_options = install.user_options + extra_install_options

	def initialize_options(self):
		install.initialize_options(self)
		self.portage_base = '/usr/lib/portage'
		self.portage_datadir = '/usr/share/portage'
		self.sysconfdir = sysconfdir


class x_install_data(install_data):
	""" install_data with customized path support """

	user_options = install_data.user_options + extra_install_options

	def initialize_options(self):
		install_data.initialize_options(self)
		self.portage_base = None
		self.portage_datadir = None
		self.sysconfdir = None

	def finalize_options(self):
		install_data.finalize_options(self)
		self.set_undefined_options('install', *extra_install_option_mapping)

		self.logrotatedir = os.path.join(self.sysconfdir, 'logrotate.d')
		self.portage_confdir = os.path.join(self.portage_datadir, 'config')
		self.portage_setsdir = os.path.join(self.portage_confdir, 'sets')

		# substitute default paths in data_files with user-provided paths
		dir_mapping = {
			sysconfdir: self.sysconfdir,
			logrotatedir: self.logrotatedir,
			portage_confdir: self.portage_confdir,
			portage_setsdir: self.portage_setsdir,
		}
		for f in self.data_files:
			f[0] = dir_mapping[f[0]]


class x_install_lib(install_lib):
	""" install_lib command with Portage path substitution """

	user_options = install_lib.user_options + extra_install_options

	def initialize_options(self):
		install_lib.initialize_options(self)
		self.portage_base = None
		self.portage_datadir = None
		self.sysconfdir = None

	def finalize_options(self):
		install_lib.finalize_options(self)
		self.set_undefined_options('install', *extra_install_option_mapping)

		self.portage_confdir = os.path.join(self.portage_datadir, 'config')

	def install(self):
		ret = install_lib.install(self)

		base_re = re.compile(r'(^PORTAGE_BASE_PATH.*=) .*$', re.MULTILINE)
		global_config_re = re.compile(r'(^GLOBAL_CONFIG_PATH.*=) .*$', re.MULTILINE)

		constfile = os.path.join(self.install_dir, 'portage', 'const.py')
		print('Rewriting %s' % constfile)
		with codecs.open(constfile, 'r', 'utf-8') as f:
			data = f.read()
		data = base_re.sub('\\1 %s' % repr(self.portage_base), data)
		data = global_config_re.sub('\\1 %s' % repr(self.portage_confdir), data)
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

		data_files = [
			[sysconfdir, ['cnf/etc-update.conf', 'cnf/dispatch-conf.conf']],
			[logrotatedir, ['cnf/logrotate.d/elog-save-summary']],
			[portage_confdir, [
				'cnf/make.conf.example', 'cnf/make.globals', 'cnf/repos.conf']],
			[portage_setsdir, ['cnf/sets/portage.conf']],
		],

		cmdclass = {
			'install': x_install,
			'install_data': x_install_data,
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
