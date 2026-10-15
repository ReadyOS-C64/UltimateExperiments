DOS64_ZIG ?= $(firstword $(wildcard ../../zeropage-tooling/bin/zig) $(shell command -v zig 2>/dev/null))
DOS64_CA65 ?= ca65
DOS64_LD65 ?= ld65
DOS64_PYTHON ?= python3

ASM_SOURCES := src/boot.s src/cpu_state.s
OBJECTS := $(patsubst src/%.s,build/%.o,$(ASM_SOURCES))

.PHONY: all build test verify-memory manifest clean
all: build
build: build/dos64.prg build/dos64-tests.prg build/dos64-tests.bin verify-memory manifest

build/%.o: src/%.s include/abi.inc
	@mkdir -p build
	$(DOS64_CA65) -g -I include -o $@ $<

build/fixtures.o: tests/fixtures/foundation.s include/abi.inc
	@mkdir -p build
	$(DOS64_CA65) -g -I include -o $@ $<

build/dos64.prg: $(OBJECTS) cfg/dos64.cfg
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64.map -Ln build/dos64.labels $(OBJECTS)

build/dos64-tests.prg: $(OBJECTS) build/fixtures.o cfg/dos64.cfg
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-tests.map -Ln build/dos64-tests.labels $(OBJECTS) build/fixtures.o

build/dos64-tests.bin: build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/raw_payload.py $< $@

verify-memory: build/dos64.prg build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64.map build/dos64.labels
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-tests.map build/dos64-tests.labels

manifest: build/dos64.prg build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/manifest.py --zig "$(DOS64_ZIG)" --ca65 "$(DOS64_CA65)" --ld65 "$(DOS64_LD65)"

test: build
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -v
	$(DOS64_ZIG) build test --summary all

.PHONY: test-reference
test-reference:
	$(DOS64_PYTHON) build_support/reference_boot.py

clean:
	rm -rf build .zig-cache zig-out
