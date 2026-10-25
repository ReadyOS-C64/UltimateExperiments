# All isolated outputs stay under this owned probe directory.
CA65 ?= ca65
LD65 ?= ld65
PYTHON ?= python3
OUT=probes/empty_seq/build
NAMES=state channel chunk status directory commands save
OBJECTS=$(addprefix $(OUT)/fileio-,$(addsuffix .o,$(NAMES)))
.PHONY: all test
all: $(OUT)/empty-seq.prg
$(OUT):
	mkdir -p $@
$(OUT)/fileio-%.o: src/fileio/%.s src/fileio/api.inc src/fileio/internal.inc src/fileio/save.inc | $(OUT)
	$(CA65) -g -I src -o $@ $<
$(OUT)/%.o: probes/empty_seq/%.s | $(OUT)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
$(OUT)/empty-seq.prg: $(OBJECTS) $(OUT)/reader.o $(OUT)/native.o probes/empty_seq/probe.cfg
	$(LD65) -C probes/empty_seq/probe.cfg -o $@ -m $(OUT)/empty-seq.map -Ln $(OUT)/empty-seq.lbl $(OBJECTS) $(OUT)/reader.o $(OUT)/native.o
test: all
	$(PYTHON) tests/test_empty_seq.py
