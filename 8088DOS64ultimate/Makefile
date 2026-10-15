DOS64_ZIG ?= $(firstword $(wildcard ../../zeropage-tooling/bin/zig) $(shell command -v zig 2>/dev/null))
DOS64_CA65 ?= ca65
DOS64_LD65 ?= ld65
DOS64_PYTHON ?= python3

.DEFAULT_GOAL := all

ASM_SOURCES := src/boot.s src/cpu_state.s src/reu.s src/address.s src/memory.s src/cpu.s src/fetch.s src/alu.s src/operands.s src/stack.s src/strings.s src/shifts.s src/control.s src/math.s src/indirect.s src/range.s src/disk.s src/bios.s src/ports.s src/video.s src/adjust.s src/aux_bios.s src/clock.s src/keyboard.s src/uci.s src/host_clock.s src/files.s src/render_text.s src/overlays.s src/image_import.s src/host_input.s src/cold.s src/elapsed.s src/native_text_display.s src/native_text_fonts.s
OBJECTS := $(patsubst src/%.s,build/%.o,$(ASM_SOURCES))
build/alu.o: include/parity.inc Makefile
build/range.o: include/range.inc Makefile
build/disk.o: include/disk.inc include/range.inc Makefile
build/bios.o: include/bios.inc include/video.inc Makefile
build/ports.o: include/ports.inc Makefile
build/video.o: include/video.inc Makefile
build/clock.o: include/clock.inc Makefile
build/keyboard.o: include/keyboard.inc Makefile
build/uci.o: include/uci.inc Makefile
build/host_clock.o: include/host_clock.inc Makefile
build/files.o: include/files.inc include/uci.inc Makefile
build/render_text.o: include/render_text.inc Makefile
build/overlays.o: include/overlays.inc include/reu.inc Makefile
build/image_import.o: include/image_import.inc include/files.inc include/uci.inc include/overlays.inc include/reu.inc Makefile
build/boot.o: include/overlays.inc Makefile
build/host_input.o: include/host_input.inc Makefile
build/cold.o: include/overlays.inc include/bios.inc include/image_import.inc Makefile
build/elapsed.o: include/elapsed.inc include/host_clock.inc Makefile
build/native_text_display.o: include/native_text_display.inc Makefile
build/native_text_fonts.o: assets/native-text/cp437-narrow4x8.bin assets/native-text/cp437-unscii8.bin Makefile
build/aux_bios.o: include/aux_bios.inc Makefile
build/range_probe.o: include/range.inc Makefile
build/host_clock_probe.o: include/host_clock.inc Makefile

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

# This native calibration fixture has its own short contiguous layout and
# scripted VIC test lane. It is deliberately excluded from ASM_SOURCES.
build/dos64-clock-probe.prg: build/host_clock_probe_boot.o build/host_clock_probe.o build/host_clock.o cfg/dos64-clock-probe.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64-clock-probe.cfg -o $@ -m build/dos64-clock-probe.map -Ln build/dos64-clock-probe.labels build/host_clock_probe_boot.o build/host_clock_probe.o build/host_clock.o

.PHONY: clock-probe test-clock-probe
clock-probe: build/dos64-clock-probe.prg

test-clock-probe: clock-probe
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -p test_clock_probe_verify.py -v
	$(DOS64_ZIG) build clock-probe --summary all

.PHONY: range-probe test-range-vice profile-cpu test-dos-boot
range-probe: build/dos64-range-probe.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-range-probe.map build/dos64-range-probe.labels
	$(DOS64_PYTHON) build_support/vice_probe.py --kind range --prepare

test-range-vice: range-probe
	$(DOS64_PYTHON) build_support/vice_probe.py --kind range

test-dos-boot: build
	$(DOS64_ZIG) build dos-boot --summary all

.PHONY: test-image-import
test-image-import: build
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -p test_image_import_contract.py -v
	$(DOS64_ZIG) build image-import --summary all

.PHONY: test-native-text
test-native-text: build
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -p test_native_text_assets.py -v
	$(DOS64_ZIG) build native-text --summary all

.PHONY: test-overlays
test-overlays: build
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -p test_overlay_package.py -v
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -p test_overlay_memory_contract.py -v
	$(DOS64_ZIG) build overlays --summary all

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

build/dos64.prg: $(OBJECTS) cfg/dos64-runtime.cfg build_support/overlay_package.py Makefile
	$(DOS64_LD65) -C cfg/dos64-runtime.cfg -o build/dos64-resident.prg -m build/dos64.map -Ln build/dos64.labels $(OBJECTS)
	$(DOS64_PYTHON) build_support/overlay_package.py --resident-prg build/dos64-resident.prg --files build/dos64-resident.prg.files.bin --render build/dos64-resident.prg.render.bin --input build/dos64-resident.prg.input.bin --import-code build/dos64-resident.prg.import.bin --labels build/dos64.labels --output-prg $@ --output-assets build/dos64-overlay-startup.bin --manifest build/dos64-overlay-package.json

build/dos64-tests.prg: $(OBJECTS) build/fixtures.o build/reu_probe.o build/cache_probe.o build/reu_snapshot.o build/range_probe.o build/range_snapshot.o cfg/dos64-runtime.cfg build_support/overlay_package.py Makefile
	$(DOS64_LD65) -C cfg/dos64-runtime.cfg -o build/dos64-tests-resident.prg -m build/dos64-tests.map -Ln build/dos64-tests.labels $(OBJECTS) build/fixtures.o build/reu_probe.o build/cache_probe.o build/reu_snapshot.o build/range_probe.o build/range_snapshot.o
	$(DOS64_PYTHON) build_support/overlay_package.py --resident-prg build/dos64-tests-resident.prg --files build/dos64-tests-resident.prg.files.bin --render build/dos64-tests-resident.prg.render.bin --input build/dos64-tests-resident.prg.input.bin --import-code build/dos64-tests-resident.prg.import.bin --labels build/dos64-tests.labels --output-prg $@ --output-assets build/dos64-tests-overlay-startup.bin --manifest build/dos64-tests-overlay-package.json

build/dos64-tests.bin: build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/raw_payload.py $< $@

verify-memory: build/dos64.prg build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64.map build/dos64.labels --overlay-files build/dos64-resident.prg.files.bin --overlay-render build/dos64-resident.prg.render.bin --overlay-input build/dos64-resident.prg.input.bin --import-code build/dos64-resident.prg.import.bin
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-tests.map build/dos64-tests.labels --overlay-files build/dos64-tests-resident.prg.files.bin --overlay-render build/dos64-tests-resident.prg.render.bin --overlay-input build/dos64-tests-resident.prg.input.bin --import-code build/dos64-tests-resident.prg.import.bin

manifest: build/dos64.prg build/dos64-tests.prg verify-memory
	$(DOS64_PYTHON) build_support/manifest.py --zig "$(DOS64_ZIG)" --ca65 "$(DOS64_CA65)" --ld65 "$(DOS64_LD65)"

test: build hardware-helpers range-probe
	$(DOS64_PYTHON) -m unittest discover -s tests/tooling -v
	$(DOS64_ZIG) build test --summary all
	# Capture helpers after all test prerequisites have finished rebuilding.
	$(MAKE) manifest

.PHONY: test-cpu-corpus
test-cpu-corpus: build hardware-helpers
	$(DOS64_ZIG) build test -Dcpu-corpus=true --summary all
	$(MAKE) manifest

.PHONY: test-reference
test-reference:
	$(DOS64_PYTHON) build_support/reference_boot.py

clean:
	rm -rf build .zig-cache zig-out
