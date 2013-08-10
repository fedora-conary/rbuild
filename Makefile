#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


all: all-subdirs default-all

all-subdirs:
	for d in $(MAKEALLSUBDIRS); do make -C $$d DIR=$$d || exit 1; done

export TOPDIR = $(shell pwd)

SUBDIRS=commands rbuild plugins pylint
MAKEALLSUBDIRS=commands rbuild plugins

extra_files = \
	Make.rules 		\
	Makefile		\
	Make.defs		\
	NEWS			\
	README			\
	EULA_rBuild.txt		\
	LICENSE


.PHONY: clean dist install subdirs html

subdirs: default-subdirs

install: install-subdirs

clean: clean-subdirs default-clean

doc: html

html:
	ln -fs plugins/ rbuild_plugins
	scripts/generate_docs.sh
	rm -f rbuild_plugins

dist:
	if ! grep "^Changes in $(VERSION)" NEWS > /dev/null 2>&1; then \
		echo "no NEWS entry"; \
		exit 1; \
	fi
	$(MAKE) forcedist

show-version:
	@echo $(VERSION)

archive:
	@rm -rf /tmp/rbuild-$(VERSION) /tmp/rbuild$(VERSION)-tmp
	@mkdir -p /tmp/rbuild-$(VERSION)-tmp
	@git archive --format tar $(VERSION) | (cd /tmp/rbuild-$(VERSION)-tmp/ ; tar x )
	@mv /tmp/rbuild-$(VERSION)-tmp/ /tmp/rbuild-$(VERSION)/
	@dir=$$PWD; cd /tmp; tar -c --bzip2 -f $$dir/rbuild-$(VERSION).tar.bz2 rbuild-$(VERSION)
	@rm -rf /tmp/pesign-$(VERSION)
	@echo "The archive is in rbuild-$(VERSION).tar.bz2"

forcedist: archive

forcetag:
	git tag --force $(VERSION) refs/heads/master

tag:
	git tag $(VERSION) refs/heads/master

clean: clean-subdirs default-clean

include Make.rules
include Make.defs
 
# vim: set sts=8 sw=8 noexpandtab :
