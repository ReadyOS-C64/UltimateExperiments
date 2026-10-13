# ReadyFS standalone filesystem laboratory
.DEFAULT_GOAL := all

CC = cl65
C1541 = c1541
PYTHON = python3
CLANG ?= clang

SRC_DIR := src
APPS_DIR := $(SRC_DIR)/apps
READYFS_SRC_DIR := $(APPS_DIR)/readyfs
OBJ_DIR := obj
CFG_DIR := cfg
BUILD_SUPPORT_DIR := build_support
READYFS_OUT_DIR := artifacts/readyfs
READYFS_OVERLAY_OBJ_DIR := $(OBJ_DIR)/readyfs_overlay

CFLAGS := -t c64

READYFS := $(READYFS_OUT_DIR)/readyfs.prg
READYFS_D81 := $(READYFS_OUT_DIR)/readyfs-lab.d81
READYFS_OVERLAY := $(READYFS_OUT_DIR)/readyfs-overlay.prg
READYFS_OVERLAY_D81 := $(READYFS_OUT_DIR)/readyfs-overlay-lab.d81
READYFS_MATCH_OVERLAY := $(READYFS_OUT_DIR)/readyfs-match.prg
READYFS_PLAN_OVERLAY := $(READYFS_OUT_DIR)/readyfs-plan.prg
READYFS_HELP_OVERLAY := $(READYFS_OUT_DIR)/readyfs-help.prg
READYFS_BACKEND_OVERLAY := $(READYFS_OUT_DIR)/readyfs-backend.prg
READYFS_CMDPATH_OVERLAY := $(READYFS_OUT_DIR)/readyfs-cmdpath.prg
READYFS_DRIVE_OVERLAY := $(READYFS_OUT_DIR)/readyfs-drive.prg
READYFS_UTILITY_OVERLAY := $(READYFS_OUT_DIR)/readyfs-utility.prg
READYFS_TREE_OVERLAY := $(READYFS_OUT_DIR)/readyfs-tree.prg
READYFS_CONTENT_OVERLAY := $(READYFS_OUT_DIR)/readyfs-content.prg
READYFS_BATCH_OVERLAY := $(READYFS_OUT_DIR)/readyfs-batch.prg
READYFS_RECURSIVE_OVERLAY := $(READYFS_OUT_DIR)/readyfs-recursive.prg
READYFS_TAPE_OVERLAY := $(READYFS_OUT_DIR)/readyfs-tape.prg

READYFS_HELP_DATA := $(READYFS_SRC_DIR)/readyfs_help_data.h

$(READYFS_HELP_DATA): docs/command-help.json $(BUILD_SUPPORT_DIR)/build_readyfs_command_help.py
	$(PYTHON) $(BUILD_SUPPORT_DIR)/build_readyfs_command_help.py

READYFS_MONOLITHIC_SRCS := \
	$(READYFS_SRC_DIR)/readyfs.c \
	$(READYFS_SRC_DIR)/readyfs_path.c \
	$(READYFS_SRC_DIR)/readyfs_match.c \
	$(READYFS_SRC_DIR)/readyfs_driver.c \
	$(READYFS_SRC_DIR)/readyfs_plan.c \
	$(READYFS_SRC_DIR)/readyfs_help.c \
	$(READYFS_SRC_DIR)/readyfs_present.c \
	$(READYFS_SRC_DIR)/readyfs_overlay.c \
	$(READYFS_SRC_DIR)/readyfs_reu.c \
	$(READYFS_SRC_DIR)/readyfs_utility.c \
	$(READYFS_SRC_DIR)/readyfs_commands.c \
	$(READYFS_SRC_DIR)/readyfs_uci.c \
	$(READYFS_SRC_DIR)/readyfs_uci_asm.s \
	$(READYFS_SRC_DIR)/readyfs_reu_overlay_asm.s \
	$(READYFS_SRC_DIR)/readyfs_console.s \
	$(READYFS_SRC_DIR)/readyfs_softname.s

