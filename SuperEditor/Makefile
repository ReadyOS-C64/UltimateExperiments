PYTHON ?= python3
CA65 ?= ca65
LD65 ?= ld65
C1541 ?= c1541

.PHONY: all disk check cpu smoke clean
all: disk

build:
	mkdir -p build

COMMON_SRC = src/reu.s src/tui/charset.s src/tui/petscii.s src/tui/text40.s src/tui/hex.s src/input/keyboard_irq.s src/input/events.s
COMMON_OBJ = $(patsubst src/%.s,build/%.o,$(COMMON_SRC))
PROBE_UI_OBJ = build/tui/cell40.o build/tui/box40.o
MEMORY_OBJ = build/reu/provider.o build/reu/dma.o

build/%.o: src/%.s src/platform.inc src/tui/theme.inc src/overlay/format.inc | build
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<

build/supereditor.o: src/main.s src/platform.inc src/boot_ui.s | build
	$(CA65) -g -I src -o $@ -l build/supereditor.lst src/main.s

build/supereditor.prg: build/supereditor.o $(COMMON_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/supereditor.map -Ln build/supereditor.lbl --dbgfile build/supereditor.dbg build/supereditor.o $(COMMON_OBJ)
	$(PYTHON) tools/check_build.py

assets/fonts/generated/manifest.json: tools/fonts.py assets/fonts/narrow3x7.txt
	$(PYTHON) tools/fonts.py

build/probe_display.o: src/probe_display.s src/probe_panel.s assets/fonts/generated/manifest.json
	mkdir -p build
	$(CA65) -g -I src -o $@ -l build/probe_display.lst $<

build/probe_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D DISPLAY_PROBE=1 -I src -o $@ $<

build/display-probe.prg: build/probe_main.o build/probe_display.o $(COMMON_OBJ) $(PROBE_UI_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/display-probe.map -Ln build/display-probe.lbl --dbgfile build/display-probe.dbg build/probe_main.o build/probe_display.o $(COMMON_OBJ) $(PROBE_UI_OBJ)
	$(PYTHON) tools/check_build.py --stem display-probe

build/memory_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D MEMORY_PROBE=1 -I src -o $@ $<

build/memory-probe.prg: build/memory_main.o build/probe_memory.o $(COMMON_OBJ) $(MEMORY_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/memory-probe.map -Ln build/memory-probe.lbl --dbgfile build/memory-probe.dbg build/memory_main.o build/probe_memory.o $(COMMON_OBJ) $(MEMORY_OBJ)
	$(PYTHON) tools/check_build.py --stem memory-probe

.PHONY: probes
probes: build/display-probe.prg build/memory-probe.prg

.PHONY: display-test
display-test: disk
	$(PYTHON) tests/test_display.py

.PHONY: keyboard-test
keyboard-test: disk
	$(PYTHON) tests/test_keyboard.py

build/supereditor.d81: package-force tools/package.py tools/overlays.py build/supereditor.prg build/display-probe.prg build/memory-probe.prg
	$(PACKAGE_GUARD) --package --c1541 "$(C1541)"

disk: build/supereditor.d81

check: disk
	$(PYTHON) tools/check_build.py

cpu: build/supereditor.prg build/display-probe.prg
	$(PYTHON) tests/test_cpu.py

.PHONY: reu-test
reu-test: build/memory-probe.prg
	$(PYTHON) tests/test_reu.py

.PHONY: reu-vice-test
reu-vice-test: disk
	$(PYTHON) tests/test_reu_vice.py

boot-smoke: disk
	$(PYTHON) tools/run_vice.py --suite boot

smoke: editor-vice-test

clean:
	rm -rf build

OVERLAY_OBJ = build/overlay/binding.o build/overlay/crc.o build/overlay/header.o build/overlay/cache.o build/iec/overlay_read.o
build/overlay_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D OVERLAY_PROBE=1 -I src -o $@ $<

build/overlay-probe.prg: build/overlay_main.o build/probe_overlay.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OVERLAY_OBJ) cfg/standalone.cfg tools/bindings.py
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/overlay-probe.map -Ln build/overlay-probe.lbl build/overlay_main.o build/probe_overlay.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OVERLAY_OBJ)
	$(PYTHON) tools/bindings.py --stem overlay-probe
	$(PYTHON) tools/check_build.py --stem overlay-probe

build/overlay-api.inc: build/overlay-probe.prg tools/overlay_api.py
	$(PYTHON) tools/overlay_api.py

OVERLAY_MODULES = probe-rone probe-rtwo probe-cone probe-rnest
$(addprefix build/overlays/,$(addsuffix .o,$(OVERLAY_MODULES))): build/overlays/%.o: src/overlays/%.s build/overlay-api.inc | build
	mkdir -p $(dir $@)
	$(CA65) -g -I build -o $@ $<

build/overlays/probe-r%.bin: build/overlays/probe-r%.o cfg/overlay-r.cfg
	$(LD65) -C cfg/overlay-r.cfg -o $@ $<

build/overlays/probe-c%.bin: build/overlays/probe-c%.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ $<

build/overlays/rone.seo: build/overlays/probe-rone.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 1
build/overlays/rtwo.seo: build/overlays/probe-rtwo.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 2
build/overlays/cone.seo: build/overlays/probe-cone.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 1
build/overlays/rnest.seo: build/overlays/probe-rnest.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 3
OVERLAY_ASSETS = build/overlays/rone.seo build/overlays/rtwo.seo build/overlays/cone.seo build/overlays/rnest.seo

build/supereditor.d81: build/overlay-probe.prg $(OVERLAY_ASSETS)
probes: build/overlay-probe.prg
.PHONY: overlay-test overlay-vice-test
overlay-test: $(OVERLAY_ASSETS)
	$(PYTHON) tests/test_overlay.py
overlay-vice-test: disk
	$(PYTHON) tests/test_overlay_vice.py

OBJECT_OBJ = build/object/state.o build/object/validate.o build/object/allocate.o build/object/resize.o build/object/copy.o
$(OBJECT_OBJ) build/probe_object.o: src/object/api.inc
build/object_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D OBJECT_PROBE=1 -I src -o $@ $<
build/object-probe.prg: build/object_main.o build/probe_object.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/object-probe.map -Ln build/object-probe.lbl build/object_main.o build/probe_object.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ)
	$(PYTHON) tools/check_build.py --stem object-probe
probes: build/object-probe.prg
.PHONY: object-test object-vice-test
object-test: build/object-probe.prg
	$(PYTHON) tests/test_object.py
object-vice-test: disk
	$(PYTHON) tests/test_object_vice.py
build/supereditor.d81: build/object-probe.prg

DOCUMENT_READ_OBJ = build/document/state.o build/document/init.o build/document/import.o build/document/cache.o build/document/read.o build/document/lease.o
DOCUMENT_EDIT_OBJ = build/document/local.o build/document/refs.o build/document/piece.o build/document/walk.o build/document/emit.o build/document/splice.o build/document/splice_build.o
DOCUMENT_OBJ = $(DOCUMENT_READ_OBJ) $(DOCUMENT_EDIT_OBJ)
$(DOCUMENT_OBJ) build/probe_document.o: src/document/api.inc src/object/api.inc src/document/math24.inc src/document/splice.inc
build/document_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D DOCUMENT_PROBE=1 -I src -o $@ $<
build/document-probe.prg: build/document_main.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_READ_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/document-probe.map -Ln build/document-probe.lbl build/document_main.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_READ_OBJ)
	$(PYTHON) tools/check_build.py --stem document-probe
.PHONY: document-test
document-test: build/document-probe.prg
	$(PYTHON) tests/test_document.py

probes: build/document-probe.prg
build/supereditor.d81: build/document-probe.prg
.PHONY: document-vice-test
document-vice-test: disk
	$(PYTHON) tests/test_document_vice.py

.PHONY: splice-test
splice-test: build/splice-probe.prg
	$(PYTHON) tests/test_splice.py

build/probe_splice.o: src/document/api.inc src/document/math24.inc
build/splice_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D SPLICE_PROBE=1 -I src -o $@ $<
build/splice-probe.prg: build/splice_main.o build/probe_splice.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/splice-probe.map -Ln build/splice-probe.lbl build/splice_main.o build/probe_splice.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ)
	$(PYTHON) tools/check_build.py --stem splice-probe
probes: build/splice-probe.prg
build/supereditor.d81: build/splice-probe.prg
.PHONY: splice-vice-test
splice-vice-test: disk
	$(PYTHON) tests/test_splice_vice.py

CLIPBOARD_OBJ = build/clipboard/state.o build/clipboard/copy.o build/clipboard/paste.o
$(CLIPBOARD_OBJ): src/clipboard/api.inc src/object/api.inc src/document/api.inc src/document/math24.inc
.PHONY: clipboard-test
clipboard-test: build/clipboard-probe.prg
	$(PYTHON) tests/test_clipboard.py

HISTORY_CORE_OBJ = build/document/snapshot.o build/document/replay.o
$(HISTORY_CORE_OBJ): src/document/api.inc src/object/api.inc src/document/math24.inc src/document/splice.inc
build/replay-probe.prg: build/splice_main.o build/probe_splice.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) $(HISTORY_CORE_OBJ) $(CLIPBOARD_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/replay-probe.map -Ln build/replay-probe.lbl build/splice_main.o build/probe_splice.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) $(HISTORY_CORE_OBJ) $(CLIPBOARD_OBJ)
	$(PYTHON) tools/check_build.py --stem replay-probe
.PHONY: replay-test
replay-test: build/replay-probe.prg
	$(PYTHON) tests/test_replay.py

build/probe_clipboard.o: src/clipboard/api.inc src/document/api.inc src/object/api.inc src/document/math24.inc
build/clipboard_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D CLIPBOARD_PROBE=1 -I src -o $@ $<
build/clipboard-probe.prg: build/clipboard_main.o build/probe_clipboard.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) $(HISTORY_CORE_OBJ) $(CLIPBOARD_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/clipboard-probe.map -Ln build/clipboard-probe.lbl build/clipboard_main.o build/probe_clipboard.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) $(HISTORY_CORE_OBJ) $(CLIPBOARD_OBJ)
	$(PYTHON) tools/check_build.py --stem clipboard-probe
probes: build/clipboard-probe.prg
build/supereditor.d81: build/clipboard-probe.prg
.PHONY: clipboard-vice-test
clipboard-vice-test: disk
	$(PYTHON) tests/test_clipboard_vice.py

.PHONY: refs-test
refs-test: build/clipboard-probe.prg
	$(PYTHON) tests/test_refs.py

.PHONY: local-test
local-test: build/clipboard-probe.prg
	$(PYTHON) tests/test_local.py

build/probe_local.o: src/document/api.inc src/object/api.inc src/document/math24.inc
build/local_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D LOCAL_PROBE=1 -I src -o $@ $<
build/local-probe.prg: build/local_main.o build/probe_local.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) $(HISTORY_CORE_OBJ) cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/local-probe.map -Ln build/local-probe.lbl build/local_main.o build/probe_local.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) $(HISTORY_CORE_OBJ)
	$(PYTHON) tools/check_build.py --stem local-probe
probes: build/local-probe.prg
build/supereditor.d81: build/local-probe.prg
.PHONY: local-vice-test
local-vice-test: disk
	$(PYTHON) tests/test_local_vice.py

.PHONY: read-some-test
read-some-test: build/clipboard-probe.prg
	$(PYTHON) tests/test_read_some.py

