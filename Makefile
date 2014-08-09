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
EPYDOC_OPTS = -qqqqq --no-frames --show-imports
INSMODE = 0644
EXEMODE = 0755
DIRMODE = 0755
LINGUAS ?= $(shell cd "$(srcdir)/man" && find -mindepth 1 -type d)

ifdef PYTHONPATH
	PYTHONPATH := $(srcdir)/pym:$(PYTHONPATH)
else
	PYTHONPATH := $(srcdir)/pym
endif

all: docbook epydoc

docbook:
	set -e; \
	touch "$(srcdir)/doc/fragment/date"; \
	$(MAKE) -C "$(srcdir)/doc" xhtml xhtml-nochunks

epydoc:
	set -e; \
	env PYTHONPATH="$(PYTHONPATH)" epydoc \
		-o "$(WORKDIR)/epydoc" \
		--name $(PN) \
		--url "$(HOMEPAGE)" \
		$(EPYDOC_OPTS) \
		$$(cd "$(srcdir)" && find pym -name '*.py' | sed \
		-e s:/__init__.py$$:: \
		-e s:\.py$$:: \
		-e s:^pym/:: \
		-e s:/:.:g \
		| sort); \
	rm -f "$(WORKDIR)/epydoc/api-objects.txt"; \

test:
	set -e; \
	"$(srcdir)/pym/portage/tests/runTests.py"; \

install:
	set -e; \
	\
	# Use setup.py to install Python modules. \
	cd "$(srcdir)"; \
	./setup.py build; \
	./setup.py install --compile -O2 --root="$(DESTDIR)" \
		--bindir="$(bindir)" \
		--docdir="$(docdir)" \
		--portage-base="$(portage_base)" \
		--portage-bindir="$(portage_base)/bin" \
		--portage-datadir="$(portage_datadir)" \
		--sbindir="$(sbindir)" \
		--sysconfdir="$(sysconfdir)"; \
	\
	for x in "" $(LINGUAS); do \
		for y in 1 5 ; do \
			if [ -d "$(srcdir)/man/$$x" ]; then \
				cd "$(srcdir)/man/$$x"; \
				files=$$(echo *.$$y); \
				if [ -z "$$files" ] || [ "$$files" = "*.$$y" ]; then \
					continue; \
				fi; \
				install -d -m$(DIRMODE) "$(DESTDIR)$(mandir)/$$x/man$$y"; \
				install -m$(INSMODE) *.$$y "$(DESTDIR)$(mandir)/$$x/man$$y"; \
			fi; \
		done; \
	done; \
	\
	if [ -f "$(srcdir)/doc/portage.html" ] ; then \
		install -d -m$(DIRMODE) "$(DESTDIR)$(htmldir)"; \
		cd "$(srcdir)/doc"; \
		install -m$(INSMODE) *.html "$(DESTDIR)$(htmldir)"; \
	fi; \
	\
	if [ -d "$(WORKDIR)/epydoc" ] ; then \
		install -d -m$(DIRMODE) "$(DESTDIR)$(htmldir)"; \
		cp -pPR "$(WORKDIR)/epydoc" \
			"$(DESTDIR)$(htmldir)/api"; \
		cd "$(DESTDIR)$(htmldir)/api"; \
		find . -type d | xargs chmod $(DIRMODE); \
		find . -type f | xargs chmod $(INSMODE); \
	fi; \

clean:
	set -e; \
	$(MAKE) -C "$(srcdir)/doc" clean; \
	rm -rf "$(WORKDIR)/epydoc"; \

.PHONY: all clean docbook epydoc install test