READYFS_OVERLAY_RESIDENT_SRCS := \
	$(READYFS_SRC_DIR)/readyfs.c \
	$(READYFS_SRC_DIR)/readyfs_path.c \
	$(READYFS_SRC_DIR)/readyfs_overlay.c \
	$(READYFS_SRC_DIR)/readyfs_reu.c \
	$(READYFS_SRC_DIR)/readyfs_uci.c
READYFS_OVERLAY_RESIDENT_OBJS := $(patsubst %.c,$(READYFS_OVERLAY_OBJ_DIR)/resident/%.o,$(READYFS_OVERLAY_RESIDENT_SRCS))
READYFS_OVERLAY_MATCH_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay1/$(READYFS_SRC_DIR)/readyfs_match.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay1/$(READYFS_SRC_DIR)/readyfs_match_name.o
READYFS_OVERLAY_PLAN_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay2/$(READYFS_SRC_DIR)/readyfs_plan.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay2/$(READYFS_SRC_DIR)/readyfs_exec.o
READYFS_OVERLAY_HELP_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay3/$(READYFS_SRC_DIR)/readyfs_help.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay3/$(READYFS_SRC_DIR)/readyfs_journal.o
READYFS_OVERLAY_BACKEND_OBJ := $(READYFS_OVERLAY_OBJ_DIR)/overlay4/$(READYFS_SRC_DIR)/readyfs_backend.o
READYFS_OVERLAY_CMDPATH_OBJ := $(READYFS_OVERLAY_OBJ_DIR)/overlay5/$(READYFS_SRC_DIR)/readyfs_cmdpath.o
READYFS_OVERLAY_DRIVE_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay6/$(READYFS_SRC_DIR)/readyfs_driver.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay6/$(READYFS_SRC_DIR)/readyfs_driveui.o
READYFS_OVERLAY_UTILITY_OBJ := $(READYFS_OVERLAY_OBJ_DIR)/overlay7/$(READYFS_SRC_DIR)/readyfs_utility.o
READYFS_OVERLAY_TREE_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay8/$(READYFS_SRC_DIR)/readyfs_tree.o
READYFS_OVERLAY_CONTENT_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay9/$(READYFS_SRC_DIR)/readyfs_content.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay9/$(READYFS_SRC_DIR)/readyfs_content_format.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay9/$(READYFS_SRC_DIR)/readyfs_utility_test.o
READYFS_OVERLAY_UI_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay13/$(READYFS_SRC_DIR)/readyfs_ui.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay13/$(READYFS_SRC_DIR)/readyfs_commands.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay13/$(READYFS_SRC_DIR)/readyfs_ui_overlay_addr.o
READYFS_OVERLAY_BATCH_OBJ := $(READYFS_OVERLAY_OBJ_DIR)/overlay10/$(READYFS_SRC_DIR)/readyfs_batch.o
READYFS_OVERLAY_RECURSIVE_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay11/$(READYFS_SRC_DIR)/readyfs_recursive.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay11/$(READYFS_SRC_DIR)/readyfs_recursive_name.o
READYFS_OVERLAY_TAPE_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay12/$(READYFS_SRC_DIR)/readyfs_tape.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay12/$(READYFS_SRC_DIR)/readyfs_tape_spool.o
READYFS_OVERLAY_ASM_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/resident/$(READYFS_SRC_DIR)/readyfs_uci_asm.o \
	$(READYFS_OVERLAY_OBJ_DIR)/resident/$(READYFS_SRC_DIR)/readyfs_reu_overlay_asm.o \
	$(READYFS_OVERLAY_OBJ_DIR)/resident/$(READYFS_SRC_DIR)/readyfs_softname.o \
	$(READYFS_OVERLAY_OBJ_DIR)/resident/$(READYFS_SRC_DIR)/readyfs_console.o