build/document/range.o: src/document/api.inc src/object/api.inc src/document/math24.inc src/document/splice.inc
build/range-probe.prg: build/range_main.o build/probe_range.o build/probe_local.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) $(HISTORY_CORE_OBJ) build/document/range.o cfg/standalone.cfg
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/range-probe.map -Ln build/range-probe.lbl build/range_main.o build/probe_range.o build/probe_local.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) $(HISTORY_CORE_OBJ) build/document/range.o
	$(PYTHON) tools/check_build.py --stem range-probe
.PHONY: range-test
range-test: build/range-probe.prg
	$(PYTHON) tests/test_range.py

build/range_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D LOCAL_PROBE=1 -D RANGE_PROBE=1 -I src -o $@ $<
build/probe_range.o: src/document/api.inc src/object/api.inc
probes: build/range-probe.prg
build/supereditor.d81: build/range-probe.prg
.PHONY: range-vice-test
range-vice-test: disk
	$(PYTHON) tests/test_range_vice.py

.PHONY: bindings-test
bindings-test: $(OVERLAY_ASSETS)
	$(PYTHON) tests/test_bindings.py

HISTORY_OBJ = build/history/state.o build/history/dispatch.o build/history/services.o
$(HISTORY_OBJ): src/history/api.inc src/document/api.inc src/object/api.inc
build/history_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -D HISTORY_PROBE=1 -I src -o $@ $<
build/probe_history.o: src/history/api.inc src/document/api.inc src/object/api.inc
build/history-probe.prg: build/history_main.o build/probe_history.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) build/document/range.o $(HISTORY_OBJ) $(OVERLAY_OBJ) cfg/standalone.cfg tools/bindings.py
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/history-probe.map -Ln build/history-probe.lbl build/history_main.o build/probe_history.o build/probe_document.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) build/document/range.o $(HISTORY_OBJ) $(OVERLAY_OBJ)
	$(PYTHON) tools/bindings.py --stem history-probe
	$(PYTHON) tools/check_build.py --stem history-probe
build/history-api.inc: build/history-probe.prg tools/overlay_api.py
	$(PYTHON) tools/overlay_api.py --report build/history-probe-report.json --output $@ --all-public --symbols object_owner object_banks object_size_lo object_size_mid object_size_hi
build/overlays/history-edit.o build/overlays/history-play.o: build/overlays/history-%.o: src/overlays/history-%.s src/history/api.inc src/history/record.inc src/document/api.inc src/document/math24.inc src/object/api.inc build/history-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/history-%.bin: build/overlays/history-%.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $<
build/overlays/hedit.seo: build/overlays/history-edit.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 4 --resident-report build/history-probe-report.json
build/overlays/hplay.seo: build/overlays/history-play.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 5 --resident-report build/history-probe-report.json
HISTORY_ASSETS = build/overlays/hedit.seo build/overlays/hplay.seo

.PHONY: history-test
history-test: $(HISTORY_ASSETS)
	$(PYTHON) tests/test_history.py

.PHONY: crc-test
crc-test: build/overlay-probe.prg
	$(PYTHON) tests/test_crc.py

build/supereditor.d81: build/history-probe.prg $(HISTORY_ASSETS)
probes: build/history-probe.prg
.PHONY: history-vice-test
history-vice-test: disk
	$(PYTHON) tests/test_history_vice.py

# Isolated editor working-set consumer. Keeps original history fixtures sealed
# to their own resident; each consumer gets distinct command asset bindings.
HOT_OBJ = build/hot/state.o build/hot/dispatch.o
$(HOT_OBJ): src/hot/api.inc src/history/api.inc src/document/api.inc
build/hot_main.o: src/main.s src/boot_ui.s src/platform.inc | build
	$(CA65) -g -I src -o $@ $<
build/hot-probe.prg: build/hot_main.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) build/document/range.o $(HISTORY_OBJ) $(OVERLAY_OBJ) $(HOT_OBJ) cfg/standalone.cfg tools/bindings.py
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/hot-probe.map -Ln build/hot-probe.lbl build/hot_main.o $(COMMON_OBJ) $(MEMORY_OBJ) $(OBJECT_OBJ) $(DOCUMENT_OBJ) build/document/range.o $(HISTORY_OBJ) $(OVERLAY_OBJ) $(HOT_OBJ)
	$(PYTHON) tools/bindings.py --stem hot-probe
	$(PYTHON) tools/check_build.py --stem hot-probe
build/hot-api.inc: build/hot-probe.prg tools/overlay_api.py
	$(PYTHON) tools/overlay_api.py --report build/hot-probe-report.json --output $@ --all-public --symbols object_owner object_banks object_size_lo object_size_mid object_size_hi
build/overlays/hot-window.o: src/overlays/hot-window.s src/hot/api.inc build/hot-api.inc src/document/api.inc src/document/math24.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/wedit.o: src/overlays/history-edit.s src/history/record.inc src/history/api.inc build/hot-api.inc
	$(CA65) -g -D HOT_BINDINGS=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/wplay.o: src/overlays/history-play.s src/history/record.inc src/history/api.inc build/hot-api.inc
	$(CA65) -g -D HOT_BINDINGS=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/hot-window.bin build/overlays/wedit.bin build/overlays/wplay.bin: build/overlays/%.bin: build/overlays/%.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $<
build/overlays/hwin.seo: build/overlays/hot-window.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 6 --resident-report build/hot-probe-report.json
build/overlays/wedit.seo: build/overlays/wedit.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 4 --resident-report build/hot-probe-report.json
build/overlays/wplay.seo: build/overlays/wplay.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 5 --resident-report build/hot-probe-report.json
HOT_ASSETS = build/overlays/hwin.seo build/overlays/wedit.seo build/overlays/wplay.seo
.PHONY: hot-test
hot-test: $(HOT_ASSETS)
	$(PYTHON) tests/test_hot.py

# Actual editor consumer; its warm path has no diagnostic/cold probe dependency.
# Host-only defaults compiler. Runtime settings never rewrite this TOML.
SETTINGS_PYTHON ?= $(if $(wildcard /opt/homebrew/bin/python3),/opt/homebrew/bin/python3,$(PYTHON))
build/editor-settings/editor-font-catalog.bin: build/editor-settings/editor-defaults.bin
	@test -f $@
build/editor-settings/editor-defaults.bin: build/geos-font-catalog/catalog.json config/editor-defaults.toml tools/editor_settings.py tools/presentation_defaults.py src/render/geos/settings.inc assets/fonts/generated/bsw9-widths.bin assets/fonts/generated/native8.bin
	$(SETTINGS_PYTHON) tools/editor_settings.py --out-dir build/editor-settings
build/editor-settings/presentation-defaults.inc: config/editor-defaults.toml tools/presentation_defaults.py tools/editor_settings.py src/render/presentation.inc build/geos-font-catalog/catalog.json assets/fonts/generated/bsw9-widths.bin assets/fonts/generated/native8.bin
	$(SETTINGS_PYTHON) tools/presentation_defaults.py --out-dir build/editor-settings
build/editor/startup.o: build/editor-settings/editor-defaults.bin src/render/geos/settings.inc src/render/presentation.inc build/editor-settings/presentation-defaults.inc

EDITOR_OBJ = build/editor/main.o build/editor/state.o build/editor/startup.o build/editor/commands.o build/view/source.o build/nav/state.o build/nav/dispatch.o build/nav/invalidate.o build/editor_fold/dispatch.o build/geos-resident/dispatch.o build/editor/presentation.o
DIAGNOSTICS_RESIDENT_OBJ = build/diagnostics-editor/state.o build/diagnostics-editor/cancel.o build/diagnostics-editor/dispatch.o
DIAGNOSTICS_OVERLAY_OBJ = build/diagnostics-editor/snapshot.o build/diagnostics-editor/context.o build/diagnostics-editor/scan.o
STYLE_RESIDENT_OBJ = build/style-prod/state.o build/style-prod/source-state.o build/style-prod/block-state.o build/style-prod/inline-state.o build/style-prod/lexer-state.o build/style-prod/lexical-state.o build/style-prod/display-state.o build/style-prod/render-state.o build/style-prod/source-cleanup.o build/style-prod/dispatch.o
GRID_RESIDENT_OBJ = build/grid-prod/cache-state.o
FOLD_RESIDENT_OBJ = build/fold-prod/state.o build/fold-prod/builder-state.o build/editor_fold/state.o build/editor_fold/projection-state.o build/editor_fold/phase-state.o build/editor_fold/emergency.o build/editor_fold/key.o build/editor_fold/motion-state.o build/editor_fold/modal-state.o build/editor_fold/modal.o build/editor_fold/journal-state.o build/editor_fold/summary.o
EDITOR_FILE_RESIDENT_OBJ = build/editor-file-prod/state.o build/editor-file-prod/dialog-state.o build/editor-file-prod/preflight-state.o build/editor-file-prod/dispatch.o build/editor-file-prod/provider-state.o build/editor-file-prod/policy-state.o
FILE_TRANSPORT_OBJ = $(addprefix build/file-transport/,$(addsuffix .o,channel chunk status directory commands)) build/editor-file-prod/transport.o build/editor-file-prod/preflight.o
build/diagnostics-editor/%.o: src/diagnostics/%.s src/diagnostics/api.inc src/diagnostics/internal.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
$(EDITOR_OBJ): src/editor/geometry.inc src/editor/api.inc src/hot/api.inc src/history/api.inc src/document/api.inc
build/editor/main.o build/render/state.o: src/render/api.inc
build/editor/reu.o: src/reu.s | build
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_COLD_STARTUP=1 -I src -o $@ -l $(@:.o=.lst) $<
ENGINE_MODULES = local refs emit splice splice_build
ENGINE_ORIG_OBJ = $(addprefix build/document/,$(addsuffix .o,$(ENGINE_MODULES)))
ENGINE_STATE_OBJ = $(addprefix build/engine-state/,$(addsuffix .o,$(ENGINE_MODULES)))
EDITOR_DOCUMENT_OBJ = $(foreach obj,$(DOCUMENT_OBJ),$(if $(filter $(obj),$(ENGINE_ORIG_OBJ)),$(patsubst build/document/%,build/engine-state/%,$(obj)),$(obj)))
$(ENGINE_ORIG_OBJ): src/document/frames/local.inc src/document/frames/refs.inc src/document/frames/emit.inc src/document/frames/splice.inc src/document/frames/splice_build.inc src/document/frames/range.inc
build/engine-state/%.o: src/document/%.s src/document/frames/%.inc src/document/api.inc src/document/splice.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D ENGINE_STATE_ONLY=1 -I src -o $@ -l $(@:.o=.lst) $<
build/engine/trampoline.o: src/engine/api.inc src/document/api.inc
EDITOR_OBJECT_OBJ = $(patsubst build/object/allocate.o,build/editor/object-allocate.o,$(OBJECT_OBJ))
EDITOR_COMMON_OBJ = $(filter-out build/reu.o,$(COMMON_OBJ)) build/editor/reu.o build/tui/cell40.o
build/editor/clip-copy.o: src/clipboard/copy.s src/clipboard/frames/copy.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D CLIP_COPY_CLEANUP_ONLY=1 -I src -o $@ -l $(@:.o=.lst) $<
build/clipboard/editor_dispatch.o: src/block/api.inc src/clipboard/api.inc
build/clipboard/copy.o: src/clipboard/frames/copy.inc
EDITOR_OVERLAY_OBJ = $(patsubst build/overlay/header.o,build/editor/overlay-header.o,$(patsubst build/overlay/cache.o,build/editor/overlay-cache.o,$(patsubst build/overlay/crc.o,build/editor/crc-half.o,$(OVERLAY_OBJ))))
build/editor/crc-half.o: src/overlay/crc_fast.s
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_HALF_CRC=1 -I src -o $@ -l $(@:.o=.lst) $<
build/editor/overlay-cache.o: src/overlay/cache.s src/overlay/format.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_MANAGED_CODE=1 -D FAST_EDITOR_CRC=1 -D EDITOR_HALF_CRC=1 -D EDITOR_CATALOG_TAIL=1 -D EDITOR_FIXED_ENTRY=1 -D OVL_LIMIT=51 -I src -o $@ -l $(@:.o=.lst) $<
build/editor/overlay-header.o: src/overlay/header.s src/overlay/format.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_CATALOG_TAIL=1 -D EDITOR_FIXED_ENTRY=1 -D OVL_LIMIT=51 -I src -o $@ -l $(@:.o=.lst) $<
build/overlay/crc_fast.o: src/overlay/crc_tables.inc
EDITOR_OVERLAY_OBJ := $(patsubst build/iec/overlay_read.o,build/editor/overlay-read.o,$(EDITOR_OVERLAY_OBJ))
EDITOR_HISTORY_OBJ = $(patsubst build/history/dispatch.o,build/editor/history-dispatch.o,$(HISTORY_OBJ))
EDITOR_HOT_OBJ = $(patsubst build/hot/dispatch.o,build/editor/hot-dispatch.o,$(HOT_OBJ))
build/editor/hot-dispatch.o: src/hot/dispatch.s src/hot/api.inc src/history/api.inc src/document/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_COLD_DISPATCH=1 -D EDITOR_FAST_HOT_FEED=1 -I src -o $@ -l $(@:.o=.lst) $<
# Editor provider initialization is called only during cold startup.
EDITOR_MEMORY_OBJ = build/editor-memory/provider.o build/editor-memory/dma.o
build/editor-memory/provider.o: src/reu/provider.s
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_MANAGED_CODE=1 -D SE_EDITOR_COLD_PROVIDER_INIT=1 -I src -o $@ -l $(@:.o=.lst) $<
build/editor.prg: $(EDITOR_OBJ) $(EDITOR_COMMON_OBJ) $(EDITOR_MEMORY_OBJ) $(EDITOR_OBJECT_OBJ) $(EDITOR_DOCUMENT_OBJ) build/engine-state/range.o $(EDITOR_HISTORY_OBJ) $(EDITOR_OVERLAY_OBJ) $(EDITOR_HOT_OBJ) build/engine/trampoline.o build/search/dispatch.o build/search/state.o build/clipboard/state.o build/editor/clip-copy.o build/block/state.o build/block/selection.o build/block/controller.o build/render/state.o build/layout/state.o build/layout/dispatch.o $(DIAGNOSTICS_RESIDENT_OBJ) $(EDITOR_FILE_RESIDENT_OBJ) $(STYLE_RESIDENT_OBJ) $(GRID_RESIDENT_OBJ) $(FOLD_RESIDENT_OBJ) build/cache/state.o cfg/standalone.cfg tools/bindings.py tools/check_build.py
	$(LD65) -C cfg/standalone.cfg -o $@ -m build/editor.map -Ln build/editor.lbl $(EDITOR_OBJ) $(EDITOR_COMMON_OBJ) $(EDITOR_MEMORY_OBJ) $(EDITOR_OBJECT_OBJ) $(EDITOR_DOCUMENT_OBJ) build/engine-state/range.o $(EDITOR_HISTORY_OBJ) $(EDITOR_OVERLAY_OBJ) $(EDITOR_HOT_OBJ) build/engine/trampoline.o build/search/dispatch.o build/search/state.o build/clipboard/state.o build/editor/clip-copy.o build/block/state.o build/block/selection.o build/block/controller.o build/render/state.o build/layout/state.o build/layout/dispatch.o $(DIAGNOSTICS_RESIDENT_OBJ) $(EDITOR_FILE_RESIDENT_OBJ) $(STYLE_RESIDENT_OBJ) $(GRID_RESIDENT_OBJ) $(FOLD_RESIDENT_OBJ) build/cache/state.o
	$(PYTHON) tools/bindings.py --stem editor
	$(PYTHON) tools/check_build.py --stem editor
