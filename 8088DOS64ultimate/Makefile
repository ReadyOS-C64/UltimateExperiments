DOS64_ZIG ?= $(firstword $(wildcard ../../zeropage-tooling/bin/zig) $(shell command -v zig 2>/dev/null))
DOS64_CA65 ?= ca65
DOS64_LD65 ?= ld65
DOS64_PYTHON ?= python3

ASM_SOURCES := src/boot.s src/cpu_state.s src/reu.s src/address.s src/memory.s
OBJECTS := $(patsubst src/%.s,build/%.o,$(ASM_SOURCES))

.PHONY: all build test verify-memory manifest clean
all: build
build: build/dos64.prg build/dos64-tests.prg build/dos64-tests.bin verify-memory manifest

build/%.o: src/%.s include/abi.inc include/reu.inc include/memory.inc
	@mkdir -p build
	$(DOS64_CA65) -g -I include -o $@ $<

build/fixtures.o: tests/fixtures/foundation.s include/abi.inc
	@mkdir -p build
	$(DOS64_CA65) -g -I include -o $@ $<

build/probe_boot.o: src/boot.s include/abi.inc
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_PROBE=1 -I include -o $@ $<

build/cache_probe_boot.o: src/boot.s include/abi.inc
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_CACHE_PROBE=1 -I include -o $@ $<

build/backup_boot.o: src/boot.s include/abi.inc
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_SNAPSHOT=1 -I include -o $@ $<

build/restore_boot.o: src/boot.s include/abi.inc
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_SNAPSHOT=1 -D DOS64_RESTORE=1 -I include -o $@ $<

build/dos64-backup.prg: build/backup_boot.o build/cpu_state.o build/reu.o build/reu_snapshot.o cfg/dos64.cfg
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-backup.map -Ln build/dos64-backup.labels build/backup_boot.o build/cpu_state.o build/reu.o build/reu_snapshot.o

build/dos64-restore.prg: build/restore_boot.o build/cpu_state.o build/reu.o build/reu_snapshot.o cfg/dos64.cfg
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-restore.map -Ln build/dos64-restore.labels build/restore_boot.o build/cpu_state.o build/reu.o build/reu_snapshot.o

.PHONY: hardware-helpers
hardware-helpers: build/dos64-backup.prg build/dos64-restore.prg cache-probe
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-backup.map build/dos64-backup.labels
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-restore.map build/dos64-restore.labels

build/dos64-cache-probe.prg: build/cache_probe_boot.o build/cpu_state.o build/reu.o build/address.o build/memory.o build/cache_probe.o cfg/dos64.cfg
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-cache-probe.map -Ln build/dos64-cache-probe.labels build/cache_probe_boot.o build/cpu_state.o build/reu.o build/address.o build/memory.o build/cache_probe.o

build/dos64-reu-probe.prg: build/probe_boot.o build/cpu_state.o build/reu.o build/reu_probe.o cfg/dos64.cfg
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-reu-probe.map -Ln build/dos64-reu-probe.labels build/probe_boot.o build/cpu_state.o build/reu.o build/reu_probe.o

.PHONY: probe test-vice
probe: build/dos64-reu-probe.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-reu-probe.map build/dos64-reu-probe.labels
	$(DOS64_PYTHON) build_support/vice_probe.py --prepare

test-vice: probe
	$(DOS64_PYTHON) build_support/vice_probe.py

.PHONY: cache-probe test-cache-vice
cache-probe: build/dos64-cache-probe.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-cache-probe.map build/dos64-cache-probe.labels
	$(DOS64_PYTHON) build_support/vice_probe.py --kind cache --prepare

test-cache-vice: cache-probe
	$(DOS64_PYTHON) build_support/vice_probe.py --kind cache

build/dos64.prg: $(OBJECTS) cfg/dos64.cfg
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64.map -Ln build/dos64.labels $(OBJECTS)

build/dos64-tests.prg: $(OBJECTS) build/fixtures.o build/reu_probe.o build/cache_probe.o build/reu_snapshot.o cfg/dos64.cfg
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-tests.map -Ln build/dos64-tests.labels $(OBJECTS) build/fixtures.o build/reu_probe.o build/cache_probe.o build/reu_snapshot.o

build/dos64-tests.bin: build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/raw_payload.py $< $@

verify-memory: build/dos64.prg build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64.map build/dos64.labels
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-tests.map build/dos64-tests.labels

manifest: build/dos64.prg build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/manifest.py --zig "$(DOS64_ZIG)" --ca65 "$(DOS64_CA65)" --ld65 "$(DOS64_LD65)"

test: build hardware-helpers
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -v
	$(DOS64_ZIG) build test --summary all

.PHONY: test-reference
test-reference:
	$(DOS64_PYTHON) build_support/reference_boot.py

clean:
	rm -rf build .zig-cache zig-out