READYFS_OVERLAY_ADDR_OBJS := \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay1/$(READYFS_SRC_DIR)/readyfs_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay2/$(READYFS_SRC_DIR)/readyfs_plan_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay3/$(READYFS_SRC_DIR)/readyfs_help_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay4/$(READYFS_SRC_DIR)/readyfs_backend_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay5/$(READYFS_SRC_DIR)/readyfs_cmdpath_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay6/$(READYFS_SRC_DIR)/readyfs_drive_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay7/$(READYFS_SRC_DIR)/readyfs_utility_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay8/$(READYFS_SRC_DIR)/readyfs_tree_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay9/$(READYFS_SRC_DIR)/readyfs_content_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay10/$(READYFS_SRC_DIR)/readyfs_batch_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay11/$(READYFS_SRC_DIR)/readyfs_recursive_overlay_addr.o \
	$(READYFS_OVERLAY_OBJ_DIR)/overlay12/$(READYFS_SRC_DIR)/readyfs_tape_overlay_addr.o
READYFS_OVERLAY_PRESENT_OBJS := $(READYFS_OVERLAY_OBJ_DIR)/overlay14/$(READYFS_SRC_DIR)/readyfs_transfer.o $(READYFS_OVERLAY_OBJ_DIR)/overlay14/$(READYFS_SRC_DIR)/readyfs_present.o $(READYFS_OVERLAY_OBJ_DIR)/overlay14/$(READYFS_SRC_DIR)/readyfs_present_overlay_addr.o
READYFS_OVERLAY_ALL_OBJS := $(READYFS_OVERLAY_PRESENT_OBJS) \
	$(READYFS_OVERLAY_RESIDENT_OBJS) $(READYFS_OVERLAY_MATCH_OBJS) \
	$(READYFS_OVERLAY_PLAN_OBJS) $(READYFS_OVERLAY_HELP_OBJS) \
	$(READYFS_OVERLAY_BACKEND_OBJ) $(READYFS_OVERLAY_CMDPATH_OBJ) \
	$(READYFS_OVERLAY_DRIVE_OBJS) $(READYFS_OVERLAY_UTILITY_OBJ) \
	$(READYFS_OVERLAY_TREE_OBJS) $(READYFS_OVERLAY_CONTENT_OBJS) \
	$(READYFS_OVERLAY_BATCH_OBJ) $(READYFS_OVERLAY_RECURSIVE_OBJS) \
	$(READYFS_OVERLAY_TAPE_OBJS) $(READYFS_OVERLAY_UI_OBJS) $(READYFS_OVERLAY_ASM_OBJS) \
	$(READYFS_OVERLAY_ADDR_OBJS)

all: readyfs

$(READYFS): $(READYFS_MONOLITHIC_SRCS) $(READYFS_HELP_DATA)
	@mkdir -p "$(dir $@)" "$(OBJ_DIR)"
	$(CC) $(CFLAGS) -I$(READYFS_SRC_DIR) -Os -DREADYFS_MONOLITHIC=1 \
		-m $(OBJ_DIR)/readyfs.map -o $@ $(filter %.c %.s,$^)

$(READYFS_OVERLAY_OBJ_DIR)/resident/%.o: %.c
	@mkdir -p "$(dir $@)"
	$(CC) -t c64 -Os -I$(READYFS_SRC_DIR) \
		-DREADYFS_OVERLAY_RUNTIME=1 -c -o $@ $<

$(READYFS_OVERLAY_OBJ_DIR)/resident/%.o: %.s
	@mkdir -p "$(dir $@)"
	$(CC) -t c64 -I$(READYFS_SRC_DIR) -c -o $@ $<

define READYFS_OVERLAY_RULE
$(READYFS_OVERLAY_OBJ_DIR)/overlay$(1)/%.o: %.c Makefile
	@mkdir -p "$$(dir $$@)"
	$$(CC) -t c64 -Os -I$$(READYFS_SRC_DIR) $(2) \
		--code-name OVERLAY$(1) --rodata-name OVERLAY$(1)R --bss-name OVERLAY$(1)B \
		-c -o $$@ $$<

