MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:

# global configurations

# echo target and recipe
DEBUG_ECHO_RECIPES ?=
DEBUG_ECHO_RECIPE := $(if $(DEBUG_ECHO_RECIPES),,@)
DEBUG_ECHO_TARGETS ?=
DEBUG_ECHO_TARGET = $(if $(DEBUG_ECHO_TARGETS),$(info Executing '$@'),)

# enable verbose output
VERBOSE ?=
VERBOSE_FLAG := $(if $(VERBOSE),-v,)
ZIP_SLIENT_FLAG := $(if $(VERBOSE),,-q)

# python environment
python ?= python3

# output directory
distdir ?= dist

# some useful functions
filter_contains = $(foreach v,$(2),$(if $(findstring $(1),$(v)),$(v),))
filter_not_contains = $(foreach v,$(2),$(if $(findstring $(1),$(v)),,$(v)))
all_files = $(shell find $(1) -type f ! -name '\.*') # ignore all files starts with dot

scriptsdir := scripts
resdir := res

r1distdir := $(distdir)/r1
r1docdistdir := $(distdir)/r1/doc
r2distdir := $(distdir)/r2
r2docdistdir := $(distdir)/r2/doc
r3distdir := $(distdir)/r3
r3docdistdir := $(distdir)/r3/doc

# files needed to build csf
r1deps := $(addprefix $(distdir)/,base.json $(addprefix r1/,missions.json names.json data.json))
r2deps := $(addprefix $(distdir)/,r1/ra2md.json $(addprefix r2/,missions.json names.json from_prev.json data.json))
r3deps := $(addprefix $(distdir)/,r2/ra2md.json $(addprefix r3/,missions.json names.json from_prev.json data.json))

# all files need to copy
res := $(subst $(resdir),$(distdir),$(call all_files,$(resdir)))
r1res := $(call filter_contains,r1/,$(res))
r2res := $(call filter_contains,r2/,$(res))
r3res := $(call filter_contains,r3/,$(res))

# all doc files need to copy
r1docres := $(call filter_contains,doc/,$(r1res))
r2docres := $(call filter_contains,doc/,$(r2res))
r3docres := $(call filter_contains,doc/,$(r3res))

# docs need to build
r1doc := $(addprefix $(r1docdistdir)/,guide.html summary.html) $(r1docres)
r2doc := $(addprefix $(r2docdistdir)/,guide.html summary.html units.html) $(r2docres)
r3doc := $(addprefix $(r3docdistdir)/,guide.html summary.html units.html) $(r3docres)

.PHONY: all
all: r1 r2 r3

.PHONY: r1 r2 r3
r1 r2 r3: %: $(distdir)/%.zip

.PHONY: doc
doc: $(r1doc) $(r2doc) $(r3doc)

.PHONY: csf
csf: $(r1distdir)/ra2md.csf $(r2distdir)/ra2md.csf $(r3distdir)/ra2md.csf

.PHONY: debug
debug: $(r1distdir)/ra2md_debug.json $(r2distdir)/ra2md_debug.json $(r3distdir)/ra2md_debug.json

# create all dirs
$(distdir) $(r1distdir) $(r2distdir) $(r3distdir):
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)mkdir -p "$@"

# create dirs for file copy
$(sort $(dir $(res))):
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)mkdir -p "$@"

.SECONDEXPANSION:

# copy all files from res
$(res): $(distdir)/%: $(resdir)/% | $$(dir $$@)
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)cp "$<" "$@"

# build zip
$(addprefix $(distdir)/,$(addsuffix .zip,r1 r2 r3)): $(distdir)/%.zip: $$($$(*)res) $$($$(*)doc) $(distdir)/%/ra2md.csf
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)pushd $(distdir)/$* > /dev/null; zip $(ZIP_SLIENT_FLAG) -T -r ../$*.zip $(subst $(distdir)/$*/,,$^) -x '**/.*'; popd > /dev/null

# build doc (md -> html)
$(distdir)/%.html: doc/$$(subst doc/,,$$*).md $(scriptsdir)/doc-template.html | $$(@D)
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/makedoc.py $< $@ -t $(scriptsdir)/doc-template.html

# special case: r3 guide
$(distdir)/r3/doc/guide.html: doc/r3/guide.md $(scriptsdir)/doc-script-template.html | $$(@D)
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/makedoc.py $< $@ -t $(scriptsdir)/doc-script-template.html

# build csf from json
$(addprefix $(distdir)/,$(addsuffix /ra2md.csf,r1 r2 r3)): %.csf: %.json
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/csftool.py -e -i $< -o $@

# build final json
# apply 2nd to 2nd-to-last word and extend the last word
$(distdir)/%/ra2md.json: $$($$(*)deps) | $(distdir)/%
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/apply.py $< $@ $(addprefix --apply ,$(filter-out $< $(lastword $^),$^)) --extend $(lastword $^) $(VERBOSE_FLAG)

$(distdir)/%/ra2md_debug.json: $$($$(*)deps) | $(distdir)/%
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/apply.py $< $@ $(addprefix --apply ,$(filter-out $< $(lastword $^),$^)) --extend $(lastword $^) -k $(VERBOSE_FLAG)

# build each json
$(distdir)/%/missions.json: src/%/missions.txt | $(distdir)/%
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/makemissions.py $< $@ -p $* $(VERBOSE_FLAG)

$(distdir)/%/names.json: src/%/names.json | $(distdir)/%
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/maketranslations.py $< $@

$(distdir)/%/data.json: src/%/data.json | $(distdir)/%
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/maketranslations.py $< $@

$(distdir)/base.json: jsons/original.json | $(distdir)
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)$(python) $(scriptsdir)/makebase.py $< $@

$(distdir)/%/from_prev.json: src/%/from_prev.json | $(distdir)/%
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)cp "$<" "$@"

# prevent files from deleted in the end
.SECONDARY:

.PHONY: clean
clean:
	$(DEBUG_ECHO_TARGET)
	$(DEBUG_ECHO_RECIPE)rm -rf $(distdir)
