DOS64_ZIG ?= $(firstword $(wildcard ../../zeropage-tooling/bin/zig) $(shell command -v zig 2>/dev/null))
DOS64_CA65 ?= ca65
DOS64_LD65 ?= ld65
DOS64_PYTHON ?= python3

.DEFAULT_GOAL := all

ASM_SOURCES := src/boot.s src/cpu_state.s src/reu.s src/address.s src/memory.s src/cpu.s src/fetch.s src/alu.s src/operands.s src/stack.s src/strings.s src/shifts.s src/control.s src/math.s src/indirect.s src/range.s src/disk.s src/bios.s src/ports.s src/video.s src/adjust.s src/aux_bios.s src/clock.s src/keyboard.s src/uci.s src/host_clock.s src/files.s src/render_text.s src/overlays.s src/image_import.s src/host_input.s src/cold.s src/elapsed.s src/native_text_display.s src/native_text_fonts.s src/native_runtime.s src/native_timer.s src/virtual_irq.s src/virtual_pit.s src/render_graphics.s src/hd_cache.s src/hd_bios.s src/hd_extension_load.s src/hd_cold.s src/uci_diagnostic.s
OBJECTS := $(patsubst src/%.s,build/%.o,$(ASM_SOURCES))
OBJECTS := $(filter-out build/host_clock.o build/elapsed.o build/uci.o,$(OBJECTS)) build/owned-host_clock.o build/owned-elapsed.o build/native-uci.o
OBJECTS := $(patsubst build/reu.o,build/native-reu.o,$(OBJECTS))
build/native-reu.o: src/reu.s include/reu.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_NATIVE_REU_OBSERVER=1 -I include -o $@ $<
build/native-uci.o: src/uci.s include/uci.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_NATIVE_UCI_DIAGNOSTIC=1 -D DOS64_NATIVE_REU_OBSERVER=1 -I include -o $@ $<
build/owned-host_clock.o: src/host_clock.s include/host_clock.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_OWNED_CLOCK=1 -I include -o $@ $<
build/owned-elapsed.o: src/elapsed.s include/elapsed.inc include/host_clock.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_OWNED_CLOCK=1 -I include -o $@ $<
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
build/native_runtime.o: include/image_import.inc include/host_clock.inc include/host_input.inc include/render_graphics.inc Makefile
build/native_timer.o: include/host_clock.inc Makefile
build/virtual_pit.o: include/host_clock.inc Makefile
build/render_graphics.o: include/render_graphics.inc Makefile
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

build/unit-%.o: src/%.s include/abi.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_UNIT_COLD=1 -I include -o $@ $<

build/fixtures.o: tests/fixtures/foundation.s include/abi.inc Makefile
	@mkdir -p build
	$(DOS64_CA65) -g -D DOS64_UNIT_COLD=1 -I include -o $@ $<

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
	$(DOS64_PYTHON) build_support/overlay_package.py --resident-prg build/dos64-resident.prg --files build/dos64-resident.prg.files.bin --render build/dos64-resident.prg.render.bin --input build/dos64-resident.prg.input.bin --pit build/dos64-resident.prg.pit.bin --gfx build/dos64-resident.prg.gfx.bin --hd build/dos64-resident.prg.hd.bin --shadow build/dos64-resident.prg.hdb.bin --import-code build/dos64-resident.prg.import.bin --labels build/dos64.labels --output-prg $@ --output-assets build/dos64-overlay-startup.bin --manifest build/dos64-overlay-package.json

build/dos64-tests.prg: $(OBJECTS) build/fixtures.o build/unit-reu_probe.o build/unit-cache_probe.o build/unit-reu_snapshot.o build/unit-range_probe.o build/unit-range_snapshot.o cfg/dos64-runtime.cfg build_support/overlay_package.py Makefile
	$(DOS64_LD65) -C cfg/dos64-runtime.cfg -o build/dos64-tests-resident.prg -m build/dos64-tests.map -Ln build/dos64-tests.labels $(OBJECTS) build/fixtures.o build/unit-reu_probe.o build/unit-cache_probe.o build/unit-reu_snapshot.o build/unit-range_probe.o build/unit-range_snapshot.o
	$(DOS64_PYTHON) build_support/overlay_package.py --resident-prg build/dos64-tests-resident.prg --files build/dos64-tests-resident.prg.files.bin --render build/dos64-tests-resident.prg.render.bin --input build/dos64-tests-resident.prg.input.bin --pit build/dos64-tests-resident.prg.pit.bin --gfx build/dos64-tests-resident.prg.gfx.bin --hd build/dos64-tests-resident.prg.hd.bin --shadow build/dos64-tests-resident.prg.hdb.bin --import-code build/dos64-tests-resident.prg.import.bin --labels build/dos64-tests.labels --output-prg $@ --output-assets build/dos64-tests-overlay-startup.bin --manifest build/dos64-tests-overlay-package.json

build/dos64-tests.bin: build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/raw_payload.py $< $@