$(READYFS_OVERLAY_OBJ_DIR)/overlay$(1)/%.o: %.s
	@mkdir -p "$$(dir $$@)"
	$$(CC) -t c64 -I$$(READYFS_SRC_DIR) -c -o $$@ $$<
endef

$(eval $(call READYFS_OVERLAY_RULE,1,))
$(eval $(call READYFS_OVERLAY_RULE,2,))
$(eval $(call READYFS_OVERLAY_RULE,3,-DREADYFS_FULL_HELP=1))
$(eval $(call READYFS_OVERLAY_RULE,4,-DREADYFS_BACKEND_SIDECAR=1))
$(eval $(call READYFS_OVERLAY_RULE,5,))
$(eval $(call READYFS_OVERLAY_RULE,6,))
$(eval $(call READYFS_OVERLAY_RULE,7,-DREADYFS_UTILITY_SIDECAR=1))
$(eval $(call READYFS_OVERLAY_RULE,8,-DREADYFS_TREE_SIDECAR=1))
$(eval $(call READYFS_OVERLAY_RULE,9,))
$(eval $(call READYFS_OVERLAY_RULE,10,))
$(eval $(call READYFS_OVERLAY_RULE,11,))
$(eval $(call READYFS_OVERLAY_RULE,12,))
$(eval $(call READYFS_OVERLAY_RULE,13,))
$(eval $(call READYFS_OVERLAY_RULE,14,))
$(eval $(call READYFS_OVERLAY_RULE,15,))
$(eval $(call READYFS_OVERLAY_RULE,16,))
$(eval $(call READYFS_OVERLAY_RULE,17,))
$(eval $(call READYFS_OVERLAY_RULE,18,))
$(eval $(call READYFS_OVERLAY_RULE,19,))
$(READYFS_OVERLAY_OBJ_DIR)/overlay15/$(READYFS_SRC_DIR)/readyfs_preview.o $(READYFS_OVERLAY_OBJ_DIR)/overlay15/$(READYFS_SRC_DIR)/readyfs_command_help.o: $(READYFS_HELP_DATA)

READYFS_OVERLAY_ALL_OBJS += $(READYFS_OVERLAY_OBJ_DIR)/overlay19/$(READYFS_SRC_DIR)/readyfs_files.o $(READYFS_OVERLAY_OBJ_DIR)/overlay19/$(READYFS_SRC_DIR)/readyfs_files_overlay_addr.o

READYFS_OVERLAY_ALL_OBJS += $(READYFS_OVERLAY_OBJ_DIR)/overlay17/$(READYFS_SRC_DIR)/readyfs_iec_plan.o $(READYFS_OVERLAY_OBJ_DIR)/overlay17/$(READYFS_SRC_DIR)/readyfs_iec_overlay_addr.o $(READYFS_OVERLAY_OBJ_DIR)/overlay18/$(READYFS_SRC_DIR)/readyfs_iec.o $(READYFS_OVERLAY_OBJ_DIR)/overlay18/$(READYFS_SRC_DIR)/readyfs_media.o $(READYFS_OVERLAY_OBJ_DIR)/overlay18/$(READYFS_SRC_DIR)/readyfs_native_overlay_addr.o

READYFS_OVERLAY_ALL_OBJS += $(READYFS_OVERLAY_OBJ_DIR)/overlay16/$(READYFS_SRC_DIR)/readyfs_stream.o $(READYFS_OVERLAY_OBJ_DIR)/overlay16/$(READYFS_SRC_DIR)/readyfs_files_plan.o $(READYFS_OVERLAY_OBJ_DIR)/overlay16/$(READYFS_SRC_DIR)/readyfs_stream_overlay_addr.o

