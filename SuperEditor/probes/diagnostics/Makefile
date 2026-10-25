# Isolated emitted-service fixture;never writes shared editor objects/reports.
CA65 ?= ca65
LD65 ?= ld65
PYTHON ?= python3
BASE=reu/provider reu/dma object/state object/validate object/allocate object/resize object/copy document/state document/init document/import document/cache document/read document/lease hot/state overlay/crc
DIAG=state snapshot context scan cancel
OBJECTS=$(addprefix build/diagnostics/,$(addsuffix .o,$(BASE))) $(addprefix build/diagnostics/diagnostics/,$(addsuffix .o,$(DIAG))) build/diagnostics/probe.o
.PHONY:all test
all: build/diagnostics/provider.bin
build/diagnostics/diagnostics/cancel.o: src/diagnostics/cancel.s src/diagnostics/api.inc
	mkdir -p $(@D)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
build/diagnostics/diagnostics/%.o: src/diagnostics/%.s src/diagnostics/api.inc src/diagnostics/internal.inc
	mkdir -p $(@D)
	sed 's/\.segment "CODE"/.segment "DIAG_CODE"/' $< > $(@:.o=.s)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $(@:.o=.s)
build/diagnostics/%.o: src/%.s
	mkdir -p $(@D)
	$(CA65) -g -I src -o $@ $<
build/diagnostics/probe.o: probes/diagnostics/probe.s
	$(CA65) -g -I src -o $@ $<
build/diagnostics/provider.bin: $(OBJECTS) probes/diagnostics/probe.cfg
	$(LD65) -C probes/diagnostics/probe.cfg -o $@ -m build/diagnostics/provider.map -Ln build/diagnostics/provider.lbl $(OBJECTS)
test: all
	$(PYTHON) tests/test_diagnostics.py