verify-memory: build/dos64.prg build/dos64-tests.prg
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64.map build/dos64.labels --overlay-files build/dos64-resident.prg.files.bin --overlay-render build/dos64-resident.prg.render.bin --overlay-input build/dos64-resident.prg.input.bin --overlay-pit build/dos64-resident.prg.pit.bin --overlay-gfx build/dos64-resident.prg.gfx.bin --overlay-hd build/dos64-resident.prg.hd.bin --shadow build/dos64-resident.prg.hdb.bin --import-code build/dos64-resident.prg.import.bin
	$(DOS64_PYTHON) build_support/verify_memory.py build/dos64-tests.map build/dos64-tests.labels --overlay-files build/dos64-tests-resident.prg.files.bin --overlay-render build/dos64-tests-resident.prg.render.bin --overlay-input build/dos64-tests-resident.prg.input.bin --overlay-pit build/dos64-tests-resident.prg.pit.bin --overlay-gfx build/dos64-tests-resident.prg.gfx.bin --overlay-hd build/dos64-tests-resident.prg.hd.bin --shadow build/dos64-tests-resident.prg.hdb.bin --import-code build/dos64-tests-resident.prg.import.bin

manifest: build/dos64.prg build/dos64-tests.prg verify-memory
	$(DOS64_PYTHON) build_support/hd_identity_plan.py
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

.PHONY: test-native-runtime
test-native-runtime: build
	$(DOS64_ZIG) build native-runtime --summary all

.PHONY: test-native-dos
test-native-dos: build
	$(DOS64_ZIG) build native-dos --summary all

.PHONY: test-timer-graphics
test-timer-graphics: build
	$(DOS64_ZIG) build irq-pit timer-startup future-layout unit-layout native-cga --summary all

# Frozen exact converter is a separate actual-assembly oracle, opt-in only.
build/virtual_pit_reference.o: tests/fixtures/virtual_pit_reference.s Makefile
	$(DOS64_CA65) -g -I include -o $@ $<

build/dos64-reference.prg: $(OBJECTS) build/virtual_pit_reference.o build/fixtures.o build/unit-reu_probe.o build/unit-cache_probe.o build/unit-reu_snapshot.o build/unit-range_probe.o build/unit-range_snapshot.o cfg/dos64-runtime.cfg Makefile
	$(DOS64_LD65) -C cfg/dos64-runtime.cfg -o build/dos64-reference-resident.prg -m build/dos64-reference.map -Ln build/dos64-reference.labels $(filter-out build/virtual_pit.o,$(OBJECTS)) build/virtual_pit_reference.o build/fixtures.o build/unit-reu_probe.o build/unit-cache_probe.o build/unit-reu_snapshot.o build/unit-range_probe.o build/unit-range_snapshot.o
	$(DOS64_PYTHON) build_support/overlay_package.py --resident-prg build/dos64-reference-resident.prg --files build/dos64-reference-resident.prg.files.bin --render build/dos64-reference-resident.prg.render.bin --input build/dos64-reference-resident.prg.input.bin --pit build/dos64-reference-resident.prg.pit.bin --gfx build/dos64-reference-resident.prg.gfx.bin --hd build/dos64-reference-resident.prg.hd.bin --shadow build/dos64-reference-resident.prg.hdb.bin --import-code build/dos64-reference-resident.prg.import.bin --labels build/dos64-reference.labels --output-prg $@ --output-assets build/dos64-reference-overlay-startup.bin --manifest build/dos64-reference-overlay-package.json

.PHONY: test-timer-threshold
test-timer-threshold: build build/dos64-reference.prg
	$(DOS64_ZIG) build threshold-differential --summary all

.PHONY: test-native-builtins test-native-mode
test-native-builtins: build
	$(DOS64_ZIG) build native-builtins --summary all
	$(DOS64_PYTHON) build_support/verify_native_workflows.py build "reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img"
	$(DOS64_PYTHON) tests/host/verify_native_workflows_test.py
test-native-mode: build
	$(DOS64_ZIG) build native-mode --summary all

# Explicit development backend; excluded from all/build/test and default delta.
.PHONY: native-file-recovery test-native-file-recovery test-native-file-recovery-peddle check-native-file-recovery-test-build
native-file-recovery:
	$(DOS64_PYTHON) build_support/build_native_file_recovery.py --ca65 "$(DOS64_CA65)" --ld65 "$(DOS64_LD65)"

test-native-file-recovery: native-file-recovery
	$(DOS64_PYTHON) -m unittest discover -s tests/native_file_recovery -p test_host.py -v

test-native-file-recovery-peddle: native-file-recovery
	$(DOS64_ZIG) build native-file-recovery --summary all

check-native-file-recovery-test-build: native-file-recovery
	$(DOS64_ZIG) build native-file-recovery-compile --summary all

build/hd_cache.o: include/hd_cache.inc include/files.inc
build/hd_bios.o: include/hd_cache.inc include/files.inc include/range.inc
build/hd_cold.o: include/files.inc

.PHONY: test-hd
test-hd: build
	$(DOS64_ZIG) build hd-fixtures hd-backend hd-bios hd-cold --summary all

include build_support/iec_standalone.mk

include build_support/floppy_export.mk

.PHONY: test-reu-observer
test-reu-observer:
	$(DOS64_PYTHON) build_support/test_reu_observer.py --output build/reu-observer-regression
