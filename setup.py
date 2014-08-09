#!/usr/bin/env python
#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from distutils.core import setup
from distutils.command.build_scripts import build_scripts
from distutils.command.install import install
from distutils.command.install_data import install_data
from distutils.command.install_lib import install_lib
from distutils.command.install_scripts import install_scripts
from distutils.util import change_root

import codecs, collections, os, os.path, re

bindir = '/usr/bin'
sbindir = '/usr/sbin'
sysconfdir = '/etc'
logrotatedir = os.path.join(sysconfdir, 'logrotate.d')
portage_base = '/usr/lib/portage'
portage_bindir = os.path.join(portage_base, 'bin')
portage_datadir = '/usr/share/portage'
portage_confdir = os.path.join(portage_datadir, 'config')
portage_setsdir = os.path.join(portage_confdir, 'sets')

extra_install_options = [
	('bindir=', None, "Install directory for main executables"),
	('portage-base=', 'b', "Portage install base"),
	('portage-bindir=', None, "Install directory for Portage internal-use executables"),
	('portage-datadir=', None, 'Install directory for data files'),
	('sbindir=', None, "Install directory for superuser-intended executables"),
	('sysconfdir=', None, 'System configuration path'),
]

extra_install_option_mapping = [
	('portage_base', 'portage_base'),
	('portage_datadir', 'portage_datadir'),
	('sysconfdir', 'sysconfdir'),
]

x_scripts = {
	'bin': [
		'bin/ebuild', 'bin/egencache', 'bin/emerge', 'bin/emerge-webrsync',
		'bin/emirrordist', 'bin/portageq', 'bin/quickpkg', 'bin/repoman'
	],
	'sbin': [
		'bin/archive-conf', 'bin/dispatch-conf', 'bin/emaint', 'bin/env-update',
		'bin/etc-update', 'bin/fixpackages', 'bin/regenworld'
	],
}


class x_build_scripts_custom(build_scripts):
	def finalize_options(self):
		build_scripts.finalize_options(self)
		self.build_dir = os.path.join(self.build_dir, self.dir_name)
		self.scripts = x_scripts[self.dir_name]


class x_build_scripts_bin(x_build_scripts_custom):
	dir_name = 'bin'


class x_build_scripts_sbin(x_build_scripts_custom):
	dir_name = 'sbin'


class x_build_scripts_portagebin(build_scripts):
	def finalize_options(self):
		build_scripts.finalize_options(self)
		self.build_dir = os.path.join(self.build_dir, 'portage')

	def run(self):
		# group scripts by subdirectory
		split_scripts = collections.defaultdict(list)
		for f in self.scripts:
			for other_files in x_scripts.values():
				if f in other_files:
					break
			else:
				dir_name = os.path.dirname(f[len('bin/'):])
				split_scripts[dir_name].append(f)

		base_dir = self.build_dir
		base_scripts = self.scripts
		for d, files in split_scripts.items():
			self.build_dir = os.path.join(base_dir, d)
			self.scripts = files
			self.copy_scripts()

		# restore previous values
		self.build_dir = base_dir
		self.scripts = base_scripts


class x_build_scripts(build_scripts):
	def initialize_option(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		self.run_command('build_scripts_bin')
		self.run_command('build_scripts_portagebin')
		self.run_command('build_scripts_sbin')


class x_install(install):
	""" install command with extra Portage paths """

	user_options = install.user_options + extra_install_options

	def initialize_options(self):
		install.initialize_options(self)
		self.bindir = bindir
		self.portage_base = portage_base
		self.portage_bindir = portage_bindir
		self.portage_datadir = portage_datadir
		self.sbindir = sbindir
		self.sysconfdir = sysconfdir

	def finalize_options(self):
		install.finalize_options(self)
		# prepend root to bindirs
		self.bindir = change_root(self.root, self.bindir)
		self.sbindir = change_root(self.root, self.sbindir)
		self.portage_bindir = change_root(self.root, self.portage_bindir)

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


class x_install_scripts_custom(install_scripts):
	def finalize_options(self):
		self.set_undefined_options('install', (self.var_name, 'install_dir'))
		install_scripts.finalize_options(self)
		self.build_dir = os.path.join(self.build_dir, self.dir_name)


class x_install_scripts_bin(x_install_scripts_custom):
	dir_name = 'bin'
	var_name = 'bindir'


class x_install_scripts_sbin(x_install_scripts_custom):
	dir_name = 'sbin'
	var_name = 'sbindir'


class x_install_scripts_portagebin(x_install_scripts_custom):
	dir_name = 'portage'
	var_name = 'portage_bindir'


class x_install_scripts(install_scripts):
	def initialize_option(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		self.run_command('install_scripts_bin')
		self.run_command('install_scripts_portagebin')
		self.run_command('install_scripts_sbin')


def find_packages():
	for dirpath, dirnames, filenames in os.walk('pym'):
		if '__init__.py' in filenames:
			yield os.path.relpath(dirpath, 'pym')


def find_scripts():
	for dirpath, dirnames, filenames in os.walk('bin'):
		for f in filenames:
			yield os.path.join(dirpath, f)


setup(
		name = 'portage',
		version = '2.2.12',
		author = 'Gentoo Portage Development Team',
		author_email = 'dev-portage@gentoo.org',
		url = 'https://wiki.gentoo.org/wiki/Project:Portage',

		package_dir = {'': 'pym'},
		packages = list(find_packages()),
		# something to cheat build & install commands
		scripts = list(find_scripts()),

		data_files = [
			[sysconfdir, ['cnf/etc-update.conf', 'cnf/dispatch-conf.conf']],
			[logrotatedir, ['cnf/logrotate.d/elog-save-summary']],
			[portage_confdir, [
				'cnf/make.conf.example', 'cnf/make.globals', 'cnf/repos.conf']],
			[portage_setsdir, ['cnf/sets/portage.conf']],
		],

		cmdclass = {
			'build_scripts': x_build_scripts,
			'build_scripts_bin': x_build_scripts_bin,
			'build_scripts_portagebin': x_build_scripts_portagebin,
			'build_scripts_sbin': x_build_scripts_sbin,
			'install': x_install,
			'install_data': x_install_data,
			'install_lib': x_install_lib,
			'install_scripts': x_install_scripts,
			'install_scripts_bin': x_install_scripts_bin,
			'install_scripts_portagebin': x_install_scripts_portagebin,
			'install_scripts_sbin': x_install_scripts_sbin,
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
