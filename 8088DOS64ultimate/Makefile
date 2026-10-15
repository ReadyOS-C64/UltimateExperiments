DOS64_ZIG ?= $(firstword $(wildcard ../../zeropage-tooling/bin/zig) $(shell command -v zig 2>/dev/null))
DOS64_CA65 ?= ca65
DOS64_LD65 ?= ld65
DOS64_PYTHON ?= python3

.DEFAULT_GOAL := all

ASM_SOURCES := src/boot.s src/cpu_state.s src/reu.s src/address.s src/memory.s src/cpu.s src/fetch.s src/alu.s src/operands.s src/stack.s src/strings.s src/shifts.s src/control.s src/math.s src/indirect.s src/range.s src/disk.s src/bios.s src/ports.s
OBJECTS := $(patsubst src/%.s,build/%.o,$(ASM_SOURCES))
build/alu.o: include/parity.inc Makefile
build/range.o: include/range.inc Makefile
build/disk.o: include/disk.inc include/range.inc Makefile
build/bios.o: include/bios.inc Makefile
build/ports.o: include/ports.inc Makefile
build/range_probe.o: include/range.inc Makefile

.PHONY: all build test verify-memory manifest clean
all: build
build: build/dos64.prg build/dos64-tests.prg build/dos64-tests.bin verify-memory manifest

build/%.o: src/%.s include/abi.inc include/reu.inc include/memory.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -I include -o $@ $<

build/fixtures.o: tests/fixtures/foundation.s include/abi.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -I include -o $@ $<

build/probe_boot.o: src/boot.s include/abi.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_PROBE=1 -I include -o $@ $<

build/range_snapshot_boot.o: src/range_snapshot.s include/abi.inc include/reu.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_RANGE_SNAPSHOT=1 -I include -o $@ $<

build/dos64-range-backup.prg: build/backup_boot.o build/cpu_state.o build/reu.o build/range_snapshot_boot.o cfg/dos64.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-range-backup.map -Ln build/dos64-range-backup.labels build/backup_boot.o build/cpu_state.o build/reu.o build/range_snapshot_boot.o

build/dos64-range-restore.prg: build/restore_boot.o build/cpu_state.o build/reu.o build/range_snapshot_boot.o cfg/dos64.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-range-restore.map -Ln build/dos64-range-restore.labels build/restore_boot.o build/cpu_state.o build/reu.o build/range_snapshot_boot.o

.PHONY: range-hardware-helpers
range-hardware-helpers: build/dos64-range-backup.prg build/dos64-range-restore.prg range-probe
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-range-backup.map build/dos64-range-backup.labels
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-range-restore.map build/dos64-range-restore.labels

build/range_probe_boot.o: src/boot.s include/abi.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_RANGE_PROBE=1 -I include -o $@ $<

build/cache_probe_boot.o: src/boot.s include/abi.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_CACHE_PROBE=1 -I include -o $@ $<

build/backup_boot.o: src/boot.s include/abi.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_SNAPSHOT=1 -I include -o $@ $<

build/restore_boot.o: src/boot.s include/abi.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_SNAPSHOT=1 -D DOS64_RESTORE=1 -I include -o $@ $<

build/dos64-backup.prg: build/backup_boot.o build/cpu_state.o build/reu.o build/reu_snapshot.o cfg/dos64.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-backup.map -Ln build/dos64-backup.labels build/backup_boot.o build/cpu_state.o build/reu.o build/reu_snapshot.o

build/dos64-restore.prg: build/restore_boot.o build/cpu_state.o build/reu.o build/reu_snapshot.o cfg/dos64.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-restore.map -Ln build/dos64-restore.labels build/restore_boot.o build/cpu_state.o build/reu.o build/reu_snapshot.o

.PHONY: hardware-helpers
hardware-helpers: build/dos64-backup.prg build/dos64-restore.prg cache-probe
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-backup.map build/dos64-backup.labels
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-restore.map build/dos64-restore.labels

build/dos64-range-probe.prg: build/range_probe_boot.o build/cpu_state.o build/reu.o build/address.o build/memory.o build/range.o build/range_probe.o cfg/dos64.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-range-probe.map -Ln build/dos64-range-probe.labels build/range_probe_boot.o build/cpu_state.o build/reu.o build/address.o build/memory.o build/range.o build/range_probe.o

.PHONY: range-probe test-range-vice profile-cpu
range-probe: build/dos64-range-probe.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-range-probe.map build/dos64-range-probe.labels
	$(DOS64_PYTHON) build_support/vice_probe.py --kind range --prepare

test-range-vice: range-probe
	$(DOS64_PYTHON) build_support/vice_probe.py --kind range

profile-cpu: build
	$(DOS64_ZIG) build profile-cpu --summary all

build/dos64-cache-probe.prg: build/cache_probe_boot.o build/cpu_state.o build/reu.o build/address.o build/memory.o build/cache_probe.o cfg/dos64.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-cache-probe.map -Ln build/dos64-cache-probe.labels build/cache_probe_boot.o build/cpu_state.o build/reu.o build/address.o build/memory.o build/cache_probe.o

build/dos64-reu-probe.prg: build/probe_boot.o build/cpu_state.o build/reu.o build/reu_probe.o cfg/dos64.cfg Makefile
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

build/dos64.prg: $(OBJECTS) cfg/dos64.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64.map -Ln build/dos64.labels $(OBJECTS)

build/dos64-tests.prg: $(OBJECTS) build/fixtures.o build/reu_probe.o build/cache_probe.o build/reu_snapshot.o build/range_probe.o build/range_snapshot.o cfg/dos64.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64.cfg -o $@ -m build/dos64-tests.map -Ln build/dos64-tests.labels $(OBJECTS) build/fixtures.o build/reu_probe.o build/cache_probe.o build/reu_snapshot.o build/range_probe.o build/range_snapshot.o

build/dos64-tests.bin: build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/raw_payload.py $< $@

verify-memory: build/dos64.prg build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64.map build/dos64.labels
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-tests.map build/dos64-tests.labels

manifest: build/dos64.prg build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/manifest.py --zig "$(DOS64_ZIG)" --ca65 "$(DOS64_CA65)" --ld65 "$(DOS64_LD65)"

test: build hardware-helpers range-probe
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -v
	$(DOS64_ZIG) build test --summary all

.PHONY: test-cpu-corpus
test-cpu-corpus: build hardware-helpers
	$(DOS64_ZIG) build test -Dcpu-corpus=true --summary all

.PHONY: test-reference
test-reference:
	$(DOS64_PYTHON) build_support/reference_boot.py

clean:
	rm -rf build .zig-cache zig-out