READYFS_OVERLAY_ALL_OBJS += $(READYFS_OVERLAY_OBJ_DIR)/overlay15/$(READYFS_SRC_DIR)/readyfs_preview.o $(READYFS_OVERLAY_OBJ_DIR)/overlay15/$(READYFS_SRC_DIR)/readyfs_command_help.o $(READYFS_OVERLAY_OBJ_DIR)/overlay15/$(READYFS_SRC_DIR)/readyfs_command_help_overlay_addr.o

$(READYFS_OVERLAY): $(READYFS_OVERLAY_ALL_OBJS) $(CFG_DIR)/readyfs_overlay.cfg
	@mkdir -p "$(dir $@)"
	$(CC) -t c64 -C $(CFG_DIR)/readyfs_overlay.cfg \
		-m $(OBJ_DIR)/readyfs-overlay.map \
		-Ln $(READYFS_OUT_DIR)/readyfs-overlay.lbl -o $@ \
		$(READYFS_OVERLAY_ALL_OBJS)

$(READYFS_OVERLAY_D81): FORCE $(READYFS_OVERLAY)
	@mkdir -p "$(dir $@)"
	$(C1541) -format "readyfs ovl,rf" d81 $@ \
		-write $(READYFS_OVERLAY) readyfs-overlay \
		-write $(READYFS_MATCH_OVERLAY) rfmatch \
		-write $(READYFS_PLAN_OVERLAY) rfplan \
		-write $(READYFS_HELP_OVERLAY) rfhelp \
		-write $(READYFS_BACKEND_OVERLAY) rfbackend \
		-write $(READYFS_CMDPATH_OVERLAY) rfcmdpath \
		-write $(READYFS_DRIVE_OVERLAY) rfdrive \
		-write $(READYFS_UTILITY_OVERLAY) rfutil \
		-write $(READYFS_TREE_OVERLAY) rftree \
		-write $(READYFS_CONTENT_OVERLAY) rfcontent \
		-write $(READYFS_BATCH_OVERLAY) rfbatch \
		-write $(READYFS_RECURSIVE_OVERLAY) rfrecur \
		-write $(READYFS_TAPE_OVERLAY) rftape \
		-write $(READYFS_OUT_DIR)/readyfs-ui.prg rfui \
		-write $(READYFS_OUT_DIR)/readyfs-present.prg rfshow \
		-write $(READYFS_OUT_DIR)/readyfs-command-help.prg rfexamples \
		-write $(READYFS_OUT_DIR)/readyfs-stream.prg rfstream \
		-write $(READYFS_OUT_DIR)/readyfs-iec.prg rfiec \
		-write $(READYFS_OUT_DIR)/readyfs-files.prg rffiles \
		-write $(READYFS_OUT_DIR)/readyfs-native.prg rfnative \
		-write $(BUILD_SUPPORT_DIR)/readyfs_content_view.seq "rfview,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_content_long.seq "rflong,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_batch_ok.seq "rfbok,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_batch_continue.seq "rfbcont,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_batch_stop.seq "rfbstop,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_batch_mismatch.seq "rfbmis,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_batch_nested.seq "rfbnest,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_batch_prompt.seq "rfbprompt,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_batch_guard.seq "rfguard,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_batch_typed.seq "rfbtyped,s" \
		-write $(BUILD_SUPPORT_DIR)/readyfs_ui_ring.seq "rfring,s"

$(READYFS_D81): FORCE $(READYFS)
	@mkdir -p "$(dir $@)"
	$(C1541) -format "readyfs lab,rf" d81 $@ -write $(READYFS) readyfs

readyfs: uci-protocol-check $(READYFS_D81) $(READYFS_OVERLAY_D81) readyfs-host-tests readyfs-build-report

uci-protocol-check:
	$(PYTHON) $(BUILD_SUPPORT_DIR)/verify_readyfs_uci_protocol_contract.py

