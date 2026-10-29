ROOT := ../..
OUT := $(ROOT)/build/crc_variants
CA65 ?= ca65
LD65 ?= ld65
.PHONY: all test
all: $(OUT)/probe.bin
$(OUT):
	mkdir -p $@
$(OUT)/tables.inc: $(ROOT)/tools/crc_variants_tables.py | $(OUT)
	python3 $< $@
$(OUT)/variants.o: variants.s $(OUT)/tables.inc | $(OUT)
	$(CA65) -I $(OUT) -g -o $@ $<
$(OUT)/probe.bin: $(OUT)/variants.o probe.cfg
	$(LD65) -C probe.cfg -o $@ -m $(OUT)/probe.map -Ln $(OUT)/probe.lbl $<
test: all
	python3 $(ROOT)/tests/test_crc_variants.py