build/editor-api.inc: build/editor.prg tools/overlay_api.py
	$(PYTHON) tools/overlay_api.py --report build/editor-report.json --output $@ --all-public --symbols object_owner object_banks object_size_lo object_size_mid object_size_hi tui_putc40 tui_color tui_box_x tui_box_y tui_box_w tui_box_h box_rx box_ry text_ptr screen_ptr
build/overlays/eedit.o: src/overlays/history-edit.s src/history/hot_packet.inc src/hot/api.inc src/history/record.inc build/editor-api.inc
	$(CA65) -g -D EDITOR_BINDINGS=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/eplay.o: src/overlays/history-play.s src/history/record.inc build/editor-api.inc
	$(CA65) -g -D EDITOR_BINDINGS=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/window.o: src/overlays/hot-window.s src/render/api.inc src/style/api.inc src/overlays/render-damage.s src/render/geos/edit-certificate.inc src/render/geos/edit-certificate-body.inc src/hot/api.inc build/editor-api.inc
	$(CA65) -g -D EDITOR_BINDINGS=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/text40.o: src/overlays/editor40.s src/overlays/render-nowrap.s src/overlays/render-visibility.s src/layout/api.inc src/render/api.inc src/editor/geometry.inc src/overlays/render-cache.s src/overlays/render-style.s src/editor/geometry.inc src/editor/api.inc src/editor/menu-data.inc build/editor-api.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/menu40.o: src/overlays/editor-menu.s src/overlays/editor-settings-control.s build/editor-settings/editor-defaults.bin build/editor-settings/editor-font-catalog.bin src/overlays/editor-ui-draw.s src/diagnostics/ui.s src/diagnostics/api.inc src/editor/geometry.inc src/editor/api.inc src/editor/menu-data.inc build/editor-api.inc
	$(CA65) -g -I src -I build -I build/editor-settings -o $@ -l $(@:.o=.lst) $<
build/overlays/eedit.bin build/overlays/eplay.bin: build/overlays/%.bin: build/overlays/%.o cfg/overlay-c.cfg cfg/overlay-r.cfg
	$(LD65) -C $(if $(filter text40,$*),cfg/overlay-r.cfg,cfg/overlay-c.cfg) -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $<
build/overlays/eedit.seo: build/overlays/eedit.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 4 --resident-report build/editor-report.json
build/overlays/eplay.seo: build/overlays/eplay.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 5 --resident-report build/editor-report.json
build/overlays/window.seo: build/overlays/window.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 6 --resident-report build/editor-report.json
build/overlays/text40.seo: build/overlays/text40.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 1 --resident-report build/editor-report.json
build/overlays/menu40.seo: build/overlays/menu40.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 7 --resident-report build/editor-report.json
EDITOR_ASSETS = build/overlays/eedit.seo build/overlays/eplay.seo build/overlays/window.seo build/overlays/text40.seo build/overlays/menu40.seo
.PHONY: editor
editor: build/editor.prg $(EDITOR_ASSETS)

build/editor/box40.o: src/tui/box40.s build/editor-api.inc
	$(CA65) -g -D EDITOR_OVERLAY=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/editor/header40.o: src/tui/header40.s build/editor-api.inc
	$(CA65) -g -D EDITOR_OVERLAY=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/text40.bin: build/overlays/text40.o build/editor/header40.o build/editor/editor-chrome40.o cfg/overlay-r.cfg
	$(LD65) -C cfg/overlay-r.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/overlays/text40.o build/editor/header40.o build/editor/editor-chrome40.o
build/overlays/menu40.bin: build/overlays/menu40.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/overlays/menu40.o
build/overlays/popups.o: src/overlays/editor-popups.s src/overlays/editor-settings-draw.s build/editor-settings/editor-font-catalog.bin src/overlays/editor-ui-draw.s src/diagnostics/ui.s src/editor/menu-data.inc build/editor-api.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/popups.bin: build/overlays/popups.o build/editor/box40.o cfg/overlay-r.cfg
	$(LD65) -C cfg/overlay-r.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/overlays/popups.o build/editor/box40.o
build/overlays/popups.seo: build/overlays/popups.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 22 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/popups.seo
editor: build/overlays/popups.seo
.PHONY: editor-test
editor-test: editor
	$(PYTHON) tests/test_editor.py

build/supereditor.d81: build/editor.prg $(EDITOR_ASSETS)
.PHONY: editor-vice-test
editor-vice-test: disk
	$(PYTHON) tests/test_editor_vice.py
.PHONY: editor-failure-test
editor-failure-test: disk
	$(PYTHON) tests/test_editor_failures.py

.PHONY: boot-smoke

build/engine-api.inc: build/editor.prg tools/overlay_api.py
	$(PYTHON) tools/overlay_api.py --report build/editor-report.json --output $@ --symbols se_overlay_frame
build/engine-code/%.o: src/document/%.s src/document/frames/%.inc src/document/api.inc src/document/splice.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D ENGINE_CODE=1 -I src -o $@ -l $(@:.o=.lst) $<
build/engine/entry.o: src/engine/entry.s src/engine/api.inc build/engine-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
ENGINE_CODE_OBJ = build/engine/entry.o $(addprefix build/engine-code/,$(addsuffix .o,$(ENGINE_MODULES)))
build/engine-bindings.s: $(ENGINE_CODE_OBJ) build/editor.prg tools/engine_bindings.py
	$(PYTHON) tools/engine_bindings.py --report build/editor-report.json --output $@ $(ENGINE_CODE_OBJ)
build/engine/bindings.o: build/engine-bindings.s
	$(CA65) -g -o $@ $<
build/overlays/engine.bin: $(ENGINE_CODE_OBJ) build/engine/bindings.o cfg/overlay-r.cfg
	$(LD65) -C cfg/overlay-r.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $(ENGINE_CODE_OBJ) build/engine/bindings.o
build/overlays/engine.seo: build/overlays/engine.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 2 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/engine.seo
editor: build/overlays/engine.seo
build/supereditor.d81: build/overlays/engine.seo
.PHONY: engine-model-test
engine-model-test: editor
	$(PYTHON) tests/test_splice.py --editor-engine
	$(PYTHON) tests/test_refs.py --editor-engine
	$(PYTHON) tests/test_local.py --editor-engine
	$(PYTHON) tests/test_hot.py --editor-engine
	$(PYTHON) tests/test_history.py --editor-engine
.PHONY: engine-admission-test
engine-admission-test: editor
	$(PYTHON) tests/test_engine_admission.py

$(EDITOR_OBJ): src/nav/api.inc src/nav/header.inc
build/overlays/navigate.o: src/overlays/navigation.s src/overlays/nav-layout.s src/overlays/editor-edge.s src/layout/api.inc src/editor/geometry.inc src/nav/api.inc build/editor-api.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/navigate.bin: build/overlays/navigate.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $<
build/overlays/navigate.seo: build/overlays/navigate.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 8 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/navigate.seo
editor: build/overlays/navigate.seo
build/supereditor.d81: build/overlays/navigate.seo
.PHONY: navigation-test
navigation-test: editor
	$(PYTHON) tests/test_navigation.py
.PHONY: navigation-vice-test
navigation-vice-test: disk
	$(PYTHON) tests/test_navigation_vice.py

