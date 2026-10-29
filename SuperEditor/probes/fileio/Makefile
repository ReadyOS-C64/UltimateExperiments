# Invoke from SuperEditor: make -f probes/fileio/Makefile test
CA65 ?= ca65
LD65 ?= ld65
PYTHON ?= python3
FIO_NAMES = state channel chunk status directory commands save
FIO_OBJECTS = $(addprefix build/fileio/,$(addsuffix .o,$(FIO_NAMES)))
.PHONY: all test
all: build/fileio/provider.bin
build/fileio:
	mkdir -p $@
build/fileio/%.o: src/fileio/%.s src/fileio/api.inc src/fileio/internal.inc src/fileio/save.inc | build/fileio
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
build/fileio/probe.o: probes/fileio/probe.s src/fileio/api.inc | build/fileio
	$(CA65) -g -I src -o $@ $<
build/fileio/provider.bin: $(FIO_OBJECTS) build/fileio/probe.o probes/fileio/probe.cfg
	$(LD65) -C probes/fileio/probe.cfg -o $@ -m build/fileio/provider.map -Ln build/fileio/provider.lbl $(FIO_OBJECTS) build/fileio/probe.o
build/fileio/native.o: probes/fileio/native.s src/fileio/api.inc | build/fileio
	$(CA65) -g -I src -o $@ $<
build/fileio/native.prg: $(FIO_OBJECTS) build/fileio/native.o probes/fileio/native.cfg
	$(LD65) -C probes/fileio/native.cfg -o $@ -m build/fileio/native.map -Ln build/fileio/native.lbl $(FIO_OBJECTS) build/fileio/native.o
test: build/fileio/provider.bin
	$(PYTHON) tests/test_fileio.py
	$(PYTHON) tests/test_fileio_save.py