readyfs-build-report: $(READYFS) $(READYFS_OVERLAY)
	$(PYTHON) $(BUILD_SUPPORT_DIR)/verify_readyfs_overlay_dma.py
	$(PYTHON) $(BUILD_SUPPORT_DIR)/verify_readyfs_pipeline_contract.py
	$(PYTHON) $(BUILD_SUPPORT_DIR)/readyfs_build_report.py

readyfs-ui-report:
	$(PYTHON) $(BUILD_SUPPORT_DIR)/readyfs_ui_report.py
	$(PYTHON) $(BUILD_SUPPORT_DIR)/readyfs_ui_case_report.py

define READYFS_HOST_TEST
	$(CLANG) -std=c99 -Wall -Wextra -pedantic $(1) -I. $(2) -o /tmp/$(3)
	/tmp/$(3)
endef

readyfs-host-tests:
	$(call READYFS_HOST_TEST,-D__fastcall__= -I$(BUILD_SUPPORT_DIR)/readyfs_host_include,$(BUILD_SUPPORT_DIR)/readyfs_iec_test.c $(READYFS_SRC_DIR)/readyfs_iec_plan.c $(READYFS_SRC_DIR)/readyfs_iec.c $(READYFS_SRC_DIR)/readyfs_path.c,readyfs_iec_test)
	$(call READYFS_HOST_TEST,-D__fastcall__= -I$(BUILD_SUPPORT_DIR)/readyfs_host_include,$(BUILD_SUPPORT_DIR)/readyfs_files_test.c $(READYFS_SRC_DIR)/readyfs_files.c $(READYFS_SRC_DIR)/readyfs_files_plan.c,readyfs_files_test)
	$(call READYFS_HOST_TEST,-D__fastcall__= -I$(BUILD_SUPPORT_DIR)/readyfs_host_include,$(BUILD_SUPPORT_DIR)/readyfs_stream_test.c $(READYFS_SRC_DIR)/readyfs_stream.c $(READYFS_SRC_DIR)/readyfs_path.c,readyfs_stream_test)
	$(call READYFS_HOST_TEST,-D__fastcall__= -I$(BUILD_SUPPORT_DIR)/readyfs_host_include,$(BUILD_SUPPORT_DIR)/readyfs_present_test.c $(READYFS_SRC_DIR)/readyfs_present.c $(READYFS_SRC_DIR)/readyfs_media.c $(READYFS_SRC_DIR)/readyfs_transfer.c $(READYFS_SRC_DIR)/readyfs_preview.c $(READYFS_SRC_DIR)/readyfs_command_help.c $(READYFS_SRC_DIR)/readyfs_path.c,readyfs_present_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_tape_test.c $(READYFS_SRC_DIR)/readyfs_tape.c $(READYFS_SRC_DIR)/readyfs_path.c,readyfs_tape_test)
	$(call READYFS_HOST_TEST,-D__fastcall__=,$(BUILD_SUPPORT_DIR)/readyfs_uci_test.c $(READYFS_SRC_DIR)/readyfs_uci.c,readyfs_uci_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_path_test.c $(READYFS_SRC_DIR)/readyfs_path.c $(READYFS_SRC_DIR)/readyfs_match.c,readyfs_path_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_cmdpath_test.c $(READYFS_SRC_DIR)/readyfs_cmdpath.c $(READYFS_SRC_DIR)/readyfs_path.c,readyfs_cmdpath_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_driver_test.c $(READYFS_SRC_DIR)/readyfs_driver.c,readyfs_driver_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_plan_test.c $(READYFS_SRC_DIR)/readyfs_plan.c $(READYFS_SRC_DIR)/readyfs_walk.c $(READYFS_SRC_DIR)/readyfs_exec.c,readyfs_plan_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_tree_test.c $(READYFS_SRC_DIR)/readyfs_tree.c,readyfs_tree_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_commands_test.c $(READYFS_SRC_DIR)/readyfs_commands.c,readyfs_commands_test)
	$(call READYFS_HOST_TEST,-D__fastcall__= -DREADYFS_UI_HOST_TEST -I$(BUILD_SUPPORT_DIR)/readyfs_host_include,$(BUILD_SUPPORT_DIR)/readyfs_ui_test.c $(READYFS_SRC_DIR)/readyfs_ui.c $(READYFS_SRC_DIR)/readyfs_commands.c,readyfs_ui_test)
	$(call READYFS_HOST_TEST,-I$(BUILD_SUPPORT_DIR)/readyfs_host_include,$(BUILD_SUPPORT_DIR)/readyfs_content_test.c $(READYFS_SRC_DIR)/readyfs_content.c,readyfs_content_test)
	$(call READYFS_HOST_TEST,-I$(BUILD_SUPPORT_DIR)/readyfs_host_include,$(BUILD_SUPPORT_DIR)/readyfs_utility_test.c $(READYFS_SRC_DIR)/readyfs_utility.c $(READYFS_SRC_DIR)/readyfs_path.c $(READYFS_SRC_DIR)/readyfs_commands.c,readyfs_utility_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_journal_test.c $(READYFS_SRC_DIR)/readyfs_journal.c,readyfs_journal_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_backend_test.c $(READYFS_SRC_DIR)/readyfs_backend.c $(READYFS_SRC_DIR)/readyfs_path.c,readyfs_backend_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_pipeline_test.c $(READYFS_SRC_DIR)/readyfs_plan.c $(READYFS_SRC_DIR)/readyfs_exec.c $(READYFS_SRC_DIR)/readyfs_backend.c $(READYFS_SRC_DIR)/readyfs_path.c $(READYFS_SRC_DIR)/readyfs_journal.c,readyfs_pipeline_test)
	$(call READYFS_HOST_TEST,,$(BUILD_SUPPORT_DIR)/readyfs_recursive_test.c $(READYFS_SRC_DIR)/readyfs_recursive.c $(READYFS_SRC_DIR)/readyfs_plan.c $(READYFS_SRC_DIR)/readyfs_exec.c $(READYFS_SRC_DIR)/readyfs_backend.c $(READYFS_SRC_DIR)/readyfs_path.c $(READYFS_SRC_DIR)/readyfs_journal.c,readyfs_recursive_test)
	$(PYTHON) $(BUILD_SUPPORT_DIR)/readyfs_journal_report.py --self-test
	$(PYTHON) $(BUILD_SUPPORT_DIR)/readyfs_action_report.py --self-test