# Root-scheduled source search/word service. State linked last preserves old BSS.
build/search/state.o build/search/dispatch.o: src/search/api.inc
build/overlays/search.o: src/overlays/search.s build/editor-api.inc src/search/api.inc
	$(CA65) -g -I src -I build -o $@ -l build/overlays/search.lst $<
build/overlays/search.bin: build/overlays/search.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m build/overlays/search.map -Ln build/overlays/search.lbl $<
build/overlays/search.seo: build/overlays/search.bin build/editor-report.json tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 9 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/search.seo
editor: build/overlays/search.seo
build/supereditor.d81: build/overlays/search.seo

.PHONY: search-test search-vice-test
search-test: editor
	$(PYTHON) tests/test_search.py
	$(PYTHON) tests/test_search_arguments.py
search-vice-test: disk
	$(PYTHON) tests/test_search_vice.py

build/editor/commands.o build/overlays/navigate.o build/overlays/menu40.o: src/search/api.inc
build/search/dispatch.o: src/document/api.inc
build/overlays/search.o: src/editor/api.inc src/hot/api.inc src/document/api.inc src/document/math24.inc

# Integrated mark/private clipboard; UI paste goes through history, not paste.o.
build/block/state.o build/block/selection.o build/block/controller.o build/editor/commands.o: src/block/api.inc
build/overlays/block.o: src/overlays/block.s src/clipboard/copy.s src/clipboard/copy_overlay.s src/clipboard/frames/copy.inc src/block/api.inc src/clipboard/api.inc src/editor/api.inc build/editor-api.inc
	$(CA65) -g -I src -I build -o $@ -l build/overlays/block.lst $<
build/overlays/block.bin: build/overlays/block.o $(FILE_TRANSPORT_OBJ) build/editor-file-prod/transport-bindings.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m build/overlays/block.map -Ln build/overlays/block.lbl build/overlays/block.o $(FILE_TRANSPORT_OBJ) build/editor-file-prod/transport-bindings.o
build/overlays/block.seo: build/overlays/block.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 10 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/block.seo
editor: build/overlays/block.seo
build/supereditor.d81: build/overlays/block.seo

build/overlays/text40.o: src/block/api.inc
.PHONY: selection-test selection-vice-test
selection-test: editor
	$(PYTHON) tests/test_selection.py
	$(PYTHON) tests/test_selection_faults.py

.PHONY: editor-crc-test hot-packet-test
editor-crc-test: editor
	$(PYTHON) tests/test_editor_crc.py
hot-packet-test: editor
	$(PYTHON) tests/test_hot_packet_editor.py

selection-vice-test: disk
	$(PYTHON) tests/test_selection_vice.py

build/block/controller.o: src/editor/api.inc src/document/api.inc src/document/math24.inc src/history/api.inc src/hot/api.inc src/clipboard/api.inc src/object/api.inc
build/block/selection.o: src/hot/api.inc src/document/math24.inc
build/overlays/block.o: src/document/api.inc src/document/math24.inc src/history/api.inc src/hot/api.inc src/object/api.inc

# Bounded merged-source row-map preparation; shares resident navigation cleanup.
build/layout/dispatch.o: src/layout/api.inc src/editor/api.inc src/nav/api.inc src/render/api.inc
build/layout/state.o: src/layout/api.inc
build/editor/main.o build/editor/commands.o build/nav/dispatch.o build/block/controller.o: src/layout/api.inc
build/overlays/layout.o: src/overlays/layout.s src/layout/api.inc src/diagnostics/api.inc src/editor/geometry.inc build/editor-api.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/diagnostics-editor/bindings.s: build/overlays/layout.o $(DIAGNOSTICS_OVERLAY_OBJ) build/editor-report.json tools/diagnostics_bindings.py
	$(PYTHON) tools/diagnostics_bindings.py --report build/editor-report.json --output $@ build/overlays/layout.o $(DIAGNOSTICS_OVERLAY_OBJ)
build/diagnostics-editor/bindings.o: build/diagnostics-editor/bindings.s
	$(CA65) -g -o $@ $<
build/overlays/layout.bin: build/overlays/layout.o $(DIAGNOSTICS_OVERLAY_OBJ) build/diagnostics-editor/bindings.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/overlays/layout.o $(DIAGNOSTICS_OVERLAY_OBJ) build/diagnostics-editor/bindings.o
build/overlays/layout.seo: build/overlays/layout.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 11 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/layout.seo
editor: build/overlays/layout.seo
build/supereditor.d81: build/overlays/layout.seo

.PHONY: layout-test layout-vice-test
layout-test: editor
	$(PYTHON) tests/test_nowrap.py
	$(PYTHON) tests/test_viewport_edges.py
	$(PYTHON) tests/test_publication_wrap.py
	$(PYTHON) tests/test_redraw.py --require-incremental
layout-vice-test: disk
	$(PYTHON) tests/test_layout_vice.py

build/editor/commands.o: src/diagnostics/api.inc
.PHONY: editor-edges-test diagnostics-test
editor-edges-test: editor
	$(PYTHON) tests/test_editor_edges.py
diagnostics-test: editor
	$(PYTHON) tests/test_diagnostics_editor.py

# Explicit phase union: only state/cleanup/pump are resident. IEC transport is
# C10 and coordinator/modal keys are C12; every cross-C call returns to root.
FILE_COORDINATOR_OBJ = $(addprefix build/editor-file-prod/,$(addsuffix .o,coordinator open save dialog)) build/editor-file-prod/ui.o build/editor-file-prod/policy-code.o
build/editor-file-prod/%.o: src/editor_file/%.s src/editor_file/api.inc src/fileio/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/editor-file-prod/open.o: src/editor_file/open.s src/cache/editor/file-retire.inc src/cache/api.inc src/editor_file/api.inc src/fileio/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_FILE_CACHE_RETIRE=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/editor-file-prod/provider-state.o: src/fileio/state.s
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_FILE_UNION=1 -I src -o $@ $<
build/editor-file-prod/policy-state.o: src/fileio/save.s src/fileio/save.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_FILE_UNION=1 -D SE_FILE_STATE_ONLY=1 -I src -o $@ $<
build/editor-file-prod/policy-code.o: src/fileio/save.s src/fileio/save.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_FILE_CODE_ONLY=1 -I src -o $@ $<
build/file-transport/%.o: src/fileio/%.s src/fileio/api.inc src/fileio/internal.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
build/editor-file-prod/ui.o: src/overlays/fileio-ui.s src/editor_file/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_FILE_UI_KEY_ONLY=1 -I src -o $@ -l $(@:.o=.lst) $<
build/overlays/fileio.o: src/overlays/fileio-entry.s src/editor_file/api.inc build/editor-api.inc
	$(CA65) -g -D SE_FILE_UI_KEY_ONLY=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/editor-file-prod/transport-bindings.s: build/overlays/block.o $(FILE_TRANSPORT_OBJ) build/editor-report.json tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ --require-export se_file_transport build/overlays/block.o $(FILE_TRANSPORT_OBJ)
build/editor-file-prod/coordinator-bindings.s: build/overlays/fileio.o $(FILE_COORDINATOR_OBJ) build/editor-report.json tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ --require-export se_file_begin --require-export se_file_dialog build/overlays/fileio.o $(FILE_COORDINATOR_OBJ)
build/editor-file-prod/%-bindings.o: build/editor-file-prod/%-bindings.s
	$(CA65) -g -o $@ $<
build/overlays/fileio.bin: build/overlays/fileio.o $(FILE_COORDINATOR_OBJ) build/editor-file-prod/coordinator-bindings.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/overlays/fileio.o $(FILE_COORDINATOR_OBJ) build/editor-file-prod/coordinator-bindings.o
build/overlays/fileio.seo: build/overlays/fileio.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 12 --resident-report build/editor-report.json
build/editor-file-prod/dialog-draw.o: build/editor-api.inc src/editor_file/dialog-draw.s
build/overlays/block.o build/overlays/layout.o build/overlays/navigate.o build/editor/commands.o: src/editor_file/api.inc
EDITOR_ASSETS += build/overlays/fileio.seo
editor: build/overlays/fileio.seo
build/supereditor.d81: build/overlays/fileio.seo

# Rare control work remains operation-sized and shares one catalog entry.
AUX_CONTROL_OBJ = build/aux-control/layout-context.o build/aux-control/index.o build/aux-control/emergency.o build/editor-file-prod/dialog-draw.o build/editor/box40.o build/aux-control/checkpoint-refresh.o
build/nav/invalidate.o: src/nav/invalidate.s src/aux/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_INDEX_DISPATCH=1 -I src -o $@ -l $(@:.o=.lst) $<
build/aux-control/layout-context.o: src/aux/layout-context.s src/aux/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
build/aux-control/index.o: src/nav/invalidate.s src/nav/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_INDEX_IN_OVERLAY=1 -I src -o $@ -l $(@:.o=.lst) $<
build/aux-control/emergency.o: src/overlays/file-emergency.s src/editor_file/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
build/overlays/aux.o: src/overlays/aux.s src/aux/api.inc build/editor-api.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/aux-control/bindings.s: build/overlays/aux.o $(AUX_CONTROL_OBJ) build/editor-report.json tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ --require-export se_aux_index_changed --require-export se_aux_layout_context --require-export se_file_emergency --require-export se_file_recovery_key --require-export se_file_dialog_draw build/overlays/aux.o $(AUX_CONTROL_OBJ)
build/aux-control/bindings.o: build/aux-control/bindings.s
	$(CA65) -g -o $@ $<
build/overlays/aux.bin: build/overlays/aux.o $(AUX_CONTROL_OBJ) build/aux-control/bindings.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/overlays/aux.o $(AUX_CONTROL_OBJ) build/aux-control/bindings.o
build/overlays/aux.seo: build/overlays/aux.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 13 --resident-report build/editor-report.json
build/layout/dispatch.o: src/aux/api.inc
EDITOR_ASSETS += build/overlays/aux.seo
editor: build/overlays/aux.seo
build/supereditor.d81: build/overlays/aux.seo
.PHONY: diagnostics-vice-test
diagnostics-vice-test: disk
	$(PYTHON) tests/test_diagnostics_vice.py

# Capacity changes alter both BSS arrays and search/admission bounds.
build/overlay/cache.o build/editor/overlay-cache.o: src/overlay/format.inc

# Semantic source40 plan: C14 planner calls R14 reader; shared state is resident.
build/style-prod/%.o: src/style/%.s src/style/api.inc src/fold/source.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/style-prod/source-state.o: src/fold/source-state.s src/fold/source.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/style-prod/%-state.o: src/supermark/%.s src/supermark/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_SM_STATE_ONLY=1 -I src -o $@ $<
build/style-prod/%-code.o: src/supermark/%.s src/supermark/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_SM_CODE_ONLY=1 -I src -o $@ $<
build/style-api.inc: build/editor.prg tools/overlay_api.py
	$(PYTHON) tools/overlay_api.py --report build/editor-report.json --output $@ --all-public
