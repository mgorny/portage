#!/usr/bin/env python
#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from distutils.core import setup, Command
from distutils.command.build_scripts import build_scripts
from distutils.command.clean import clean
from distutils.command.install import install
from distutils.command.install_data import install_data
from distutils.command.install_lib import install_lib
from distutils.command.install_scripts import install_scripts
from distutils.dir_util import remove_tree
from distutils.util import change_root

import codecs, collections, glob, os, os.path, re, subprocess

# TODO:
# - 'test' command,
# - smarter rebuilds of docs w/ 'install_docbook' and 'install_epydoc'.

package_name = 'portage'
package_version = '2.2.12'
package_homepage = 'https://wiki.gentoo.org/wiki/Project:Portage'

bindir = '/usr/bin'
docdir = '/usr/share/doc/%s-%s' % (package_name, package_version)
htmldir = os.path.join(docdir, 'html')
mandir = '/usr/share/man'
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
	('docdir=', None, "Documentation install directory"),
	('htmldir=', None, "HTML documentation install directory"),
	('mandir=', None, "Manpage root install directory"),
	('portage-base=', 'b', "Portage install base"),
	('portage-bindir=', None, "Install directory for Portage internal-use executables"),
	('portage-datadir=', None, 'Install directory for data files'),
	('sbindir=', None, "Install directory for superuser-intended executables"),
	('sysconfdir=', None, 'System configuration path'),
]

extra_install_option_mapping = [
	('docdir', 'docdir'),
	('mandir', 'mandir'),
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


class docbook(Command):
	""" Build docs using docbook. """

	user_options = [
		('doc-formats=', None, 'Documentation formats to build (all xmlto formats for docbook are allowed, comma-separated'),
	]

	def initialize_options(self):
		self.doc_formats = 'xhtml,xhtml-nochunks'

	def finalize_options(self):
		self.doc_formats = self.doc_formats.replace(',', ' ').split()

	def run(self):
		with open('doc/fragment/date', 'w'):
			pass

		for f in self.doc_formats:
			print('Building docs in %s format...' % f)
			subprocess.check_call(['xmlto', '-o', 'doc',
				'-m', 'doc/custom.xsl', f, 'doc/portage.docbook'])


class epydoc(Command):
	""" Build API docs using epydoc. """

	user_options = [
	]

	def initialize_options(self):
		self.build_lib = None

	def finalize_options(self):
		self.set_undefined_options('build_py', ('build_lib', 'build_lib'))

	def run(self):
		self.run_command('build_py')

		print('Building API documentation...')

		process_env = os.environ.copy()
		pythonpath = self.build_lib
		try:
			pythonpath += ':' + process_env['PYTHONPATH']
		except KeyError:
			pass
		process_env['PYTHONPATH'] = pythonpath

		subprocess.check_call(['epydoc', '-o', 'epydoc',
			'--name', package_name,
			'--url', package_homepage,
			'-qq', '--no-frames', '--show-imports',
			'--exclude', 'portage.tests',
			'_emerge', 'portage', 'repoman'],
			env = process_env)
		os.remove('epydoc/api-objects.txt')


class install_docbook(install_data):
	""" install_data for docbook docs """

	user_options = install_data.user_options + [
		('htmldir=', None, "HTML documentation install directory"),
	]

	def initialize_options(self):
		install_data.initialize_options(self)
		self.htmldir = None

	def finalize_options(self):
		self.set_undefined_options('install', ('htmldir', 'htmldir'))
		install_data.finalize_options(self)

	def run(self):
		if not os.path.exists('doc/portage.html'):
			self.run_command('docbook')
		self.data_files = [
			(self.htmldir, glob.glob('doc/*.html')),
		]
		install_data.run(self)


class install_epydoc(install_data):
	""" install_data for epydoc docs """

	user_options = install_data.user_options + [
		('htmldir=', None, "HTML documentation install directory"),
	]

	def initialize_options(self):
		install_data.initialize_options(self)
		self.htmldir = None

	def finalize_options(self):
		self.set_undefined_options('install', ('htmldir', 'htmldir'))
		install_data.finalize_options(self)

	def run(self):
		if not os.path.exists('epydoc/index.html'):
			self.run_command('epydoc')
		self.data_files = [
			(os.path.join(self.htmldir, 'api'), glob.glob('epydoc/*')),
		]
		install_data.run(self)


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


class x_clean(clean):
	""" clean extended for doc cleaning """

	def run(self):
		clean.run(self)

		if self.all:
			def get_doc_outfiles():
				for dirpath, dirnames, filenames in os.walk('doc'):
					for f in filenames:
						if f.endswith('.docbook') or f == 'custom.xsl':
							pass
						else:
							yield os.path.join(dirpath, f)

					# do not recurse
					break


			for f in get_doc_outfiles():
				print('removing %s' % repr(f))
				os.remove(f)

			if os.path.isdir('epydoc'):
				remove_tree('epydoc')


class x_install(install):
	""" install command with extra Portage paths """

	user_options = install.user_options + extra_install_options

	def initialize_options(self):
		install.initialize_options(self)
		self.bindir = bindir
		self.docdir = docdir
		self.htmldir = htmldir
		self.mandir = mandir
		self.portage_base = portage_base
		self.portage_bindir = portage_bindir
		self.portage_datadir = portage_datadir
		self.sbindir = sbindir
		self.sysconfdir = sysconfdir

	def finalize_options(self):
		install.finalize_options(self)
		# prepend root to bindirs
		if self.root is not None:
			self.bindir = change_root(self.root, self.bindir)
			self.sbindir = change_root(self.root, self.sbindir)
			self.portage_bindir = change_root(self.root, self.portage_bindir)


class x_install_data(install_data):
	""" install_data with customized path support """

	user_options = install_data.user_options + extra_install_options

	def initialize_options(self):
		install_data.initialize_options(self)
		self.docdir = None
		self.mandir = None
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
			docdir: self.docdir,
		}
		for f in self.data_files:
			if f[0].startswith(mandir):
				f[0] = self.mandir + f[0][len(mandir):]
			else:
				f[0] = dir_mapping[f[0]]


