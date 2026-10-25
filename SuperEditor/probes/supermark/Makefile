ROOT := ../..
OUT := $(ROOT)/build/supermark
CA65 ?= ca65
LD65 ?= ld65
OBJECTS := $(OUT)/block.o $(OUT)/inline.o $(OUT)/lexer.o
.PHONY: all test
all: $(OUT)/probe.bin
$(OUT):
	mkdir -p $@
$(OUT)/%.o: $(ROOT)/src/supermark/%.s $(ROOT)/src/supermark/api.inc | $(OUT)
	$(CA65) -I $(ROOT)/src -g -o $@ $<
$(OUT)/probe.bin: $(OBJECTS) probe.cfg
	$(LD65) -C probe.cfg -o $@ -m $(OUT)/probe.map -Ln $(OUT)/probe.lbl $(OBJECTS)
test: all
	python3 $(ROOT)/tests/test_supermark.py