build/style-prod/plan.o: src/style/plan.s src/style/api.inc src/supermark/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_STYLE_LEXICAL=1 -D SE_STYLE_GRID=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/style-prod/state.o: src/style/state.s src/style/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_STYLE_GRID=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/style-prod/lexical-control.o: src/style/lexical-control.s src/style/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_STYLE_GRID=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/style-prod/entry.o: src/style/entry.s build/style-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ $<
build/style-prod/reader-dispatch.o: src/style/reader-dispatch.s build/editor-api.inc
build/style-prod/reader-grid-dispatch.o: src/style/reader-dispatch.s build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_GRID_PRODUCER=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
STYLE_CODE_OBJ = build/style-prod/entry.o build/style-prod/plan.o build/style-prod/editor-control.o build/style-prod/reader-grid-dispatch.o build/style-prod/inline-code.o
build/style-prod/bindings.s: $(STYLE_CODE_OBJ) build/editor-report.json tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ --require-export se_style_auto $(STYLE_CODE_OBJ)
build/style-prod/bindings.o: build/style-prod/bindings.s
	$(CA65) -g -o $@ $<
build/overlays/styler.bin: $(STYLE_CODE_OBJ) build/style-prod/bindings.o cfg/style-c.cfg
	$(LD65) -C cfg/style-c.cfg -o $@ -Ln $(@:.bin=.lbl) -m $(@:.bin=.map) $(STYLE_CODE_OBJ) build/style-prod/bindings.o
build/overlays/styler.seo: build/overlays/styler.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 14 --resident-report build/editor-report.json
build/style-prod/source-%.o: src/fold/source-%.s src/fold/source.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/style-prod/source-entry.o: src/overlays/source-view.s build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ $<
STYLE_SOURCE_OBJ = build/style-prod/source-entry.o build/style-prod/source-context.o build/style-prod/source-read.o build/style-prod/block-source.o build/style-prod/block-code.o
build/style-prod/source-bindings.s: $(STYLE_SOURCE_OBJ) build/editor-report.json tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ --require-export se_fs_begin $(STYLE_SOURCE_OBJ)
build/style-prod/source-bindings.o: build/style-prod/source-bindings.s
	$(CA65) -g -o $@ $<
build/overlays/viewsource.bin: $(STYLE_SOURCE_OBJ) build/style-prod/source-bindings.o cfg/source-r.cfg
	$(LD65) -C cfg/source-r.cfg -o $@ -Ln $(@:.bin=.lbl) -m $(@:.bin=.map) $(STYLE_SOURCE_OBJ) build/style-prod/source-bindings.o
build/overlays/viewsource.seo: build/overlays/viewsource.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 14 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/styler.seo build/overlays/viewsource.seo
editor: build/overlays/styler.seo build/overlays/viewsource.seo
build/supereditor.d81: build/overlays/styler.seo build/overlays/viewsource.seo

# Root schedules C15 lexical slices while C14 retains the merged-source lease.
build/style-prod/lexical-entry.o: src/overlays/lexical.s build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ $<
STYLE_LEXICAL_OBJ = build/style-prod/lexical-entry.o build/style-prod/lexical-control.o build/style-prod/reader-dispatch.o build/style-prod/lexer-code.o
build/style-prod/lexical-bindings.s: $(STYLE_LEXICAL_OBJ) build/editor-report.json tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ --require-export se_style_lexical $(STYLE_LEXICAL_OBJ)
build/style-prod/lexical-bindings.o: build/style-prod/lexical-bindings.s
	$(CA65) -g -o $@ $<
build/overlays/lexical.bin: $(STYLE_LEXICAL_OBJ) build/style-prod/lexical-bindings.o cfg/lexical-c.cfg
	$(LD65) -C cfg/lexical-c.cfg -o $@ -Ln $(@:.bin=.lbl) -m $(@:.bin=.map) $(STYLE_LEXICAL_OBJ) build/style-prod/lexical-bindings.o
build/overlays/lexical.seo: build/overlays/lexical.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 15 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/lexical.seo
editor: build/overlays/lexical.seo
build/supereditor.d81: build/overlays/lexical.seo

build/editor/editor-chrome40.o: src/tui/editor-chrome40.s build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_OVERLAY=1 -I src -I build -o $@ -l $(@:.o=.lst) $<

# Integrated grid producer C16 and two fixed-layout rendering leaves R16/R17.
assets/fonts/generated/native8.bin: tools/fonts.py assets/fonts/narrow3x7.txt
	$(PYTHON) tools/fonts.py
build/grid-prod/%.o: src/render/narrow/%.s src/render/narrow/api.inc src/render/narrow/api8.inc assets/fonts/generated/manifest.json
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/grid-prod/native8.o: assets/fonts/generated/native8.bin
build/grid-prod/font4.o: src/render/narrow/font4.s assets/fonts/generated/manifest.json
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_FIXED_NARROW_FONT=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/grid-prod/grid80.o: src/overlays/grid.s src/render/narrow/grid.inc build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ $<
build/grid-prod/grid60.o: src/overlays/grid.s src/render/narrow/grid.inc build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D GRID60=1 -I src -I build -o $@ $<
GRID_COMMON_OBJ = build/grid-prod/row.o build/grid-prod/arbitrate.o build/grid-prod/cell8.o
build/overlays/grid80.bin: build/grid-prod/grid80.o build/grid-prod/row80.o build/grid-prod/cell8.o build/grid-prod/font4.o build/grid-prod/native8.o cfg/grid-r.cfg
	$(LD65) -C cfg/grid-r.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/grid-prod/grid80.o build/grid-prod/row80.o build/grid-prod/cell8.o build/grid-prod/font4.o build/grid-prod/native8.o
build/overlays/grid60.bin: build/grid-prod/grid60.o $(GRID_COMMON_OBJ) build/grid-prod/font5.o build/grid-prod/native8.o cfg/grid-r.cfg
	$(LD65) -C cfg/grid-r.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/grid-prod/grid60.o $(GRID_COMMON_OBJ) build/grid-prod/font5.o build/grid-prod/native8.o
