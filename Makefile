SHELL = /bin/sh
PN ?= portage
PF ?= portage
HOMEPAGE ?= http://www.gentoo.org/proj/en/portage/index.xml
PWD ?= $(shell pwd)
S ?= $(PWD)
WORKDIR ?= $(PWD)
DESTDIR = $(PWD)/image/
srcdir = $(S)
prefix = /usr
sysconfdir = /etc
exec_prefix = $(prefix)
bindir = $(exec_prefix)/bin
sbindir = $(exec_prefix)/sbin
libdir = $(exec_prefix)/lib
datarootdir = $(prefix)/share
datadir = $(datarootdir)
mandir = $(datarootdir)/man
docdir = $(datarootdir)/doc/$(PF)
htmldir = $(docdir)/html
portage_datadir = $(datarootdir)/$(PN)
portage_base = $(libdir)/$(PN)
INSMODE = 0644
EXEMODE = 0755
DIRMODE = 0755

ifdef PYTHONPATH
	PYTHONPATH := $(srcdir)/pym:$(PYTHONPATH)
else
	PYTHONPATH := $(srcdir)/pym
endif

all: docbook epydoc

docbook:
	set -e; \
	cd "$(srcdir)"; \
	./setup.py docbook

epydoc:
	set -e; \
	cd "$(srcdir)"; \
	./setup.py epydoc

test:
	set -e; \
	cd "$(srcdir)"; \
	./setup.py test

install:
	set -e; \
	\
	# Use setup.py to install Python modules. \
	cd "$(srcdir)"; \
	./setup.py build; \
	./setup.py install --compile -O2 --root="$(DESTDIR)" \
		--bindir="$(bindir)" \
		--docdir="$(docdir)" \
		--mandir="$(mandir)" \
		--portage-base="$(portage_base)" \
		--portage-bindir="$(portage_base)/bin" \
		--portage-datadir="$(portage_datadir)" \
		--sbindir="$(sbindir)" \
		--sysconfdir="$(sysconfdir)"; \
	\
	if [ -f "$(srcdir)/doc/portage.html" ] ; then \
		./setup.py install --root="$(DESTDIR)" \
			install_docbook --htmldir="$(htmldir)"; \
	fi; \
	\
	if [ -d "$(WORKDIR)/epydoc" ] ; then \
		./setup.py install --root="$(DESTDIR)" \
			install_epydoc --htmldir="$(htmldir)"; \
	fi; \

clean:
	set -e; \
	\
	cd "$(srcdir)"; \
	./setup.py clean --all

.PHONY: all clean docbook epydoc install test