class x_install_lib(install_lib):
	""" install_lib command with Portage path substitution """

	user_options = install_lib.user_options + extra_install_options

	def initialize_options(self):
		install_lib.initialize_options(self)
		self.docdir = None
		self.mandir = None
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


def get_manpages():
	linguas = os.environ.get('LINGUAS')
	if linguas is not None:
		linguas = linguas.split()

	for dirpath, dirnames, filenames in os.walk('man'):
		groups = collections.defaultdict(list)
		for f in filenames:
			fn, suffix = f.rsplit('.', 1)
			groups[suffix].append(os.path.join(dirpath, f))

		topdir = dirpath[len('man/'):]
		if not topdir or linguas is None or topdir in linguas:
			for g, mans in groups.items():
				yield [os.path.join(mandir, topdir, 'man%s' % g), mans]

setup(
		name = package_name,
		version = package_version,
		author = 'Gentoo Portage Development Team',
		author_email = 'dev-portage@gentoo.org',
		url = package_homepage,

		package_dir = {'': 'pym'},
		packages = list(find_packages()),
		# something to cheat build & install commands
		scripts = list(find_scripts()),

		data_files = list(get_manpages()) + [
			[sysconfdir, ['cnf/etc-update.conf', 'cnf/dispatch-conf.conf']],
			[logrotatedir, ['cnf/logrotate.d/elog-save-summary']],
			[portage_confdir, [
				'cnf/make.conf.example', 'cnf/make.globals', 'cnf/repos.conf']],
			[portage_setsdir, ['cnf/sets/portage.conf']],
			[docdir, ['ChangeLog', 'NEWS', 'RELEASE-NOTES']],
		],

		cmdclass = {
			'build_scripts': x_build_scripts,
			'build_scripts_bin': x_build_scripts_bin,
			'build_scripts_portagebin': x_build_scripts_portagebin,
			'build_scripts_sbin': x_build_scripts_sbin,
			'clean': x_clean,
			'docbook': docbook,
			'epydoc': epydoc,
			'install': x_install,
			'install_data': x_install_data,
			'install_docbook': install_docbook,
			'install_epydoc': install_epydoc,
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