build/overlays/grid80.seo: build/overlays/grid80.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 16 --resident-report build/editor-report.json
build/overlays/grid60.seo: build/overlays/grid60.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 17 --resident-report build/editor-report.json
build/grid-prod/editor.o: src/overlays/grid-editor.s $(wildcard src/render/grid/*.s) src/render/grid/api.inc src/render/grid/cache.inc src/overlays/render-style.s build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_OVERLAY=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/grid-prod/mode.o: src/render/grid/mode.s build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_OVERLAY=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/grid-prod/cache.o: src/render/grid/cache.s src/render/grid/cache.inc build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_OVERLAY=1 -I src -I build -o $@ -l $(@:.o=.lst) $<
build/grid-prod/cache-state.o: src/render/grid/cache-state.s
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/overlays/gridedit.bin: build/grid-prod/editor.o build/grid-prod/mode.o build/grid-prod/cache.o build/editor/editor-chrome40.o build/editor/header40.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) build/grid-prod/editor.o build/grid-prod/mode.o build/grid-prod/cache.o build/editor/editor-chrome40.o build/editor/header40.o
build/overlays/gridedit.seo: build/overlays/gridedit.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 16 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/gridedit.seo build/overlays/grid80.seo build/overlays/grid60.seo
editor: build/overlays/gridedit.seo build/overlays/grid80.seo build/overlays/grid60.seo
build/supereditor.d81: build/overlays/gridedit.seo build/overlays/grid80.seo build/overlays/grid60.seo

# Fold phase owner3; state-only objects share LINEINDEX without moving SM/FS.
build/fold-prod/state.o build/fold-prod/builder-state.o: build/fold-prod/%.o: src/fold/%.s src/fold/api.inc src/fold/builder.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
build/fold-prod/editor-api.inc: build/editor.prg src/fold/editor-leaves/binding.py tools/bindings.py
	$(PYTHON) src/fold/editor-leaves/binding.py --report build/editor-report.json --output $@
build/fold-prod/parse-entry.o: src/fold/editor-leaves/builder-entry.s src/fold/editor-leaves/api.inc build/fold-prod/editor-api.inc
	$(CA65) -g -I build/fold-prod -I src -o $@ $<
build/fold-prod/finish-entry.o: src/fold/editor-leaves/builder-entry.s src/fold/editor-leaves/api.inc build/fold-prod/editor-api.inc
	$(CA65) -g -D FOLD_FINISH=1 -I build/fold-prod -I src -o $@ $<
build/fold-prod/core-entry.o: src/fold/editor-leaves/core-entry.s src/fold/editor-leaves/api.inc src/fold/locate.inc build/fold-prod/editor-api.inc
	$(CA65) -g -I build/fold-prod -I src -o $@ $<
build/fold-prod/core-bridges.o build/fold-prod/parse-stubs.o build/fold-prod/finish-stubs.o: build/fold-prod/%.o: src/fold/editor-leaves/%.s src/fold/editor-leaves/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/fold-prod/builder.o: src/fold/builder.s src/fold/builder.inc src/fold/source.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_FOLD_EDITOR_SOURCE=1 -I src -o $@ $<
build/fold-prod/store.o build/fold-prod/validate.o build/fold-prod/query.o build/fold-prod/action.o build/fold-prod/locate.o build/fold-prod/builder-filter.o: build/fold-prod/%.o: src/fold/%.s src/fold/api.inc src/fold/builder.inc src/fold/locate.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/fold-prod/block-code.o: src/supermark/block.s src/supermark/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_SM_CODE_ONLY=1 -I src -o $@ $<
build/fold-prod/reader-dispatch.o: src/style/reader-dispatch.s build/fold-prod/editor-api.inc
	$(CA65) -g -I build/fold-prod -I src -o $@ $<
FOLD_PARSE_OBJ = build/fold-prod/parse-entry.o build/fold-prod/builder.o build/fold-prod/builder-retain.o build/fold-prod/block-code.o build/fold-prod/core-bridges.o build/fold-prod/reader-dispatch.o build/fold-prod/parse-stubs.o
FOLD_FINISH_OBJ = build/fold-prod/finish-entry.o build/fold-prod/builder.o build/fold-prod/builder-filter.o build/fold-prod/builder-retain.o build/fold-prod/core-bridges.o build/fold-prod/reader-dispatch.o build/fold-prod/finish-stubs.o
FOLD_CORE_OBJ = build/fold-prod/core-entry.o build/fold-prod/store.o build/fold-prod/validate.o build/fold-prod/query.o build/fold-prod/action.o build/fold-prod/locate.o
build/fold-prod/parse-bindings.s: $(FOLD_PARSE_OBJ) build/editor.prg tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ $(FOLD_PARSE_OBJ)
build/fold-prod/finish-bindings.s: $(FOLD_FINISH_OBJ) build/editor.prg tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ $(FOLD_FINISH_OBJ)
build/fold-prod/core-bindings.s: $(FOLD_CORE_OBJ) build/editor.prg tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ $(FOLD_CORE_OBJ)
build/fold-prod/%-bindings.o: build/fold-prod/%-bindings.s
	$(CA65) -g -o $@ $<
build/overlays/foldparse.bin: $(FOLD_PARSE_OBJ) build/fold-prod/parse-bindings.o cfg/fold-editor-parse.cfg
	$(LD65) -C cfg/fold-editor-parse.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $(FOLD_PARSE_OBJ) build/fold-prod/parse-bindings.o
build/overlays/foldfinish.bin: $(FOLD_FINISH_OBJ) build/fold-prod/finish-bindings.o cfg/fold-editor-finish.cfg
	$(LD65) -C cfg/fold-editor-finish.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $(FOLD_FINISH_OBJ) build/fold-prod/finish-bindings.o
build/overlays/foldcore.bin: $(FOLD_CORE_OBJ) build/fold-prod/core-bindings.o cfg/fold-editor-core.cfg
	$(LD65) -C cfg/fold-editor-core.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $(FOLD_CORE_OBJ) build/fold-prod/core-bindings.o
build/overlays/foldparse.seo: build/overlays/foldparse.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 17 --resident-report build/editor-report.json
build/overlays/foldfinish.seo: build/overlays/foldfinish.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 18 --resident-report build/editor-report.json
build/overlays/foldcore.seo: build/overlays/foldcore.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 18 --resident-report build/editor-report.json
FOLD_ASSETS = build/overlays/foldparse.seo build/overlays/foldfinish.seo build/overlays/foldcore.seo
EDITOR_ASSETS += $(FOLD_ASSETS)
editor: $(FOLD_ASSETS)
build/supereditor.d81: $(FOLD_ASSETS)

# Retained fold descriptor/projection follows existing GRID BSS; key code is C19.
build/editor_fold/%.o: src/editor_fold/%.s src/editor_fold/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<

build/overlays/layout.o: src/overlays/layout-fold.s src/editor_fold/api.inc

# C19 fold coordinator; resident owns only cleanup/aliases/descriptor, not keys.
build/fold-prod/control-entry.o: src/overlays/fold-editor.s build/fold-prod/editor-api.inc src/editor_fold/api.inc src/editor_fold/controller.inc
	$(CA65) -g -I build/fold-prod -I src -o $@ $<
build/fold-prod/coordinator.o: src/editor_fold/coordinator.s src/editor_fold/api.inc src/editor_fold/controller.inc src/fold/editor-leaves/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/fold-prod/key.o: src/editor_fold/key.s src/editor_fold/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/fold-prod/source-context.o: src/fold/source-context.s src/fold/source.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/fold-prod/create.o: src/editor_fold/create.s src/cache/api.inc src/fold/api.inc src/editor_fold/controller.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
FOLD_CONTROL_OBJ = build/fold-prod/control-entry.o build/fold-prod/coordinator.o build/fold-prod/retain.o build/fold-prod/reader-dispatch.o build/fold-prod/create.o
build/fold-prod/control-bindings.s: $(FOLD_CONTROL_OBJ) build/editor.prg tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ $(FOLD_CONTROL_OBJ)
build/overlays/foldctl.bin: $(FOLD_CONTROL_OBJ) build/fold-prod/control-bindings.o cfg/fold-editor-control.cfg
	$(LD65) -C cfg/fold-editor-control.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $(FOLD_CONTROL_OBJ) build/fold-prod/control-bindings.o
build/overlays/foldctl.seo: build/overlays/foldctl.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 1 --id 19 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/foldctl.seo
editor: build/overlays/foldctl.seo
build/supereditor.d81: build/overlays/foldctl.seo
build/editor_fold/dispatch.o build/editor_fold/emergency.o build/editor_fold/phase-state.o: src/editor_fold/controller.inc

# Rare selected-range reader uses a separate R19; R2 mutation payload is full.
build/engine/range-entry.o: src/engine/range-entry.s src/engine/api.inc build/engine-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ $<
RANGE_CODE_OBJ = build/engine/range-entry.o build/engine-code/range.o build/editor_fold/journal-code.o build/geos-prod/checkpoint-outgoing.o build/geos-prod/cache-warm.o
build/range-bindings.s: $(RANGE_CODE_OBJ) build/editor.prg tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ --require-export se_range_begin --require-export se_range_step $(RANGE_CODE_OBJ)
build/engine/range-bindings.o: build/range-bindings.s
	$(CA65) -g -o $@ $<
build/overlays/rangeio.bin: $(RANGE_CODE_OBJ) build/engine/range-bindings.o cfg/range-journal.cfg
	$(LD65) -C cfg/range-journal.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $(RANGE_CODE_OBJ) build/engine/range-bindings.o
build/overlays/rangeio.seo: build/overlays/rangeio.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 19 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/rangeio.seo
editor: build/overlays/rangeio.seo
build/supereditor.d81: build/overlays/rangeio.seo

# Edited fold hints and the optional source publication journal.
build/fold-prod/builder-retain.o: src/fold/builder-retain.s src/fold/builder.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_FOLD_EDITOR_SOURCE=1 -I src -o $@ $<
build/editor_fold/journal-code.o: src/editor_fold/journal.s src/editor_fold/journal.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<

build/fold-prod/transform-entry.o: src/overlays/fold-transform.s src/fold/transform.inc build/fold-prod/editor-api.inc
	$(CA65) -g -I build/fold-prod -I src -o $@ $<
build/fold-prod/transform.o: src/fold/transform.s src/fold/transform.inc
	$(CA65) -g -I src -o $@ $<
FOLD_TRANSFORM_OBJ = build/fold-prod/transform-entry.o build/fold-prod/transform.o
build/fold-prod/transform-bindings.s: $(FOLD_TRANSFORM_OBJ) build/editor.prg tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ $(FOLD_TRANSFORM_OBJ)
build/overlays/foldxform.bin: $(FOLD_TRANSFORM_OBJ) build/fold-prod/transform-bindings.o cfg/fold-editor-transform.cfg
	$(LD65) -C cfg/fold-editor-transform.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $(FOLD_TRANSFORM_OBJ) build/fold-prod/transform-bindings.o
build/overlays/foldxform.seo: build/overlays/foldxform.bin tools/overlays.py
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 20 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/foldxform.seo
editor: build/overlays/foldxform.seo
build/supereditor.d81: build/overlays/foldxform.seo

build/fold-prod/retain.o: src/editor_fold/retain.s src/editor_fold/journal.inc src/fold/transform.inc src/editor_fold/controller.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<

# Object registry initialization is cold-only in the standalone editor. Warm
# create/resize/validate/copy remain resident; generic probes keep CODE layout.
build/editor/object-allocate.o: src/object/allocate.s src/object/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_COLD_OBJECT_INIT=1 -I src -o $@ -l $(@:.o=.lst) $<

# Live GEOS pages: C20 source/layout, C21 controller, C22 painter, R21 raster.
# Each sealed image is assembled against the current resident, and cache code
# is linked independently into both C consumers (never a same-slot call).
build/geos-resident/dispatch.o: src/render/geos/dispatch.s src/render/geos/editor.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
build/geos-prod/editor-api.inc: build/editor.prg src/fold/editor-leaves/binding.py
	$(PYTHON) src/fold/editor-leaves/binding.py --report build/editor-report.json --output $@
build/geos-prod/%.o: src/render/geos/%.s src/render/geos/editor.inc build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
build/geos-prod/source-line.o: src/render/geos/source-line.s src/render/geos/source-inline.s src/render/geos/source-line.inc src/render/geos/semantic.inc build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_EDITOR_GEOS_INLINE=1 -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
build/geos-prod/row.o: src/render/geos/row-fast.s src/render/geos/row-validate.s src/render/geos/row-resolve.s src/render/geos/row.inc
build/geos-prod/header.o: src/tui/header40.s
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/geos-prod/chrome.o: src/tui/editor-chrome40.s
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
GEOS_LAYOUT_OBJ = build/geos-prod/source-line.o build/geos-prod/line.o build/geos-prod/assets.o
GEOS_ROW_OBJ = build/geos-prod/row-job.o build/geos-prod/row-job-loans.o build/geos-prod/literal-byte/measure.o build/geos-prod/literal-byte/glyph.o build/geos-prod/literal-byte/assets.o
build/geos-prod/literal-byte/%.o: src/render/geos/literal-byte/%.s $(wildcard src/render/geos/*.inc)
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<
GEOS_PAGE_OBJ = build/geos-prod/page.o build/geos-prod/cache.o
GEOS_PAINT_OBJ = build/geos-prod/page-paint-entry.o build/geos-prod/page-paint.o build/geos-prod/native-pan.o build/geos-prod/cache-paint.o
GEOS_NAV_OBJ = build/geos-prod/navigation.o build/geos-prod/cache-nav.o
GEOS_DELTA_OBJ = build/geos-prod/edit-cache.o build/geos-prod/cache-warm.o
GEOS_CARET_OBJ = build/geos-prod/caret-cache.o build/geos-prod/cache-warm.o build/geos-prod/caret-ui.o build/geos-prod/chrome.o build/geos-prod/header.o
build/geos-prod/block-parser.o: src/supermark/block.s src/supermark/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
build/geos-prod/lex-parser.o: src/supermark/lexer.s src/supermark/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
GEOS_SEMANTIC_OBJ = build/geos-prod/semantic.o build/geos-prod/block-parser.o build/geos-prod/checkpoint-codec.o
GEOS_SEMLEX_OBJ = build/geos-prod/semantic-lex.o build/geos-prod/lex-parser.o
build/geos-prod/inline-parser.o: src/supermark/inline.s src/supermark/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ $<
GEOS_INLINE_OBJ = build/geos-prod/inline.o build/geos-prod/inline-parser.o
build/geos-prod/inline.o: src/render/geos/inline.s src/render/geos/body-plan/api.inc build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
build/geos-prod/cache-nav.o: src/render/geos/cache.s build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D SE_GP_CACHE_WARM_ONLY=1 -D SE_GP_CACHE_READ_ONLY=1 -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
define GEOS_IMAGE
build/geos-prod/$(1)-bindings.s: $(2) build/editor.prg tools/module_bindings.py
	$$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $$@ $(2)
build/geos-prod/$(1)-bindings.o: build/geos-prod/$(1)-bindings.s
	$$(CA65) -g -o $$@ $$<
build/overlays/$(1).bin: $(2) build/geos-prod/$(1)-bindings.o $(3)
	$$(LD65) -C $(3) -o $$@ -m $$(@:.bin=.map) -Ln $$(@:.bin=.lbl) $(2) build/geos-prod/$(1)-bindings.o
build/overlays/$(1).seo: build/overlays/$(1).bin tools/overlays.py
	$$(PYTHON) tools/overlays.py $$< $$@ --slot $(4) --id $(5) --resident-report build/editor-report.json
endef
$(eval $(call GEOS_IMAGE,geosline,$(GEOS_LAYOUT_OBJ),cfg/geos-editor-layout.cfg,1,20))
$(eval $(call GEOS_IMAGE,geospage,$(GEOS_PAGE_OBJ),cfg/geos-editor-page.cfg,1,21))
$(eval $(call GEOS_IMAGE,geospaint,$(GEOS_PAINT_OBJ),cfg/geos-editor-page.cfg,1,22))
$(eval $(call GEOS_IMAGE,geosrow,$(GEOS_ROW_OBJ),cfg/geos-editor-row.cfg,0,21))
$(eval $(call GEOS_IMAGE,geosnav,$(GEOS_NAV_OBJ),cfg/geos-editor-navigation.cfg,1,23))
$(eval $(call GEOS_IMAGE,geosdelta,$(GEOS_DELTA_OBJ),cfg/overlay-r.cfg,0,28))
$(eval $(call GEOS_IMAGE,geoscaret,$(GEOS_CARET_OBJ),cfg/overlay-r.cfg,0,27))
$(eval $(call GEOS_IMAGE,geossema,$(GEOS_SEMANTIC_OBJ),cfg/geos-editor-semantic.cfg,1,24))
$(eval $(call GEOS_IMAGE,geoslex,$(GEOS_SEMLEX_OBJ),cfg/geos-editor-semantic-lex.cfg,1,25))
$(eval $(call GEOS_IMAGE,geosinln,$(GEOS_INLINE_OBJ),cfg/geos-editor-inline.cfg,1,26))
GEOS_ASSETS = build/overlays/geosline.seo build/overlays/geospage.seo build/overlays/geospaint.seo build/overlays/geosrow.seo build/overlays/geosnav.seo build/overlays/geossema.seo build/overlays/geoslex.seo build/overlays/geosinln.seo build/overlays/geoscaret.seo build/overlays/geosdelta.seo
EDITOR_ASSETS += $(GEOS_ASSETS)
editor: $(GEOS_ASSETS)
build/supereditor.d81: $(GEOS_ASSETS)

# Genuine GEOS fonts remain data; three operation-sized presentation modules.
build/geos-font-catalog/catalog.json: build/geos-font-catalog/font-pack.bin
	@test -f $@
build/geos-font-catalog/font-pack.bin: tools/geos_font_catalog.py
	$(PYTHON) tools/geos_font_catalog.py
build/geos-prod/geos-font-pack.inc: tools/geos_font_store_meta.py build/geos-font-catalog/font-pack.bin
	mkdir -p $(dir $@)
	$(PYTHON) tools/geos_font_store_meta.py --pack build/geos-font-catalog/font-pack.bin --output $@
build/geos-prod/preview.o: src/render/geos/preview.s src/render/geos/preview.inc src/render/geos/preview-paint.inc src/render/geos/preview-cache.inc src/render/geos/preview-cache.s src/render/geos/catalog-glyph.inc src/render/geos/settings.inc build/editor-api.inc
	$(CA65) -g -I src -I build -I build/geos-prod -o $@ -l $(@:.o=.lst) $<
build/geos-prod/preview-row-entry.o: src/render/geos/preview-row-entry.s src/render/geos/preview.inc src/render/geos/catalog-glyph.inc src/render/geos/font-store.inc build/editor-api.inc
	$(CA65) -g -I src -I build -I build/geos-prod -o $@ -l $(@:.o=.lst) $<
build/geos-prod/catalog-glyph.o: src/render/geos/catalog-glyph.s src/render/geos/catalog-glyph.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/geos-prod/font-store.o: src/render/geos/font-store.s src/render/geos/font-store.inc build/geos-prod/geos-font-pack.inc
	$(CA65) -g -D SE_GEOS_PREVIEW_FAST=1 -I src -I build/geos-prod -o $@ -l $(@:.o=.lst) $<
build/geos-prod/font-import.o: src/render/geos/font-import.s src/render/geos/font-store.inc build/geos-prod/geos-font-pack.inc
	$(CA65) -g -I src -I build/geos-prod -o $@ -l $(@:.o=.lst) $<
build/geos-prod/font-import-entry.o: src/render/geos/font-import-entry.s src/render/geos/font-store.inc build/editor-api.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
GEOS_PREVIEW_OBJ=build/geos-prod/preview.o
GEOS_FONTROW_OBJ=build/geos-prod/preview-glyph-cache/entry.o build/geos-prod/preview-glyph-cache/ink.o build/geos-prod/preview-glyph-cache/codec.o build/geos-prod/preview-glyph-cache/controller.o build/geos-prod/font-store.o
$(filter-out build/geos-prod/font-store.o,$(GEOS_FONTROW_OBJ)): build/geos-prod/preview-glyph-cache/%.o: src/render/geos/preview-glyph-cache/%.s $(wildcard src/render/geos/*.inc) build/geos-prod/geos-font-pack.inc build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build/geos-prod -o $@ -l $(@:.o=.lst) $<
GEOS_FONTIN_OBJ=build/geos-prod/font-import-entry.o build/geos-prod/font-import.o
$(eval $(call GEOS_IMAGE,geospreview,$(GEOS_PREVIEW_OBJ),cfg/geos-editor-page.cfg,1,27))
$(eval $(call GEOS_IMAGE,geosfontrow,$(GEOS_FONTROW_OBJ),cfg/overlay-r.cfg,0,23))
$(eval $(call GEOS_IMAGE,geosfontin,$(GEOS_FONTIN_OBJ),cfg/overlay-c.cfg,1,28))
editor: build/overlays/geospreview.seo build/overlays/geosfontrow.seo build/overlays/geosfontin.seo
build/supereditor.d81: build/overlays/geospreview.seo build/overlays/geosfontrow.seo build/overlays/geosfontin.seo build/geos-font-catalog/font-pack.bin

# Shared GEOS folded projection query and virtual-cell policy micro modules.
GRID_GEOMETRY_OBJ=$(addprefix build/geos-prod/grid-geometry-,kernel.o authority.o transaction.o)
$(GRID_GEOMETRY_OBJ): build/geos-prod/grid-geometry-%.o: src/render/grid/geometry/%.s src/fold/source.inc src/render/grid/caret/api.inc src/render/grid/paragraph/long.inc build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build/geos-prod -o $@ -l $(@:.o=.lst) $<
GEOS_FOLD_OBJ=build/geos-prod/fold-entry.o build/geos-prod/fold-query.o $(GRID_GEOMETRY_OBJ)
GEOS_TAIL_OBJ=build/geos-prod/tail-entry.o
build/geos-prod/fold-query.o: src/render/geos/fold-query.s src/render/geos/fold-query.inc build/geos-prod/editor-api.inc
build/geos-prod/fold-entry.o: src/render/geos/fold-entry.s src/render/geos/fold-query.inc build/geos-prod/editor-api.inc
build/geos-prod/tail-entry.o: src/render/geos/tail-entry.s src/render/geos/editor.inc build/editor-api.inc
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
$(eval $(call GEOS_IMAGE,geosfold,$(GEOS_FOLD_OBJ),cfg/overlay-r.cfg,0,24))
# R25 also supplies C33's shared helpers; the bound pair is built below.
editor: build/overlays/geosfold.seo build/overlays/geostail.seo
build/supereditor.d81: build/overlays/geosfold.seo build/overlays/geostail.seo

# Pure tail policy stays in C22; omit its unused page allocation path.
build/geos-prod/cache-warm.o: src/render/geos/cache.s
build/geos-prod/page-paint.o build/geos-prod/tail-entry.o: src/render/geos/tail-policy.inc

build/geos-prod/chrome.o: src/tui/editor-chrome40.s
build/grid-prod/editor.o: src/render/grid/preflight.s

build/geos-prod/caret-cache.o: src/render/geos/edit-certificate.inc
build/geos-prod/caret-ui.o: src/render/geos/caret-ui.inc src/render/geos/caret-cache.inc

# Standalone callable lifecycle adapter. Fresh0A00 template stays in sealed C29.
LIFECYCLE_CONTROLLER_OBJ=build/lifecycle-prod/adapter.o build/lifecycle-prod/preflight.o build/lifecycle-prod/resume.o
LIFECYCLE_COPY_OBJ=build/lifecycle-prod/copy-entry.o
build/lifecycle-prod/%.o: src/lifecycle/%.s $(wildcard src/lifecycle/*.inc) build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
build/lifecycle-prod/preflight.o: src/lifecycle/preflight.s $(wildcard src/lifecycle/*.inc) build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D LC_PREFLIGHT_IN_C29=1 -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
$(eval $(call GEOS_IMAGE,lifectrl,$(LIFECYCLE_CONTROLLER_OBJ),cfg/lifecycle-controller.cfg,1,29))
$(eval $(call GEOS_IMAGE,lifecopy,$(LIFECYCLE_COPY_OBJ),cfg/overlay-r.cfg,0,26))
LIFECYCLE_ASSETS=build/overlays/lifectrl.seo build/overlays/lifecopy.seo
EDITOR_ASSETS += $(LIFECYCLE_ASSETS)
editor: $(LIFECYCLE_ASSETS)
build/supereditor.d81: $(LIFECYCLE_ASSETS)

build/geos-prod/cache-paint.o: src/render/geos/cache.s
build/geos-prod/page-paint.o: src/render/geos/edit-cache.inc

build/geos-prod/page.o build/geos-prod/page-paint.o build/geos-prod/edit-cache.o: src/render/geos/edit-cache.inc
build/geos-prod/edit-cache.o: src/render/geos/edit-certificate.inc src/render/geos/caret-cache.inc

build/geos-prod/catalog-preview.o build/geos-prod/catalog-ink-preview.o: src/render/geos/catalog-glyph.inc src/render/geos/font-store.inc

build/geos-prod/semantic.o build/geos-prod/semantic-lex.o build/geos-prod/inline.o: src/render/geos/preview-handoff.inc

# Verified normal-font cache, built in the cold path and reused by hot typing.
GEOS_TYPING_FONT_OBJ=build/geos-prod/typing-font-cache.o build/geos-prod/typing-font-loans.o build/geos-prod/measure.o build/geos-prod/glyph.o build/geos-prod/assets.o build/geos-prod/cache-warm.o
build/geos-prod/typing-font-cache.o: src/render/geos/typing-font-cache.inc src/render/geos/typing-font-witness.inc
$(eval $(call GEOS_IMAGE,gfont,$(GEOS_TYPING_FONT_OBJ),cfg/overlay-c.cfg,1,30))
editor: build/overlays/gfont.seo
build/supereditor.d81: build/overlays/gfont.seo

# Plain-line typing keeps C6/R30 hot; imported images retain ordinary CRC checks.
GEOS_TYPING_OBJ=$(addprefix build/geos-prod/typing/,$(addsuffix .o,worker guard patch-buffered status-normal status-raster transfer))
build/geos-prod/typing/%.o: src/render/geos/typing/%.s build/geos-prod/editor-api.inc src/render/geos/editor.inc $(wildcard src/render/geos/typing/*.inc)
	mkdir -p $(dir $@)
	$(CA65) -g -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
# R30 is a compact supervisor; C32 owns the bounded plain/styled transaction.
STYLE_TYPING_SRC=$(wildcard src/render/geos/style-typing/* src/render/geos/typing/*.inc) src/render/presentation.inc assets/fonts/generated/bsw9-widths.bin src/render/geos/editor.inc src/render/geos/font-store.inc src/render/geos/typing/transfer.s src/render/geos/typing/status-normal.s src/render/geos/typing/status-raster.s src/render/geos/typing/guard.inc src/render/geos/typing/certificate.inc
build/geos-prod/style-typing/worker.seo: $(STYLE_TYPING_SRC) build/editor.prg build/editor-report.json build/editor.lbl tools/module_bindings.py tools/bindings.py tools/overlays.py
	$(PYTHON) src/render/geos/style-typing/build.py build/geos-prod/style-typing .
build/geos-prod/style-typing/stage.seo: build/geos-prod/style-typing/worker.seo
	@test -f $@
build/overlays/gtype.seo: build/geos-prod/style-typing/worker.seo
	cp $< $@
build/overlays/type.seo: build/geos-prod/style-typing/stage.seo
	cp $< $@
editor: build/overlays/type.seo
build/supereditor.d81: build/overlays/type.seo
GEOS_TYPING_WINDOW_OBJ=build/overlays/window.o build/geos-prod/typing/certify.o build/geos-prod/typing/transfer.o
build/geos-prod/window-bindings.s: $(GEOS_TYPING_WINDOW_OBJ) build/editor.prg tools/module_bindings.py
	$(PYTHON) tools/module_bindings.py --report build/editor-report.json --output $@ $(GEOS_TYPING_WINDOW_OBJ)
build/geos-prod/window-bindings.o: build/geos-prod/window-bindings.s
	$(CA65) -g -o $@ $<
build/overlays/window.bin: $(GEOS_TYPING_WINDOW_OBJ) build/geos-prod/window-bindings.o cfg/overlay-c.cfg
	$(LD65) -C cfg/overlay-c.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $(GEOS_TYPING_WINDOW_OBJ) build/geos-prod/window-bindings.o
editor: build/overlays/gtype.seo
build/supereditor.d81: build/overlays/gtype.seo

build/geos-prod/semantic.o: src/render/geos/preview-prepare.inc src/render/geos/preview.inc src/render/geos/settings.inc

# R31 code typing uses a separately sealed C31 data capsule. The code payload
# is linked to run at5000; only R31's checked primer may execute that window.
CODE_TYPING_SRC=$(wildcard src/render/geos/code-typing/*) src/render/presentation.inc src/supermark/lexer.s src/supermark/api.inc src/render/geos/typing/status-normal.s src/render/geos/typing/status-raster.s
build/geos-prod/code-typing/worker.seo: $(CODE_TYPING_SRC) build/editor.prg build/editor-report.json build/editor.lbl tools/module_bindings.py tools/bindings.py tools/overlays.py
	mkdir -p build/geos-prod/code-typing
	$(PYTHON) src/render/geos/code-typing/build-worker.py build/geos-prod/code-typing .
build/geos-prod/code-typing/stage.seo: build/geos-prod/code-typing/worker.seo
	@test -f $@
	@touch $@
build/overlays/code.seo: build/geos-prod/code-typing/worker.seo
	cp $< $@
build/overlays/clex.seo: build/geos-prod/code-typing/stage.seo
	cp $< $@
editor: build/overlays/code.seo build/overlays/clex.seo
build/supereditor.d81: build/overlays/code.seo build/overlays/clex.seo

# Managed code is standalone-editor-only; generic probes keep strict objects.
build/editor-memory/dma.o: src/reu/dma.s
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_MANAGED_CODE=1 -I src -o $@ -l $(@:.o=.lst) $<
build/editor/overlay-read.o: src/iec/overlay_read.s src/overlay/format.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_MANAGED_CODE=1 -I src -o $@ -l $(@:.o=.lst) $<
build/editor/history-dispatch.o: src/history/dispatch.s src/history/api.inc src/object/api.inc src/document/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_COLD_DISPATCH=1 -I src -o $@ -l $(@:.o=.lst) $<
build/editor/startup.o: src/editor/startup.s src/editor/catalog.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_MANAGED_CODE=1 -I src -o $@ -l $(@:.o=.lst) src/editor/startup.s
build/lifecycle-prod/resume.o: src/lifecycle/resume.s $(wildcard src/lifecycle/*.inc) build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_MANAGED_CODE=1 -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) src/lifecycle/resume.s

# Lifecycle direct stashes revoke managed preview-body verification.
build/lifecycle-prod/copy-entry.o: src/lifecycle/copy-entry.s $(wildcard src/lifecycle/*.inc) build/geos-prod/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D EDITOR_MANAGED_CODE=1 -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<

# Retained source-grid caret/typing; exact R16/R17 font and R25 helper witnesses.
GRID_PAIR_INPUTS = $(wildcard src/render/grid/caret/*) $(wildcard src/render/grid/paragraph/*) src/render/geos/typing/status-normal.s $(wildcard src/render/geos/*.inc) tools/module_bindings.py tools/bindings.py tools/overlays.py
build/grid-caret/pair.stamp: build/editor.prg build/editor.lbl build/editor-report.json build/overlays/grid80.seo build/overlays/grid60.seo build/overlays/styler.seo build/overlays/viewsource.seo assets/fonts/generated/native8.bin $(GRID_PAIR_INPUTS)
	$(PYTHON) src/render/grid/caret/build.py build/grid-caret $(CURDIR)
	touch $@
build/overlays/grid.seo: build/grid-caret/pair.stamp
	cp build/grid-caret/grid.seo $@
	cp build/grid-caret/grid.bin build/overlays/grid.bin
	cp build/grid-caret/grid.lbl build/overlays/grid.lbl
	cp build/grid-caret/grid.map build/overlays/grid.map
build/overlays/geostail.seo: build/grid-caret/pair.stamp
	cp build/grid-caret/geostail.seo $@
	cp build/grid-caret/geostail.bin build/overlays/geostail.bin
	cp build/grid-caret/geostail.lbl build/overlays/geostail.lbl
	cp build/grid-caret/geostail.map build/overlays/geostail.map
EDITOR_ASSETS += build/overlays/grid.seo
editor: build/overlays/grid.seo
build/supereditor.d81: build/overlays/grid.seo

# Plain Return/BACK geometry: one authenticated R29 transaction, no row swaps.
GRID_CR_OBJ=$(addprefix build/grid-cr/,$(addsuffix .o,entry owner core validate-bounded suffix font raw-row)) build/geos-prod/grid-geometry-authority.o
build/grid-cr/font-crc.inc: build/overlays/grid80.seo build/overlays/grid60.seo assets/fonts/generated/narrow4.bin assets/fonts/generated/narrow5.bin tools/grid_cr_font_witness.py build/editor.prg
	$(PYTHON) tools/grid_cr_font_witness.py --base $(CURDIR) --output $@
$(filter-out build/geos-prod/grid-geometry-authority.o,$(GRID_CR_OBJ)): build/grid-cr/%.o: src/render/grid/cr/%.s src/render/grid/caret/api.inc src/render/grid/paragraph/long.inc src/fold/source.inc build/geos-prod/editor-api.inc build/grid-cr/font-crc.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I build/grid-cr -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
$(eval $(call GEOS_IMAGE,row,$(GRID_CR_OBJ),cfg/overlay-r.cfg,0,29))
EDITOR_ASSETS += build/overlays/row.seo
editor build/supereditor.d81: build/overlays/row.seo

# C24 incoming-checkpoint ABI witnesses are generated from the linked worker.
build/geos-prod/checkpoint-codec.o: src/render/geos/checkpoint/codec.s src/render/geos/checkpoint/codec.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D GSC_RESTORE_ONLY=1 -I src -I build -o $@ $<
build/geos-prod/checkpoint-witness.stamp: build/overlays/geossema.bin tools/checkpoint_witness.py
	$(PYTHON) tools/checkpoint_witness.py $< build/geos-prod
	touch $@
build/geos-prod/page.o build/geos-prod/navigation.o: build/geos-prod/checkpoint-witness.stamp
build/geos-prod/inline.o: src/render/geos/body-plan/api.inc
build/geos-prod/navigation.o: src/render/geos/navigation.inc
build/geos-prod/page.o: src/render/geos/checkpoint/publish.inc src/render/geos/checkpoint/consumer.inc src/render/geos/checkpoint/codec.inc
build/geos-prod/semantic.o: src/render/geos/checkpoint/seed.inc src/render/geos/checkpoint/codec.inc

# Optional parser-checkpoint retention after a completed GEOS publication.
build/aux-control/checkpoint-refresh.o: src/render/geos/checkpoint/rekey.s build/geos-prod/editor-api.inc src/render/geos/checkpoint/codec.inc
	mkdir -p $(dir $@)
	$(CA65) -g -D GSR_AUX=1 -I build/geos-prod -I src -o $@ $<
build/geos-prod/page.o: src/render/geos/source-certificate.inc
build/geos-prod/checkpoint-outgoing.o: src/render/geos/checkpoint/outgoing.s src/render/geos/checkpoint/codec.inc build/geos-prod/editor-api.inc build/geos-prod/checkpoint-witness.stamp
	mkdir -p $(dir $@)
	$(CA65) -g -I build/geos-prod -I src -o $@ $<
build/geos-prod/source-line.o: src/render/geos/source-certificate.inc src/render/geos/source-certificate.s src/render/geos/certificate-consumer.s src/render/geos/style-window.s
build/geos-prod/source-line.o: src/render/geos/body-plan/api.inc

# Runtime parsing capabilities are independent of the SES64 font ABI.
build/overlays/menu40.o: build/editor-settings/presentation-defaults.inc src/render/presentation.inc
build/overlays/popups.o build/overlays/text40.o build/grid-prod/editor.o build/overlays/layout.o build/layout/dispatch.o build/editor_fold/summary.o build/editor_fold/dispatch.o build/editor/presentation.o build/style-prod/dispatch.o build/style-prod/plan.o build/geos-prod/cache.o build/geos-prod/cache-warm.o build/geos-prod/cache-paint.o: src/render/presentation.inc
build/fold-prod/coordinator.o: src/render/presentation.inc
build/geos-prod/semantic-lex.o build/geos-prod/preview.o: src/render/presentation.inc
build/geos-prod/page.o build/geos-prod/navigation.o: src/render/geos/plain-context.inc src/render/presentation.inc

# Append derived-cache state last; preserve all existing object/doc offsets.
build/cache/state.o: src/cache/state.s src/cache/api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -o $@ -l $(@:.o=.lst) $<

# Cold window operations leave C6 resident for direct hot mutation producers.
build/hot-cold/worker.o: src/hot/cold/worker.s src/hot/api.inc build/editor-api.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I src -I build -o $@ -l $(@:.o=.lst) $<
build/overlays/hotcold.bin: build/hot-cold/worker.o cfg/overlay-r.cfg
	$(LD65) -C cfg/overlay-r.cfg -o $@ -m $(@:.bin=.map) -Ln $(@:.bin=.lbl) $<
build/overlays/hotcold.seo: build/overlays/hotcold.bin tools/overlays.py build/editor-report.json
	$(PYTHON) tools/overlays.py $< $@ --slot 0 --id 32 --resident-report build/editor-report.json
EDITOR_ASSETS += build/overlays/hotcold.seo
editor build/supereditor.d81: build/overlays/hotcold.seo

build/overlays/window.o build/overlays/hot-window.o build/hot-cold/worker.o: src/hot/validate.s src/hot/cold/load.s src/hot/cold/prepare.s
# One checked current-BODY presentation plan replaces the retired baseline,
# inline-query, lexical and rebase capsule families. It retains no new resident
# state and uses the existing R33 identity.
BODY_PLAN_OBJ=build/geos-prod/body-plan-entry.o
build/geos-prod/body-plan-entry.o: src/render/geos/body-plan/entry.s src/render/geos/body-plan/api.inc build/geos-prod/editor-api.inc src/render/geos/semantic.inc src/render/geos/source-line.inc src/render/geos/line.inc src/render/geos/source-certificate.inc src/render/geos/inline.inc src/object/api.inc src/document/math24.inc
	mkdir -p $(dir $@)
	$(CA65) -g -I build/geos-prod -I src -o $@ -l $(@:.o=.lst) $<
$(eval $(call GEOS_IMAGE,fold,$(BODY_PLAN_OBJ),cfg/overlay-r.cfg,0,33))
EDITOR_ASSETS += build/overlays/fold.seo
editor build/supereditor.d81: build/overlays/fold.seo

build/editor/commands.o build/geos-resident/dispatch.o: src/cache/api.inc
build/overlays/menu40.o: src/render/geos/source-line.inc src/render/geos/fold-query.inc src/render/geos/semantic.inc
build/geos-prod/page.o: src/cache/api.inc
build/editor/startup.o: src/editor/catalog.inc

.PHONY: package-force
package-force:
PACKAGE_GUARD = $(PYTHON) tools/cache_job_build.py --project "$(CURDIR)"

# The runtime medium contains only the editor, its real images and fontpack.
# Depend on editor (including its additional per-mode targets), never probes.
.PHONY: runtime-disk
runtime-disk: editor build/geos-font-catalog/font-pack.bin
	$(PACKAGE_GUARD) --package --runtime --c1541 "$(C1541)"

# Complete logical-row C22/R21 paired ABI.
build/geos-prod/row-job.o build/geos-prod/page-paint.o: src/render/geos/row-job.inc