readyfs-vice-smoke: readyfs
	/bin/bash $(BUILD_SUPPORT_DIR)/run_readyfs_vice_smoke.sh

clean:
	rm -rf $(READYFS_OVERLAY_OBJ_DIR) $(OBJ_DIR)/readyfs.map $(OBJ_DIR)/readyfs-overlay.map
	rm -f $(READYFS_OUT_DIR)/readyfs*.prg $(READYFS_OUT_DIR)/readyfs*.lbl
	rm -f $(READYFS_D81) $(READYFS_OVERLAY_D81)

help:
	@echo "ReadyFS standalone targets:"
	@echo "  readyfs              Build PRGs/D81s and run contracts + host tests"
	@echo "  readyfs-host-tests   Run host-side unit and pipeline tests"
	@echo "  readyfs-build-report Validate maps, sidecars, and REU layout"
	@echo "  readyfs-ui-report    Summarize migrated VICE evidence"
	@echo "  readyfs-vice-smoke   Rebuild and run the VICE smoke plan"

FORCE:

.PHONY: all readyfs uci-protocol-check readyfs-build-report readyfs-ui-report \
	readyfs-host-tests readyfs-vice-smoke clean help FORCE

# Slot19 includes the pure identity classifier without loading slot6.
$(READYFS_OVERLAY_OBJ_DIR)/overlay19/$(READYFS_SRC_DIR)/readyfs_files.o: $(READYFS_SRC_DIR)/readyfs_driver.c
