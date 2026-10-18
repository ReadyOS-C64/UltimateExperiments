RSQL_CC65 ?= /opt/homebrew/bin/cl65
RSQL_CC ?= /opt/homebrew/bin/cc65
RSQL_CA65 ?= /opt/homebrew/bin/ca65
RSQL_ZIG ?= ../../zig64tooling/bin/zig
RSQL_VICE ?= /opt/homebrew/bin/x64sc
RSQL_DOTNET ?= /usr/local/share/dotnet/dotnet
RSQL_VICE_TASKS ?= ../../agenticdevharness/tools/vice_tasks_dotnet/src/ViceTasks.Binary/ViceTasks.Binary.csproj
RSQL_C1541 ?= /opt/homebrew/bin/c1541

BUILD := build
OBJ := $(BUILD)/obj
TARGET := $(BUILD)/rsql64.prg
QUERY_TARGET := $(BUILD)/rsql64_query.prg
AGG_TARGET := $(BUILD)/rsql64_aggregate.prg
VARIABLE_TARGET := $(BUILD)/rsql64_variable.prg
VARUPDATE_TARGET := $(BUILD)/rsql64_varupdate.prg
JOIN_TARGET := $(BUILD)/rsql64_join.prg
NESTED_TARGET := $(BUILD)/rsql64_nested.prg
WIDE_TARGET := $(BUILD)/rsql64_wide.prg
WIDE_SCALAR_TARGET := $(BUILD)/rsql64_wide_scalar.prg
JOINAGG_TARGET := $(BUILD)/rsql64_joinagg.prg
RESULT_TARGET := $(BUILD)/rsql64_result.prg
CTAS_TARGET := $(BUILD)/rsql64_ctas.prg
FIXEDAGG_TARGET := $(BUILD)/rsql64_fixedagg.prg
CHECKPOINT_TARGET := $(BUILD)/rsql64_checkpoint.prg
SHELL_TARGET := $(BUILD)/rsql64_shell.prg
BENCHMARK_TARGET := $(BUILD)/rsql64_benchmark.prg
PIPELINE_TARGET := $(BUILD)/rsql64_pipeline_benchmark.prg
DISK := $(BUILD)/rsql64.d81
QUERY_DISK := $(BUILD)/rsql64_query.d81
AGG_DISK := $(BUILD)/rsql64_aggregate.d81
VARIABLE_DISK := $(BUILD)/rsql64_variable.d81
VARUPDATE_DISK := $(BUILD)/rsql64_varupdate.d81
JOIN_DISK := $(BUILD)/rsql64_join.d81
NESTED_DISK := $(BUILD)/rsql64_nested.d81
JOINAGG_DISK := $(BUILD)/rsql64_joinagg.d81
RESULT_DISK := $(BUILD)/rsql64_result.d81
CTAS_DISK := $(BUILD)/rsql64_ctas.d81
FIXEDAGG_DISK := $(BUILD)/rsql64_fixedagg.d81
CHECKPOINT_DISK := $(BUILD)/rsql64_checkpoint.d81
SHELL_DISK := $(BUILD)/rsql64_shell.d81
WIDE_DISK := $(BUILD)/rsql64_wide.d81
WIDE_SCALAR_DISK := $(BUILD)/rsql64_wide_scalar.d81
BENCHMARK_DISK := $(BUILD)/rsql64_benchmark.d81
PIPELINE_DISK := $(BUILD)/rsql64_pipeline_benchmark.d81
OVL_DIR := $(BUILD)/overlays
OVL_META := $(OVL_DIR)/rsqlmeta.prg
OVL_ROW := $(OVL_DIR)/rsqlrow.prg
OVL_PARSE := $(OVL_DIR)/rsqlparse.prg
OVL_EXEC := $(OVL_DIR)/rsqlexec.prg
OVL_QUERY := $(OVL_DIR)/rsqlsubq.prg
OVL_SORT := $(OVL_DIR)/rsqlsort.prg
OVL_JAGG := $(OVL_DIR)/rsqljagg.prg
OVL_ADMIN := $(OVL_DIR)/rsqladmin.prg
OVERLAY_PRGS := $(OVL_META) $(OVL_ROW) $(OVL_PARSE) $(OVL_EXEC) $(OVL_QUERY) $(OVL_SORT) $(OVL_JAGG) $(OVL_ADMIN) $(OVL_DIR)/rsqlwide.prg
QUERY_OVL_DIR := $(BUILD)/query_overlays
QUERY_OVL_META := $(QUERY_OVL_DIR)/rsqlmeta.prg
QUERY_OVL_ROW := $(QUERY_OVL_DIR)/rsqlrow.prg
QUERY_OVL_PARSE := $(QUERY_OVL_DIR)/rsqlparse.prg
QUERY_OVL_EXEC := $(QUERY_OVL_DIR)/rsqlexec.prg
QUERY_OVL_QUERY := $(QUERY_OVL_DIR)/rsqlsubq.prg
QUERY_OVL_SORT := $(QUERY_OVL_DIR)/rsqlsort.prg
QUERY_OVL_JAGG := $(QUERY_OVL_DIR)/rsqljagg.prg
QUERY_OVL_ADMIN := $(QUERY_OVL_DIR)/rsqladmin.prg
QUERY_OVERLAY_PRGS := $(QUERY_OVL_META) $(QUERY_OVL_ROW) $(QUERY_OVL_PARSE) $(QUERY_OVL_EXEC) $(QUERY_OVL_QUERY) $(QUERY_OVL_SORT) $(QUERY_OVL_JAGG) $(QUERY_OVL_ADMIN) $(QUERY_OVL_DIR)/rsqlwide.prg
AGG_OVL_DIR := $(BUILD)/aggregate_overlays
AGG_OVL_META := $(AGG_OVL_DIR)/rsqlmeta.prg
AGG_OVL_ROW := $(AGG_OVL_DIR)/rsqlrow.prg
AGG_OVL_PARSE := $(AGG_OVL_DIR)/rsqlparse.prg
AGG_OVL_EXEC := $(AGG_OVL_DIR)/rsqlexec.prg
AGG_OVL_QUERY := $(AGG_OVL_DIR)/rsqlsubq.prg
AGG_OVL_SORT := $(AGG_OVL_DIR)/rsqlsort.prg
AGG_OVL_JAGG := $(AGG_OVL_DIR)/rsqljagg.prg
AGG_OVL_ADMIN := $(AGG_OVL_DIR)/rsqladmin.prg
AGG_OVERLAY_PRGS := $(AGG_OVL_META) $(AGG_OVL_ROW) $(AGG_OVL_PARSE) $(AGG_OVL_EXEC) $(AGG_OVL_QUERY) $(AGG_OVL_SORT) $(AGG_OVL_JAGG) $(AGG_OVL_ADMIN) $(AGG_OVL_DIR)/rsqlwide.prg
VARIABLE_OVL_DIR := $(BUILD)/variable_overlays
VARIABLE_OVL_META := $(VARIABLE_OVL_DIR)/rsqlmeta.prg
VARIABLE_OVL_ROW := $(VARIABLE_OVL_DIR)/rsqlrow.prg
VARIABLE_OVL_PARSE := $(VARIABLE_OVL_DIR)/rsqlparse.prg
VARIABLE_OVL_EXEC := $(VARIABLE_OVL_DIR)/rsqlexec.prg
VARIABLE_OVL_QUERY := $(VARIABLE_OVL_DIR)/rsqlsubq.prg
VARIABLE_OVL_SORT := $(VARIABLE_OVL_DIR)/rsqlsort.prg
VARIABLE_OVL_JAGG := $(VARIABLE_OVL_DIR)/rsqljagg.prg
VARIABLE_OVL_ADMIN := $(VARIABLE_OVL_DIR)/rsqladmin.prg
VARIABLE_OVERLAY_PRGS := $(VARIABLE_OVL_META) $(VARIABLE_OVL_ROW) $(VARIABLE_OVL_PARSE) $(VARIABLE_OVL_EXEC) $(VARIABLE_OVL_QUERY) $(VARIABLE_OVL_SORT) $(VARIABLE_OVL_JAGG) $(VARIABLE_OVL_ADMIN) $(VARIABLE_OVL_DIR)/rsqlwide.prg
VARUPDATE_OVL_DIR := $(BUILD)/varupdate_overlays
VARUPDATE_OVL_META := $(VARUPDATE_OVL_DIR)/rsqlmeta.prg
VARUPDATE_OVL_ROW := $(VARUPDATE_OVL_DIR)/rsqlrow.prg
VARUPDATE_OVL_PARSE := $(VARUPDATE_OVL_DIR)/rsqlparse.prg
VARUPDATE_OVL_EXEC := $(VARUPDATE_OVL_DIR)/rsqlexec.prg
VARUPDATE_OVL_QUERY := $(VARUPDATE_OVL_DIR)/rsqlsubq.prg
VARUPDATE_OVL_SORT := $(VARUPDATE_OVL_DIR)/rsqlsort.prg
VARUPDATE_OVL_JAGG := $(VARUPDATE_OVL_DIR)/rsqljagg.prg
VARUPDATE_OVL_ADMIN := $(VARUPDATE_OVL_DIR)/rsqladmin.prg
VARUPDATE_OVERLAY_PRGS := $(VARUPDATE_OVL_META) $(VARUPDATE_OVL_ROW) $(VARUPDATE_OVL_PARSE) $(VARUPDATE_OVL_EXEC) $(VARUPDATE_OVL_QUERY) $(VARUPDATE_OVL_SORT) $(VARUPDATE_OVL_JAGG) $(VARUPDATE_OVL_ADMIN) $(VARUPDATE_OVL_DIR)/rsqlwide.prg
JOIN_OVL_DIR := $(BUILD)/join_overlays
JOIN_OVL_META := $(JOIN_OVL_DIR)/rsqlmeta.prg
JOIN_OVL_ROW := $(JOIN_OVL_DIR)/rsqlrow.prg
JOIN_OVL_PARSE := $(JOIN_OVL_DIR)/rsqlparse.prg
JOIN_OVL_EXEC := $(JOIN_OVL_DIR)/rsqlexec.prg
JOIN_OVL_QUERY := $(JOIN_OVL_DIR)/rsqlsubq.prg
JOIN_OVL_SORT := $(JOIN_OVL_DIR)/rsqlsort.prg
JOIN_OVL_JAGG := $(JOIN_OVL_DIR)/rsqljagg.prg
JOIN_OVL_ADMIN := $(JOIN_OVL_DIR)/rsqladmin.prg
JOIN_OVERLAY_PRGS := $(JOIN_OVL_META) $(JOIN_OVL_ROW) $(JOIN_OVL_PARSE) $(JOIN_OVL_EXEC) $(JOIN_OVL_QUERY) $(JOIN_OVL_SORT) $(JOIN_OVL_JAGG) $(JOIN_OVL_ADMIN) $(JOIN_OVL_DIR)/rsqlwide.prg
NESTED_OVL_DIR := $(BUILD)/nested_overlays
NESTED_OVERLAY_PRGS := $(addprefix $(NESTED_OVL_DIR)/,rsqlmeta.prg rsqlrow.prg rsqlparse.prg rsqlexec.prg rsqlsubq.prg rsqlsort.prg rsqljagg.prg rsqladmin.prg rsqlwide.prg)
NESTED_CFG := $(BUILD)/reusql64_nested.cfg
JOINAGG_OVL_DIR := $(BUILD)/joinagg_overlays
JOINAGG_OVL_META := $(JOINAGG_OVL_DIR)/rsqlmeta.prg
JOINAGG_OVL_ROW := $(JOINAGG_OVL_DIR)/rsqlrow.prg
JOINAGG_OVL_PARSE := $(JOINAGG_OVL_DIR)/rsqlparse.prg
JOINAGG_OVL_EXEC := $(JOINAGG_OVL_DIR)/rsqlexec.prg
JOINAGG_OVL_QUERY := $(JOINAGG_OVL_DIR)/rsqlsubq.prg
JOINAGG_OVL_SORT := $(JOINAGG_OVL_DIR)/rsqlsort.prg
JOINAGG_OVL_JAGG := $(JOINAGG_OVL_DIR)/rsqljagg.prg
JOINAGG_OVL_ADMIN := $(JOINAGG_OVL_DIR)/rsqladmin.prg
JOINAGG_OVERLAY_PRGS := $(JOINAGG_OVL_META) $(JOINAGG_OVL_ROW) $(JOINAGG_OVL_PARSE) $(JOINAGG_OVL_EXEC) $(JOINAGG_OVL_QUERY) $(JOINAGG_OVL_SORT) $(JOINAGG_OVL_JAGG) $(JOINAGG_OVL_ADMIN) $(JOINAGG_OVL_DIR)/rsqlwide.prg
RESULT_OVL_DIR := $(BUILD)/result_overlays
RESULT_OVL_META := $(RESULT_OVL_DIR)/rsqlmeta.prg
RESULT_OVL_ROW := $(RESULT_OVL_DIR)/rsqlrow.prg
RESULT_OVL_PARSE := $(RESULT_OVL_DIR)/rsqlparse.prg
RESULT_OVL_EXEC := $(RESULT_OVL_DIR)/rsqlexec.prg
RESULT_OVL_QUERY := $(RESULT_OVL_DIR)/rsqlsubq.prg
RESULT_OVL_SORT := $(RESULT_OVL_DIR)/rsqlsort.prg
RESULT_OVL_JAGG := $(RESULT_OVL_DIR)/rsqljagg.prg
RESULT_OVL_ADMIN := $(RESULT_OVL_DIR)/rsqladmin.prg
RESULT_OVERLAY_PRGS := $(RESULT_OVL_META) $(RESULT_OVL_ROW) $(RESULT_OVL_PARSE) $(RESULT_OVL_EXEC) $(RESULT_OVL_QUERY) $(RESULT_OVL_SORT) $(RESULT_OVL_JAGG) $(RESULT_OVL_ADMIN) $(RESULT_OVL_DIR)/rsqlwide.prg
CTAS_OVL_DIR := $(BUILD)/ctas_overlays
CTAS_OVL_META := $(CTAS_OVL_DIR)/rsqlmeta.prg
CTAS_OVL_ROW := $(CTAS_OVL_DIR)/rsqlrow.prg
CTAS_OVL_PARSE := $(CTAS_OVL_DIR)/rsqlparse.prg
CTAS_OVL_EXEC := $(CTAS_OVL_DIR)/rsqlexec.prg
CTAS_OVL_QUERY := $(CTAS_OVL_DIR)/rsqlsubq.prg
CTAS_OVL_SORT := $(CTAS_OVL_DIR)/rsqlsort.prg
CTAS_OVL_JAGG := $(CTAS_OVL_DIR)/rsqljagg.prg
CTAS_OVL_ADMIN := $(CTAS_OVL_DIR)/rsqladmin.prg
CTAS_OVERLAY_PRGS := $(CTAS_OVL_META) $(CTAS_OVL_ROW) $(CTAS_OVL_PARSE) $(CTAS_OVL_EXEC) $(CTAS_OVL_QUERY) $(CTAS_OVL_SORT) $(CTAS_OVL_JAGG) $(CTAS_OVL_ADMIN) $(CTAS_OVL_DIR)/rsqlwide.prg
FIXEDAGG_OVL_DIR := $(BUILD)/fixedagg_overlays
FIXEDAGG_OVL_META := $(FIXEDAGG_OVL_DIR)/rsqlmeta.prg
FIXEDAGG_OVL_ROW := $(FIXEDAGG_OVL_DIR)/rsqlrow.prg
FIXEDAGG_OVL_PARSE := $(FIXEDAGG_OVL_DIR)/rsqlparse.prg
FIXEDAGG_OVL_EXEC := $(FIXEDAGG_OVL_DIR)/rsqlexec.prg
FIXEDAGG_OVL_QUERY := $(FIXEDAGG_OVL_DIR)/rsqlsubq.prg
FIXEDAGG_OVL_SORT := $(FIXEDAGG_OVL_DIR)/rsqlsort.prg
FIXEDAGG_OVL_JAGG := $(FIXEDAGG_OVL_DIR)/rsqljagg.prg
FIXEDAGG_OVL_ADMIN := $(FIXEDAGG_OVL_DIR)/rsqladmin.prg
FIXEDAGG_OVERLAY_PRGS := $(FIXEDAGG_OVL_META) $(FIXEDAGG_OVL_ROW) $(FIXEDAGG_OVL_PARSE) $(FIXEDAGG_OVL_EXEC) $(FIXEDAGG_OVL_QUERY) $(FIXEDAGG_OVL_SORT) $(FIXEDAGG_OVL_JAGG) $(FIXEDAGG_OVL_ADMIN) $(FIXEDAGG_OVL_DIR)/rsqlwide.prg
CHECKPOINT_OVL_DIR := $(BUILD)/checkpoint_overlays
CHECKPOINT_OVL_META := $(CHECKPOINT_OVL_DIR)/rsqlmeta.prg
CHECKPOINT_OVL_ROW := $(CHECKPOINT_OVL_DIR)/rsqlrow.prg
CHECKPOINT_OVL_PARSE := $(CHECKPOINT_OVL_DIR)/rsqlparse.prg
CHECKPOINT_OVL_EXEC := $(CHECKPOINT_OVL_DIR)/rsqlexec.prg
CHECKPOINT_OVL_QUERY := $(CHECKPOINT_OVL_DIR)/rsqlsubq.prg
CHECKPOINT_OVL_SORT := $(CHECKPOINT_OVL_DIR)/rsqlsort.prg
CHECKPOINT_OVL_JAGG := $(CHECKPOINT_OVL_DIR)/rsqljagg.prg
CHECKPOINT_OVL_ADMIN := $(CHECKPOINT_OVL_DIR)/rsqladmin.prg
CHECKPOINT_OVERLAY_PRGS := $(CHECKPOINT_OVL_META) $(CHECKPOINT_OVL_ROW) $(CHECKPOINT_OVL_PARSE) $(CHECKPOINT_OVL_EXEC) $(CHECKPOINT_OVL_QUERY) $(CHECKPOINT_OVL_SORT) $(CHECKPOINT_OVL_JAGG) $(CHECKPOINT_OVL_ADMIN) $(CHECKPOINT_OVL_DIR)/rsqlwide.prg
SHELL_OVL_DIR := $(BUILD)/shell_overlays
SHELL_OVL_META := $(SHELL_OVL_DIR)/rsqlmeta.prg
SHELL_OVL_ROW := $(SHELL_OVL_DIR)/rsqlrow.prg
SHELL_OVL_PARSE := $(SHELL_OVL_DIR)/rsqlparse.prg
SHELL_OVL_EXEC := $(SHELL_OVL_DIR)/rsqlexec.prg
SHELL_OVL_QUERY := $(SHELL_OVL_DIR)/rsqlsubq.prg
SHELL_OVL_SORT := $(SHELL_OVL_DIR)/rsqlsort.prg
SHELL_OVL_JAGG := $(SHELL_OVL_DIR)/rsqljagg.prg
SHELL_OVL_ADMIN := $(SHELL_OVL_DIR)/rsqladmin.prg
SHELL_OVERLAY_PRGS := $(SHELL_OVL_META) $(SHELL_OVL_ROW) $(SHELL_OVL_PARSE) $(SHELL_OVL_EXEC) $(SHELL_OVL_QUERY) $(SHELL_OVL_SORT) $(SHELL_OVL_JAGG) $(SHELL_OVL_ADMIN) $(SHELL_OVL_DIR)/rsqlwide.prg
WIDE_OVL_DIR := $(BUILD)/wide_overlays
WIDE_OVERLAY_PRGS := $(addprefix $(WIDE_OVL_DIR)/,rsqlmeta.prg rsqlrow.prg rsqlparse.prg rsqlexec.prg rsqlsubq.prg rsqlsort.prg rsqljagg.prg rsqladmin.prg rsqlwide.prg)
WIDE_SCALAR_OVL_DIR := $(BUILD)/wide_scalar_overlays
WIDE_SCALAR_OVERLAY_PRGS := $(addprefix $(WIDE_SCALAR_OVL_DIR)/,rsqlmeta.prg rsqlrow.prg rsqlparse.prg rsqlexec.prg rsqlsubq.prg rsqlsort.prg rsqljagg.prg rsqladmin.prg rsqlwide.prg)
WIDE_SCALAR_CFG := $(BUILD)/reusql64_wide_scalar.cfg
BENCHMARK_OVL_DIR := $(BUILD)/benchmark_overlays
BENCHMARK_OVERLAY_PRGS := $(addprefix $(BENCHMARK_OVL_DIR)/,rsqlmeta.prg rsqlrow.prg rsqlparse.prg rsqlexec.prg rsqlsubq.prg rsqlsort.prg rsqljagg.prg rsqladmin.prg rsqlwide.prg)
BENCHMARK_CFG := $(BUILD)/reusql64_benchmark.cfg
PIPELINE_OVL_DIR := $(BUILD)/pipeline_benchmark_overlays
PIPELINE_OVERLAY_PRGS := $(addprefix $(PIPELINE_OVL_DIR)/,rsqlmeta.prg rsqlrow.prg rsqlparse.prg rsqlexec.prg rsqlsubq.prg rsqlsort.prg rsqljagg.prg rsqladmin.prg rsqlwide.prg)
PIPELINE_CFG := $(BUILD)/reusql64_pipeline_benchmark.cfg

APP_C := src/main.c
QUERY_APP_C := src/query_main.c
AGG_APP_C := src/aggregate_main.c
VARIABLE_APP_C := src/variable_main.c
VARUPDATE_APP_C := src/variable_update_main.c
JOIN_APP_C := src/join_main.c
NESTED_APP_C := src/nested_main.c
WIDE_APP_C := src/wide_join_main.c
WIDE_SCALAR_APP_C := src/wide_scalar_main.c
JOINAGG_APP_C := src/join_aggregate_main.c
RESULT_APP_C := src/result_main.c
CTAS_APP_C := src/ctas_main.c
FIXEDAGG_APP_C := src/fixed_aggregate_main.c
CHECKPOINT_APP_C := src/checkpoint_main.c src/export_d81.c
SHELL_APP_C := src/shell_main.c src/rsql_shell.c src/export_d81.c
BENCHMARK_APP_C := src/benchmark_main.c
PIPELINE_APP_C := src/pipeline_benchmark_main.c
ENGINE_C := src/api.c src/query_api.c src/query_create.c src/query_index.c src/reu.c src/page.c src/overlay.c src/storage_layout.c
ABI_C := src/query_enum.c src/query_blob.c src/query_float.c
META_C := src/types.c src/catalog.c src/blob.c src/enum.c src/query_bind.c
ROW_C := src/row.c src/query_cursor.c
ROW_ASM := src/aggregate_index.s
PARSE_C := src/query_parse.c
EXEC_C := src/query_exec.c src/index.c src/blob_write.c src/table_drop.c src/scalar_shape.c
EXEC_ASM := src/scalar_shape_byte.s
QUERYX_C := src/join.c
SORT_C := src/order.c src/blob_compact.c
JAGG_C := src/join_aggregate.c src/variable_predicate.c
JAGG_ASM := src/join_aggregate_entry.s
ADMIN_C := src/inspect.c src/wide_scalar_compare.c src/wide_bind.c \
	src/nested_bind.c
WIDE_C := src/wide_join.c src/wide_scalar_dispatch.c \
	src/query_result_schema.c
WIDE_ASM := src/wide_join_entry.s src/wide_scalar_compare_entry.s
ASM := src/overlay_headers.s src/blob_compact_entry.s src/result_entry.s \
	src/variable_compare_bridge.s src/scalar_source_query.s src/overlay_admin.s
QUERYX_ASM := src/join_entry.s src/scalar_concat.s src/shape_compare_entry.s \
	src/nested_subquery.s
PHASE_ENTRY_ASM := src/result_phase_entry.s

APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(APP_C))
QUERY_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(QUERY_APP_C))
AGG_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(AGG_APP_C))
VARIABLE_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(VARIABLE_APP_C))
VARUPDATE_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(VARUPDATE_APP_C))
JOIN_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(JOIN_APP_C))
NESTED_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(NESTED_APP_C))
WIDE_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(WIDE_APP_C))
WIDE_SCALAR_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(WIDE_SCALAR_APP_C))
JOINAGG_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(JOINAGG_APP_C))
RESULT_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(RESULT_APP_C))
CTAS_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(CTAS_APP_C))
FIXEDAGG_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(FIXEDAGG_APP_C))
CHECKPOINT_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(CHECKPOINT_APP_C))
SHELL_APP_O := $(patsubst src/%.c,$(OBJ)/shell/%.o,$(SHELL_APP_C))
BENCHMARK_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(BENCHMARK_APP_C))
PIPELINE_APP_O := $(patsubst src/%.c,$(OBJ)/app/%.o,$(PIPELINE_APP_C))
ENGINE_O := $(patsubst src/%.c,$(OBJ)/engine/%.o,$(ENGINE_C))
ABI_JUMP_O := $(OBJ)/asm/abi.o
ABI_C_O := $(ABI_JUMP_O) $(patsubst src/%.c,$(OBJ)/abi/%.o,$(ABI_C))
META_O := $(patsubst src/%.c,$(OBJ)/meta/%.o,$(META_C))
ROW_O := $(patsubst src/%.c,$(OBJ)/row/%.o,$(ROW_C)) \
	$(patsubst src/%.s,$(OBJ)/rowasm/%.o,$(ROW_ASM))
PARSE_O := $(patsubst src/%.c,$(OBJ)/parse/%.o,$(PARSE_C))
EXEC_O := $(patsubst src/%.c,$(OBJ)/exec/%.o,$(EXEC_C)) \
	$(patsubst src/%.s,$(OBJ)/execasm/%.o,$(EXEC_ASM))
QUERYX_O := $(patsubst src/%.c,$(OBJ)/queryx/%.o,$(QUERYX_C))
SORT_O := $(patsubst src/%.c,$(OBJ)/sort/%.o,$(SORT_C))
JAGG_O := $(patsubst src/%.c,$(OBJ)/jagg/%.o,$(JAGG_C)) \
	$(OBJ)/jagg/join_core.o \
	$(patsubst src/%.s,$(OBJ)/jaggasm/%.o,$(JAGG_ASM))
ADMIN_O := $(patsubst src/%.c,$(OBJ)/admin/%.o,$(ADMIN_C))
WIDE_O := $(patsubst src/%.c,$(OBJ)/wide/%.o,$(WIDE_C)) \
	$(patsubst src/%.s,$(OBJ)/wideasm/%.o,$(WIDE_ASM))
ASM_O := $(patsubst src/%.s,$(OBJ)/asm/%.o,$(ASM))
QUERYX_ASM_O := $(patsubst src/%.s,$(OBJ)/queryxasm/%.o,$(QUERYX_ASM))
PHASE_ENTRY_O := $(patsubst src/%.s,$(OBJ)/phaseentry/%.o,$(PHASE_ENTRY_ASM))
DEPS := $(APP_O:.o=.d) $(QUERY_APP_O:.o=.d) $(AGG_APP_O:.o=.d) \
	$(VARIABLE_APP_O:.o=.d) $(VARUPDATE_APP_O:.o=.d) \
	$(JOIN_APP_O:.o=.d) $(NESTED_APP_O:.o=.d) $(WIDE_APP_O:.o=.d) $(WIDE_SCALAR_APP_O:.o=.d) $(JOINAGG_APP_O:.o=.d) $(RESULT_APP_O:.o=.d) \
	$(CTAS_APP_O:.o=.d) $(FIXEDAGG_APP_O:.o=.d) $(CHECKPOINT_APP_O:.o=.d) \
	$(SHELL_APP_O:.o=.d) \
	$(BENCHMARK_APP_O:.o=.d) \
	$(PIPELINE_APP_O:.o=.d) \
	$(ENGINE_O:.o=.d) $(ABI_C_O:.o=.d) $(META_O:.o=.d) $(ROW_O:.o=.d) \
	$(PARSE_O:.o=.d) $(EXEC_O:.o=.d) $(QUERYX_O:.o=.d) $(SORT_O:.o=.d) \
	$(JAGG_O:.o=.d) $(ADMIN_O:.o=.d) $(WIDE_O:.o=.d)

CFLAGS := -t c64 -Oirs -I include
APP_FLAGS := --bss-name APPBSS
ENGINE_FLAGS := --code-name ENGINE --rodata-name ENGINE --data-name ENGINEDATA --bss-name BSS
META_FLAGS := --code-name OVERLAY0 --rodata-name OVERLAY0 --data-name ENGINEDATA --bss-name BSS
ROW_FLAGS := --code-name OVERLAY1 --rodata-name OVERLAY1 --data-name ENGINEDATA --bss-name BSS
PARSE_FLAGS := --code-name OVERLAY2 --rodata-name OVERLAY2 --data-name ENGINEDATA --bss-name BSS
EXEC_FLAGS := --code-name OVERLAY3 --rodata-name OVERLAY3 --data-name ENGINEDATA --bss-name BSS
QUERYX_FLAGS := --code-name OVERLAY4 --rodata-name OVERLAY4 --data-name ENGINEDATA --bss-name BSS
SORT_FLAGS := --code-name OVERLAY5 --rodata-name OVERLAY5 --data-name ENGINEDATA --bss-name BSS
JAGG_FLAGS := --code-name OVERLAY6 --rodata-name OVERLAY6 --data-name ENGINEDATA --bss-name BSS
ADMIN_FLAGS := --code-name OVERLAY7 --rodata-name OVERLAY7 --data-name ENGINEDATA --bss-name BSS
WIDE_FLAGS := --code-name OVERLAY8 --rodata-name OVERLAY8 --data-name ENGINEDATA --bss-name BSS
ABI_C_FLAGS := --code-name ABI --rodata-name ABI --data-name ENGINEDATA --bss-name BSS

.PHONY: all clean tools test emu-test emu-aggregate-test emu-fixedagg-test emu-checkpoint-test emu-shell-test emu-benchmark-test emu-pipeline-benchmark-test emu-variable-test emu-result-test emu-ctas-test emu-varupdate-test emu-wide-test emu-wide-scalar-test emu-nested-test vice-test vice-benchmark-test vice-pipeline-benchmark-test pipeline-benchmark-memory-report memory-report run-vice

all: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(NESTED_TARGET) $(WIDE_TARGET) $(WIDE_SCALAR_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(FIXEDAGG_TARGET) $(CHECKPOINT_TARGET) $(SHELL_TARGET) $(BENCHMARK_TARGET) memory-report

tools:
	@test -x "$(RSQL_CC65)" || { echo "missing cc65: $(RSQL_CC65)"; exit 1; }
	@test -x "$(RSQL_ZIG)" || { echo "missing Zig: $(RSQL_ZIG)"; exit 1; }
	@test -x "$(RSQL_VICE)" || { echo "missing VICE: $(RSQL_VICE)"; exit 1; }
	@test -x "$(RSQL_DOTNET)" || { echo "missing .NET: $(RSQL_DOTNET)"; exit 1; }
	@test -f "$(RSQL_VICE_TASKS)" || { echo "missing .NET VICE harness: $(RSQL_VICE_TASKS)"; exit 1; }
	@test -x "$(RSQL_C1541)" || { echo "missing c1541: $(RSQL_C1541)"; exit 1; }
	@echo "cc65=$(RSQL_CC65)"
	@echo "zig=$(RSQL_ZIG)"
	@echo "vice=$(RSQL_VICE)"
	@echo "dotnet=$(RSQL_DOTNET)"
	@echo "c1541=$(RSQL_C1541)"

# cc65 2.19 crashes in its optimizer on the deliberately broad wide-query
# regression client's aggregate/group assertion graph.  This client still
# ends below $2800 without optimization, preserving more than 2KB of its
# reserved application region; engine and sidecar optimization are unchanged.
$(OBJ)/app/wide_join_main.s: src/wide_join_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -I include $(APP_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# The benchmark client combines a bulk fixture builder with two broad result
# assertion graphs; cc65 2.19's inline optimizer crashes on that combination.
$(OBJ)/app/benchmark_main.s: src/benchmark_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -I include $(APP_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# The staged benchmark has the same broad assertion graph as the monolithic
# benchmark and is kept unoptimized for the same cc65 2.19 compiler limitation.
$(OBJ)/app/pipeline_benchmark_main.s: src/pipeline_benchmark_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -I include $(APP_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

$(OBJ)/app/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) $(CFLAGS) $(APP_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# The interactive shell is an ordinary client application. Its buffers live
# in the client-owned region, while the resident engine still leaves that
# complete region available to other applications.
$(OBJ)/shell/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(APP_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

$(OBJ)/shell/shell_main.s: src/shell_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include --bss-name SHELLBSS \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/shell/%.o: $(OBJ)/shell/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

# The storage/index regression client is deliberately broad. cc65 2.18's
# inline optimizer can generate a taken failure branch even when both byte
# comparisons are equal after small, unrelated engine layout changes.
$(OBJ)/app/main.s: src/main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(APP_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

# cc65 2.18 crashes in its optimizer on the deliberately broad aggregate
# regression client, and corrupts the similarly broad result-shaping client's
# software-stack offsets. The engine and focused clients remain optimized.
$(OBJ)/app/aggregate_main.s: src/aggregate_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -I include $(APP_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# This compact aggregate client deliberately combines ordinary, joined,
# correlated, and CTAS paths; cc65 2.18's inline optimizer crashes while
# compiling that control-flow mix just as it does for aggregate_main.c.
$(OBJ)/app/fixed_aggregate_main.s: src/fixed_aggregate_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -I include $(APP_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

$(OBJ)/app/result_main.s: src/result_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -I include $(APP_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# The lifecycle/CTAS client is intentionally broad and now includes results
# larger than the journal. Prefer compact one-shot test orchestration.
$(OBJ)/app/ctas_main.s: src/ctas_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(APP_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/app/join_main.s: src/join_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(APP_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/app/join_aggregate_main.s: src/join_aggregate_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(APP_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

# The broad variable-value regression client is near the fixed $3100 engine
# boundary; favor compact test code as shared cursor helpers evolve.
$(OBJ)/app/variable_main.s: src/variable_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(APP_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

# Schema destruction is branch-heavy lifecycle orchestration, never a row hot
# loop. Favor compact code so TABLE/INDEX/TYPE reclamation shares slot 3.
$(OBJ)/exec/blob_write.s: src/blob_write.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(EXEC_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/exec/table_drop.s: src/table_drop.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(EXEC_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/app/%.o: $(OBJ)/app/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/app/wide_scalar_main.s: src/wide_scalar_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -Cl -I include $(APP_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/app/nested_main.s: src/nested_main.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -Cl -I include $(APP_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/engine/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(ENGINE_FLAGS) \
		--create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# The resident query dispatcher is control flow, not a hot row loop. Static
# locals and out-of-line helpers preserve the fixed resident/WORK boundary.
$(OBJ)/engine/query_api.s: src/query_api.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -Cl -I include $(ENGINE_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

# The resident mutation coordinator is branch-heavy and CTAS adds another
# overlay-spanning state machine. Static locals and out-of-line helpers keep
# it inside the fixed resident region without borrowing from the user area.
$(OBJ)/engine/api.s: src/api.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -Cl -I include $(ENGINE_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

# These tiny endian/checksum loops are smaller with the ordinary optimizer;
# unlike the branch-heavy coordinators, size-loop optimization adds bytes.
$(OBJ)/engine/storage_layout.s: src/storage_layout.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Oirs -I include $(ENGINE_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

# Index dispatch is branch-heavy resident coordination. Out-of-line helpers
# recover the bytes used by the admin-cache scalar comparison trampoline.
$(OBJ)/engine/query_index.s: src/query_index.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -Cl -I include $(ENGINE_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/engine/%.o: $(OBJ)/engine/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/abi/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) $(CFLAGS) $(ABI_C_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# Enum binding is branch-heavy metadata orchestration rather than a hot row
# loop. Keeping helpers out of line leaves ABI room for all three schemas in a
# joined correlated predicate.
$(OBJ)/abi/query_enum.s: src/query_enum.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(ABI_C_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/abi/%.o: $(OBJ)/abi/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/meta/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(META_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# Binding and variable-value metadata are query-open/read control paths. Size
# optimization preserves room in the metadata sidecar for TEXT expressions.
$(OBJ)/meta/query_bind.s: src/query_bind.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -Cl -I include $(META_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/meta/%.o: $(OBJ)/meta/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/row/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) $(CFLAGS) $(ROW_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# Row storage is branch-heavy and the CTAS patch continuation is cold.
# Out-of-line size optimization leaves room for the bounded patch phase.
$(OBJ)/row/row.s: src/row.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(ROW_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

# Aggregate/group selection is a restart-oriented control path. Avoid helper
# inlining across this deliberately broad unit so it remains in sidecar 1.
$(OBJ)/row/query_cursor.s: src/query_cursor.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -Cl -I include $(ROW_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/row/%.o: $(OBJ)/row/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/rowasm/%.o: src/%.s
	@mkdir -p "$(@D)"
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/parse/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) $(CFLAGS) $(PARSE_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# Parsing is one-shot work. Avoid function inlining here so the complete SQL
# grammar, including scalar string expressions, remains in one 16KB sidecar.
$(OBJ)/parse/query_parse.s: src/query_parse.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(PARSE_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/parse/%.o: $(OBJ)/parse/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/exec/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) $(CFLAGS) $(EXEC_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

$(OBJ)/exec/%.o: $(OBJ)/exec/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/execasm/%.o: src/%.s
	@mkdir -p "$(@D)"
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/exec/scalar_shape.s: src/scalar_shape.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(EXEC_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/queryx/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) $(CFLAGS) $(QUERYX_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# Complex result shaping is restart/control-heavy and now includes fixed scalar
# comparison. Keep helpers out of line so joins and correlated subqueries share
# one 16KB producer-owned sidecar.
$(OBJ)/queryx/join.s: src/join.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(QUERYX_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/queryx/%.o: $(OBJ)/queryx/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/sort/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) $(CFLAGS) $(SORT_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

# The restart-oriented sorter now includes streamed TEXT/BLOB comparison.
# Keep its broad control helpers out of line so the complete shaping operator
# remains inside one overlay while preserving its page-at-a-time hot loops.
$(OBJ)/sort/order.s: src/order.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(SORT_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

# Blob compaction is an explicit administrative call.  Keep it beside schema
# inspection in the fixed low-REU admin cache; parser and maintenance cannot be
# live at the same time, and this leaves room for the complete SHOW grammar.
$(OBJ)/sort/blob_compact.s: src/blob_compact.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) $(CFLAGS) $(ADMIN_FLAGS) --create-dep $(@:.s=.d) \
		--dep-target $@ -o $@ $<

$(OBJ)/sort/%.o: $(OBJ)/sort/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/jagg/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(JAGG_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/jagg/join_core.s: src/join.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -D RSQL_JOIN_AGGREGATE_CORE -I include \
		$(JAGG_FLAGS) --create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/jagg/%.o: $(OBJ)/jagg/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/jaggasm/%.o: src/%.s
	@mkdir -p "$(@D)"
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/admin/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(ADMIN_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/admin/wide_scalar_compare.s: src/wide_scalar_compare.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(ADMIN_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/admin/%.o: $(OBJ)/admin/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/wide/%.s: src/%.c
	@mkdir -p "$(@D)"
	$(RSQL_CC) -t c64 -Ors -I include $(WIDE_FLAGS) \
		--create-dep $(@:.s=.d) --dep-target $@ -o $@ $<

$(OBJ)/wide/%.o: $(OBJ)/wide/%.s
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/wideasm/%.o: src/%.s
	@mkdir -p "$(@D)"
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/queryxasm/%.o: src/%.s
	@mkdir -p "$(@D)"
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/phaseentry/%.o: src/%.s
	@mkdir -p "$(@D)"
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(OBJ)/asm/%.o: src/%.s
	@mkdir -p "$(@D)"
	$(RSQL_CA65) -t c64 -I include $< -o $@

$(TARGET): $(APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64.cfg
	@mkdir -p "$(BUILD)" "$(OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64.cfg \
		-m $(BUILD)/rsql64.map -Ln $(BUILD)/rsql64.lbl \
		-o $@ $(APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(QUERY_TARGET): $(TARGET) $(QUERY_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_query.cfg
	@mkdir -p "$(BUILD)" "$(QUERY_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_query.cfg \
		-m $(BUILD)/rsql64_query.map -Ln $(BUILD)/rsql64_query.lbl \
		-o $@ $(QUERY_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(OVERLAY_PRGS): $(TARGET)
	@test -f "$@"

$(QUERY_OVERLAY_PRGS): $(QUERY_TARGET)
	@test -f "$@"

$(AGG_TARGET): $(QUERY_TARGET) $(AGG_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_aggregate.cfg
	@mkdir -p "$(BUILD)" "$(AGG_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_aggregate.cfg \
		-m $(BUILD)/rsql64_aggregate.map -Ln $(BUILD)/rsql64_aggregate.lbl \
		-o $@ $(AGG_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(AGG_OVERLAY_PRGS): $(AGG_TARGET)
	@test -f "$@"

$(VARIABLE_TARGET): $(AGG_TARGET) $(VARIABLE_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_variable.cfg
	@mkdir -p "$(BUILD)" "$(VARIABLE_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_variable.cfg \
		-m $(BUILD)/rsql64_variable.map -Ln $(BUILD)/rsql64_variable.lbl \
		-o $@ $(VARIABLE_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(VARIABLE_OVERLAY_PRGS): $(VARIABLE_TARGET)
	@test -f "$@"

$(VARUPDATE_TARGET): $(VARIABLE_TARGET) $(VARUPDATE_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_varupdate.cfg
	@mkdir -p "$(BUILD)" "$(VARUPDATE_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_varupdate.cfg \
		-m $(BUILD)/rsql64_varupdate.map -Ln $(BUILD)/rsql64_varupdate.lbl \
		-o $@ $(VARUPDATE_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(VARUPDATE_OVERLAY_PRGS): $(VARUPDATE_TARGET)
	@test -f "$@"

$(JOIN_TARGET): $(VARUPDATE_TARGET) $(JOIN_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_join.cfg
	@mkdir -p "$(BUILD)" "$(JOIN_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_join.cfg \
		-m $(BUILD)/rsql64_join.map -Ln $(BUILD)/rsql64_join.lbl \
		-o $@ $(JOIN_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(JOIN_OVERLAY_PRGS): $(JOIN_TARGET)
	@test -f "$@"

$(NESTED_CFG): cfg/reusql64_join.cfg
	@mkdir -p "$(@D)"
	sed 's|build/join_overlays|build/nested_overlays|g' "$<" > "$@"

$(NESTED_TARGET): $(JOIN_TARGET) $(NESTED_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) $(NESTED_CFG)
	@mkdir -p "$(BUILD)" "$(NESTED_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C $(NESTED_CFG) \
		-m $(BUILD)/rsql64_nested.map -Ln $(BUILD)/rsql64_nested.lbl \
		-o $@ $(NESTED_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(NESTED_OVERLAY_PRGS): $(NESTED_TARGET)
	@test -f "$@"

$(WIDE_TARGET): $(JOIN_TARGET) $(WIDE_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_wide.cfg
	@mkdir -p "$(BUILD)" "$(WIDE_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_wide.cfg \
		-m $(BUILD)/rsql64_wide.map -Ln $(BUILD)/rsql64_wide.lbl \
		-o $@ $(WIDE_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(WIDE_OVERLAY_PRGS): $(WIDE_TARGET)
	@test -f "$@"

$(WIDE_SCALAR_CFG): cfg/reusql64_wide.cfg
	@mkdir -p "$(@D)"
	sed 's|build/wide_overlays|build/wide_scalar_overlays|g' "$<" > "$@"

$(WIDE_SCALAR_TARGET): $(WIDE_TARGET) $(WIDE_SCALAR_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) $(WIDE_SCALAR_CFG)
	@mkdir -p "$(BUILD)" "$(WIDE_SCALAR_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C $(WIDE_SCALAR_CFG) \
		-m $(BUILD)/rsql64_wide_scalar.map -Ln $(BUILD)/rsql64_wide_scalar.lbl \
		-o $@ $(WIDE_SCALAR_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(WIDE_SCALAR_OVERLAY_PRGS): $(WIDE_SCALAR_TARGET)
	@:

$(BENCHMARK_CFG): cfg/reusql64_wide.cfg
	@mkdir -p "$(@D)"
	sed 's|build/wide_overlays|build/benchmark_overlays|g' "$<" > "$@"

$(BENCHMARK_TARGET): $(WIDE_TARGET) $(BENCHMARK_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) $(BENCHMARK_CFG)
	@mkdir -p "$(BUILD)" "$(BENCHMARK_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C $(BENCHMARK_CFG) \
		-m $(BUILD)/rsql64_benchmark.map -Ln $(BUILD)/rsql64_benchmark.lbl \
		-o $@ $(BENCHMARK_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(BENCHMARK_OVERLAY_PRGS): $(BENCHMARK_TARGET)
	@test -f "$@"

$(PIPELINE_CFG): cfg/reusql64_wide.cfg
	@mkdir -p "$(@D)"
	sed 's|build/wide_overlays|build/pipeline_benchmark_overlays|g' "$<" > "$@"

$(PIPELINE_TARGET): $(WIDE_TARGET) $(PIPELINE_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) $(PIPELINE_CFG)
	@mkdir -p "$(BUILD)" "$(PIPELINE_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C $(PIPELINE_CFG) \
		-m $(BUILD)/rsql64_pipeline_benchmark.map -Ln $(BUILD)/rsql64_pipeline_benchmark.lbl \
		-o $@ $(PIPELINE_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(PIPELINE_OVERLAY_PRGS): $(PIPELINE_TARGET)
	@test -f "$@"

$(JOINAGG_TARGET): $(JOIN_TARGET) $(JOINAGG_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_joinagg.cfg
	@mkdir -p "$(BUILD)" "$(JOINAGG_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_joinagg.cfg \
		-m $(BUILD)/rsql64_joinagg.map -Ln $(BUILD)/rsql64_joinagg.lbl \
		-o $@ $(JOINAGG_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(JOINAGG_OVERLAY_PRGS): $(JOINAGG_TARGET)
	@test -f "$@"

$(RESULT_TARGET): $(JOINAGG_TARGET) $(RESULT_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_result.cfg
	@mkdir -p "$(BUILD)" "$(RESULT_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_result.cfg \
		-m $(BUILD)/rsql64_result.map -Ln $(BUILD)/rsql64_result.lbl \
		-o $@ $(RESULT_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(RESULT_OVERLAY_PRGS): $(RESULT_TARGET)
	@test -f "$@"

$(CTAS_TARGET): $(RESULT_TARGET) $(CTAS_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_ctas.cfg
	@mkdir -p "$(BUILD)" "$(CTAS_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_ctas.cfg \
		-m $(BUILD)/rsql64_ctas.map -Ln $(BUILD)/rsql64_ctas.lbl \
		-o $@ $(CTAS_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(CTAS_OVERLAY_PRGS): $(CTAS_TARGET)
	@test -f "$@"

# Overlay code calls client-linked cc65 helpers, so this focused lane requires
# its own sidecars even though the database engine objects are identical.
$(FIXEDAGG_TARGET): $(CTAS_TARGET) $(FIXEDAGG_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_fixedagg.cfg
	@mkdir -p "$(BUILD)" "$(FIXEDAGG_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_fixedagg.cfg \
		-m $(BUILD)/rsql64_fixedagg.map -Ln $(BUILD)/rsql64_fixedagg.lbl \
		-o $@ $(FIXEDAGG_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(FIXEDAGG_OVERLAY_PRGS): $(FIXEDAGG_TARGET)
	@test -f "$@"

$(CHECKPOINT_TARGET): $(FIXEDAGG_TARGET) $(CHECKPOINT_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_checkpoint.cfg
	@mkdir -p "$(BUILD)" "$(CHECKPOINT_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_checkpoint.cfg \
		-m $(BUILD)/rsql64_checkpoint.map -Ln $(BUILD)/rsql64_checkpoint.lbl \
		-o $@ $(CHECKPOINT_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(CHECKPOINT_OVERLAY_PRGS): $(CHECKPOINT_TARGET)
	@test -f "$@"

$(SHELL_TARGET): $(CHECKPOINT_TARGET) $(SHELL_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O) cfg/reusql64_shell.cfg
	@mkdir -p "$(BUILD)" "$(SHELL_OVL_DIR)"
	$(RSQL_CC65) -t c64 -C cfg/reusql64_shell.cfg \
		-m $(BUILD)/rsql64_shell.map -Ln $(BUILD)/rsql64_shell.lbl \
		-o $@ $(SHELL_APP_O) $(ENGINE_O) $(ABI_C_O) $(PHASE_ENTRY_O) $(META_O) $(ROW_O) $(PARSE_O) $(EXEC_O) $(QUERYX_O) $(SORT_O) $(JAGG_O) $(ADMIN_O) $(WIDE_O) $(ASM_O) $(QUERYX_ASM_O)

$(SHELL_OVERLAY_PRGS): $(SHELL_TARGET)
	@test -f "$@"

$(DISK): $(TARGET) $(OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(TARGET)" rsql64 \
		-write "$(OVL_META)" rsqlmeta \
		-write "$(OVL_ROW)" rsqlrow \
		-write "$(OVL_PARSE)" rsqlparse \
		-write "$(OVL_EXEC)" rsqlexec \
		-write "$(OVL_QUERY)" rsqlsubq \
		-write "$(OVL_SORT)" rsqlsort \
		-write "$(OVL_JAGG)" rsqljagg \
		-write "$(OVL_ADMIN)" rsqladmin \
		-write "$(OVL_DIR)/rsqlwide.prg" rsqlwide

$(QUERY_DISK): $(QUERY_TARGET) $(QUERY_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(QUERY_TARGET)" rsql64 \
		-write "$(QUERY_OVL_META)" rsqlmeta \
		-write "$(QUERY_OVL_ROW)" rsqlrow \
		-write "$(QUERY_OVL_PARSE)" rsqlparse \
		-write "$(QUERY_OVL_EXEC)" rsqlexec \
		-write "$(QUERY_OVL_QUERY)" rsqlsubq \
		-write "$(QUERY_OVL_SORT)" rsqlsort \
		-write "$(QUERY_OVL_JAGG)" rsqljagg \
		-write "$(QUERY_OVL_ADMIN)" rsqladmin \
		-write "$(QUERY_OVL_DIR)/rsqlwide.prg" rsqlwide

$(AGG_DISK): $(AGG_TARGET) $(AGG_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(AGG_TARGET)" rsql64 \
		-write "$(AGG_OVL_META)" rsqlmeta \
		-write "$(AGG_OVL_ROW)" rsqlrow \
		-write "$(AGG_OVL_PARSE)" rsqlparse \
		-write "$(AGG_OVL_EXEC)" rsqlexec \
		-write "$(AGG_OVL_QUERY)" rsqlsubq \
		-write "$(AGG_OVL_SORT)" rsqlsort \
		-write "$(AGG_OVL_JAGG)" rsqljagg \
		-write "$(AGG_OVL_ADMIN)" rsqladmin \
		-write "$(AGG_OVL_DIR)/rsqlwide.prg" rsqlwide

$(VARIABLE_DISK): $(VARIABLE_TARGET) $(VARIABLE_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(VARIABLE_TARGET)" rsql64 \
		-write "$(VARIABLE_OVL_META)" rsqlmeta \
		-write "$(VARIABLE_OVL_ROW)" rsqlrow \
		-write "$(VARIABLE_OVL_PARSE)" rsqlparse \
		-write "$(VARIABLE_OVL_EXEC)" rsqlexec \
		-write "$(VARIABLE_OVL_QUERY)" rsqlsubq \
		-write "$(VARIABLE_OVL_SORT)" rsqlsort \
		-write "$(VARIABLE_OVL_JAGG)" rsqljagg \
		-write "$(VARIABLE_OVL_ADMIN)" rsqladmin \
		-write "$(VARIABLE_OVL_DIR)/rsqlwide.prg" rsqlwide

$(VARUPDATE_DISK): $(VARUPDATE_TARGET) $(VARUPDATE_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(VARUPDATE_TARGET)" rsql64 \
		-write "$(VARUPDATE_OVL_META)" rsqlmeta \
		-write "$(VARUPDATE_OVL_ROW)" rsqlrow \
		-write "$(VARUPDATE_OVL_PARSE)" rsqlparse \
		-write "$(VARUPDATE_OVL_EXEC)" rsqlexec \
		-write "$(VARUPDATE_OVL_QUERY)" rsqlsubq \
		-write "$(VARUPDATE_OVL_SORT)" rsqlsort \
		-write "$(VARUPDATE_OVL_JAGG)" rsqljagg \
		-write "$(VARUPDATE_OVL_ADMIN)" rsqladmin \
		-write "$(VARUPDATE_OVL_DIR)/rsqlwide.prg" rsqlwide

$(JOIN_DISK): $(JOIN_TARGET) $(JOIN_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(JOIN_TARGET)" rsql64 \
		-write "$(JOIN_OVL_META)" rsqlmeta \
		-write "$(JOIN_OVL_ROW)" rsqlrow \
		-write "$(JOIN_OVL_PARSE)" rsqlparse \
		-write "$(JOIN_OVL_EXEC)" rsqlexec \
		-write "$(JOIN_OVL_QUERY)" rsqlsubq \
		-write "$(JOIN_OVL_SORT)" rsqlsort \
		-write "$(JOIN_OVL_JAGG)" rsqljagg \
		-write "$(JOIN_OVL_ADMIN)" rsqladmin \
		-write "$(JOIN_OVL_DIR)/rsqlwide.prg" rsqlwide

$(NESTED_DISK): $(NESTED_TARGET) $(NESTED_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(NESTED_TARGET)" rsql64 \
		-write "$(NESTED_OVL_DIR)/rsqlmeta.prg" rsqlmeta \
		-write "$(NESTED_OVL_DIR)/rsqlrow.prg" rsqlrow \
		-write "$(NESTED_OVL_DIR)/rsqlparse.prg" rsqlparse \
		-write "$(NESTED_OVL_DIR)/rsqlexec.prg" rsqlexec \
		-write "$(NESTED_OVL_DIR)/rsqlsubq.prg" rsqlsubq \
		-write "$(NESTED_OVL_DIR)/rsqlsort.prg" rsqlsort \
		-write "$(NESTED_OVL_DIR)/rsqljagg.prg" rsqljagg \
		-write "$(NESTED_OVL_DIR)/rsqladmin.prg" rsqladmin \
		-write "$(NESTED_OVL_DIR)/rsqlwide.prg" rsqlwide

$(WIDE_DISK): $(WIDE_TARGET) $(WIDE_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(WIDE_TARGET)" rsql64 \
		-write "$(WIDE_OVL_DIR)/rsqlmeta.prg" rsqlmeta \
		-write "$(WIDE_OVL_DIR)/rsqlrow.prg" rsqlrow \
		-write "$(WIDE_OVL_DIR)/rsqlparse.prg" rsqlparse \
		-write "$(WIDE_OVL_DIR)/rsqlexec.prg" rsqlexec \
		-write "$(WIDE_OVL_DIR)/rsqlsubq.prg" rsqlsubq \
		-write "$(WIDE_OVL_DIR)/rsqlsort.prg" rsqlsort \
		-write "$(WIDE_OVL_DIR)/rsqljagg.prg" rsqljagg \
		-write "$(WIDE_OVL_DIR)/rsqladmin.prg" rsqladmin \
		-write "$(WIDE_OVL_DIR)/rsqlwide.prg" rsqlwide

$(WIDE_SCALAR_DISK): $(WIDE_SCALAR_TARGET) $(WIDE_SCALAR_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(WIDE_SCALAR_TARGET)" rsql64 \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqlmeta.prg" rsqlmeta \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqlrow.prg" rsqlrow \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqlparse.prg" rsqlparse \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqlexec.prg" rsqlexec \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqlsubq.prg" rsqlsubq \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqlsort.prg" rsqlsort \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqljagg.prg" rsqljagg \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqladmin.prg" rsqladmin \
		-write "$(WIDE_SCALAR_OVL_DIR)/rsqlwide.prg" rsqlwide

$(BENCHMARK_DISK): $(BENCHMARK_TARGET) $(BENCHMARK_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "rsqlbench,64" d81 "$@" \
		-write "$(BENCHMARK_TARGET)" rsql64 \
		-write "$(BENCHMARK_OVL_DIR)/rsqlmeta.prg" rsqlmeta \
		-write "$(BENCHMARK_OVL_DIR)/rsqlrow.prg" rsqlrow \
		-write "$(BENCHMARK_OVL_DIR)/rsqlparse.prg" rsqlparse \
		-write "$(BENCHMARK_OVL_DIR)/rsqlexec.prg" rsqlexec \
		-write "$(BENCHMARK_OVL_DIR)/rsqlsubq.prg" rsqlsubq \
		-write "$(BENCHMARK_OVL_DIR)/rsqlsort.prg" rsqlsort \
		-write "$(BENCHMARK_OVL_DIR)/rsqljagg.prg" rsqljagg \
		-write "$(BENCHMARK_OVL_DIR)/rsqladmin.prg" rsqladmin \
		-write "$(BENCHMARK_OVL_DIR)/rsqlwide.prg" rsqlwide

$(PIPELINE_DISK): $(PIPELINE_TARGET) $(PIPELINE_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "rsqlpipe,64" d81 "$@" \
		-write "$(PIPELINE_TARGET)" rsql64 \
		-write "$(PIPELINE_OVL_DIR)/rsqlmeta.prg" rsqlmeta \
		-write "$(PIPELINE_OVL_DIR)/rsqlrow.prg" rsqlrow \
		-write "$(PIPELINE_OVL_DIR)/rsqlparse.prg" rsqlparse \
		-write "$(PIPELINE_OVL_DIR)/rsqlexec.prg" rsqlexec \
		-write "$(PIPELINE_OVL_DIR)/rsqlsubq.prg" rsqlsubq \
		-write "$(PIPELINE_OVL_DIR)/rsqlsort.prg" rsqlsort \
		-write "$(PIPELINE_OVL_DIR)/rsqljagg.prg" rsqljagg \
		-write "$(PIPELINE_OVL_DIR)/rsqladmin.prg" rsqladmin \
		-write "$(PIPELINE_OVL_DIR)/rsqlwide.prg" rsqlwide

$(JOINAGG_DISK): $(JOINAGG_TARGET) $(JOINAGG_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(JOINAGG_TARGET)" rsql64 \
		-write "$(JOINAGG_OVL_META)" rsqlmeta \
		-write "$(JOINAGG_OVL_ROW)" rsqlrow \
		-write "$(JOINAGG_OVL_PARSE)" rsqlparse \
		-write "$(JOINAGG_OVL_EXEC)" rsqlexec \
		-write "$(JOINAGG_OVL_QUERY)" rsqlsubq \
		-write "$(JOINAGG_OVL_SORT)" rsqlsort \
		-write "$(JOINAGG_OVL_JAGG)" rsqljagg \
		-write "$(JOINAGG_OVL_ADMIN)" rsqladmin \
		-write "$(JOINAGG_OVL_DIR)/rsqlwide.prg" rsqlwide

$(RESULT_DISK): $(RESULT_TARGET) $(RESULT_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(RESULT_TARGET)" rsql64 \
		-write "$(RESULT_OVL_META)" rsqlmeta \
		-write "$(RESULT_OVL_ROW)" rsqlrow \
		-write "$(RESULT_OVL_PARSE)" rsqlparse \
		-write "$(RESULT_OVL_EXEC)" rsqlexec \
		-write "$(RESULT_OVL_QUERY)" rsqlsubq \
		-write "$(RESULT_OVL_SORT)" rsqlsort \
		-write "$(RESULT_OVL_JAGG)" rsqljagg \
		-write "$(RESULT_OVL_ADMIN)" rsqladmin \
		-write "$(RESULT_OVL_DIR)/rsqlwide.prg" rsqlwide

$(CTAS_DISK): $(CTAS_TARGET) $(CTAS_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(CTAS_TARGET)" rsql64 \
		-write "$(CTAS_OVL_META)" rsqlmeta \
		-write "$(CTAS_OVL_ROW)" rsqlrow \
		-write "$(CTAS_OVL_PARSE)" rsqlparse \
		-write "$(CTAS_OVL_EXEC)" rsqlexec \
		-write "$(CTAS_OVL_QUERY)" rsqlsubq \
		-write "$(CTAS_OVL_SORT)" rsqlsort \
		-write "$(CTAS_OVL_JAGG)" rsqljagg \
		-write "$(CTAS_OVL_ADMIN)" rsqladmin \
		-write "$(CTAS_OVL_DIR)/rsqlwide.prg" rsqlwide

$(FIXEDAGG_DISK): $(FIXEDAGG_TARGET) $(FIXEDAGG_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(FIXEDAGG_TARGET)" rsql64 \
		-write "$(FIXEDAGG_OVL_META)" rsqlmeta \
		-write "$(FIXEDAGG_OVL_ROW)" rsqlrow \
		-write "$(FIXEDAGG_OVL_PARSE)" rsqlparse \
		-write "$(FIXEDAGG_OVL_EXEC)" rsqlexec \
		-write "$(FIXEDAGG_OVL_QUERY)" rsqlsubq \
		-write "$(FIXEDAGG_OVL_SORT)" rsqlsort \
		-write "$(FIXEDAGG_OVL_JAGG)" rsqljagg \
		-write "$(FIXEDAGG_OVL_ADMIN)" rsqladmin \
		-write "$(FIXEDAGG_OVL_DIR)/rsqlwide.prg" rsqlwide

$(CHECKPOINT_DISK): $(CHECKPOINT_TARGET) $(CHECKPOINT_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(CHECKPOINT_TARGET)" rsql64 \
		-write "$(CHECKPOINT_OVL_META)" rsqlmeta \
		-write "$(CHECKPOINT_OVL_ROW)" rsqlrow \
		-write "$(CHECKPOINT_OVL_PARSE)" rsqlparse \
		-write "$(CHECKPOINT_OVL_EXEC)" rsqlexec \
		-write "$(CHECKPOINT_OVL_QUERY)" rsqlsubq \
		-write "$(CHECKPOINT_OVL_SORT)" rsqlsort \
		-write "$(CHECKPOINT_OVL_JAGG)" rsqljagg \
		-write "$(CHECKPOINT_OVL_ADMIN)" rsqladmin \
		-write "$(CHECKPOINT_OVL_DIR)/rsqlwide.prg" rsqlwide

$(SHELL_DISK): $(SHELL_TARGET) $(SHELL_OVERLAY_PRGS)
	@mkdir -p "$(BUILD)"
	@rm -f "$@"
	$(RSQL_C1541) -format "reusql64,64" d81 "$@" \
		-write "$(SHELL_TARGET)" rsql64 \
		-write "$(SHELL_OVL_META)" rsqlmeta \
		-write "$(SHELL_OVL_ROW)" rsqlrow \
		-write "$(SHELL_OVL_PARSE)" rsqlparse \
		-write "$(SHELL_OVL_EXEC)" rsqlexec \
		-write "$(SHELL_OVL_QUERY)" rsqlsubq \
		-write "$(SHELL_OVL_SORT)" rsqlsort \
		-write "$(SHELL_OVL_JAGG)" rsqljagg \
		-write "$(SHELL_OVL_ADMIN)" rsqladmin \
		-write "$(SHELL_OVL_DIR)/rsqlwide.prg" rsqlwide

memory-report: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(NESTED_TARGET) $(WIDE_TARGET) $(WIDE_SCALAR_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(FIXEDAGG_TARGET) $(CHECKPOINT_TARGET) $(SHELL_TARGET) $(BENCHMARK_TARGET)
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64.map $(BUILD)/rsql64.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_query.map $(BUILD)/rsql64_query.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_aggregate.map $(BUILD)/rsql64_aggregate.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_variable.map $(BUILD)/rsql64_variable.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_varupdate.map $(BUILD)/rsql64_varupdate.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_join.map $(BUILD)/rsql64_join.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_nested.map $(BUILD)/rsql64_nested.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_wide.map $(BUILD)/rsql64_wide.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_wide_scalar.map $(BUILD)/rsql64_wide_scalar.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_joinagg.map $(BUILD)/rsql64_joinagg.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_result.map $(BUILD)/rsql64_result.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_ctas.map $(BUILD)/rsql64_ctas.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_fixedagg.map $(BUILD)/rsql64_fixedagg.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_checkpoint.map $(BUILD)/rsql64_checkpoint.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_shell.map $(BUILD)/rsql64_shell.lbl
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_benchmark.map $(BUILD)/rsql64_benchmark.lbl

emu-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(FIXEDAGG_TARGET) $(CHECKPOINT_TARGET) $(SHELL_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_OVERLAY_PRGS) $(CHECKPOINT_OVERLAY_PRGS) $(SHELL_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_TARGET) $(FIXEDAGG_OVERLAY_PRGS) $(CHECKPOINT_TARGET) $(CHECKPOINT_OVERLAY_PRGS) $(SHELL_TARGET) $(SHELL_OVERLAY_PRGS)

emu-result-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --result-only

emu-ctas-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --ctas-only

emu-varupdate-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --varupdate-only

emu-variable-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --variable-only

emu-aggregate-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(FIXEDAGG_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_TARGET) $(FIXEDAGG_OVERLAY_PRGS) --aggregate-only

emu-fixedagg-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(FIXEDAGG_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_TARGET) $(FIXEDAGG_OVERLAY_PRGS) --fixedagg-only

emu-checkpoint-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(FIXEDAGG_TARGET) $(CHECKPOINT_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_OVERLAY_PRGS) $(CHECKPOINT_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_TARGET) $(FIXEDAGG_OVERLAY_PRGS) $(CHECKPOINT_TARGET) $(CHECKPOINT_OVERLAY_PRGS) --checkpoint-only

emu-shell-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(FIXEDAGG_TARGET) $(CHECKPOINT_TARGET) $(SHELL_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_OVERLAY_PRGS) $(CHECKPOINT_OVERLAY_PRGS) $(SHELL_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) $(FIXEDAGG_TARGET) $(FIXEDAGG_OVERLAY_PRGS) $(CHECKPOINT_TARGET) $(CHECKPOINT_OVERLAY_PRGS) $(SHELL_TARGET) $(SHELL_OVERLAY_PRGS) --shell-only

emu-benchmark-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(BENCHMARK_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(BENCHMARK_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(BENCHMARK_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(BENCHMARK_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --benchmark-only

emu-pipeline-benchmark-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(PIPELINE_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(PIPELINE_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(PIPELINE_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(PIPELINE_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --pipeline-benchmark-only

emu-join-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(JOIN_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(JOIN_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --join-only

emu-wide-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(WIDE_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(WIDE_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(WIDE_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(WIDE_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --join-only

emu-wide-scalar-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(WIDE_SCALAR_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(WIDE_SCALAR_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(WIDE_SCALAR_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(WIDE_SCALAR_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --join-only

emu-nested-test: $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(NESTED_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(NESTED_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS)
	$(RSQL_ZIG) build emu-test -- $(TARGET) $(QUERY_TARGET) $(AGG_TARGET) $(VARIABLE_TARGET) $(VARUPDATE_TARGET) $(NESTED_TARGET) $(JOINAGG_TARGET) $(RESULT_TARGET) $(CTAS_TARGET) $(OVERLAY_PRGS) $(QUERY_OVERLAY_PRGS) $(AGG_OVERLAY_PRGS) $(VARIABLE_OVERLAY_PRGS) $(VARUPDATE_OVERLAY_PRGS) $(NESTED_OVERLAY_PRGS) $(JOINAGG_OVERLAY_PRGS) $(RESULT_OVERLAY_PRGS) $(CTAS_OVERLAY_PRGS) --join-only

test: emu-test emu-wide-test emu-wide-scalar-test emu-nested-test

vice-test: $(DISK) $(QUERY_DISK) $(AGG_DISK) $(VARIABLE_DISK) $(VARUPDATE_DISK) $(JOIN_DISK) $(NESTED_DISK) $(WIDE_DISK) $(WIDE_SCALAR_DISK) $(JOINAGG_DISK) $(RESULT_DISK) $(CTAS_DISK) $(FIXEDAGG_DISK) $(CHECKPOINT_DISK) $(SHELL_DISK)
	RSQL_DOTNET="$(RSQL_DOTNET)" RSQL_VICE_TASKS="$(RSQL_VICE_TASKS)" bash scripts/run_vice_tests.sh

vice-benchmark-test: $(BENCHMARK_DISK)
	RSQL_DOTNET="$(RSQL_DOTNET)" RSQL_VICE_TASKS="$(RSQL_VICE_TASKS)" bash scripts/run_vice_benchmark.sh

vice-pipeline-benchmark-test: $(PIPELINE_DISK)
	RSQL_DOTNET="$(RSQL_DOTNET)" RSQL_VICE_TASKS="$(RSQL_VICE_TASKS)" bash scripts/run_vice_pipeline_benchmark.sh

pipeline-benchmark-memory-report: $(PIPELINE_TARGET)
	python3 scripts/verify_memory_map.py $(BUILD)/rsql64_pipeline_benchmark.map $(BUILD)/rsql64_pipeline_benchmark.lbl

run-vice: $(DISK)
	$(RSQL_VICE) -default -reu -reusize 16384 -autostartprgmode 1 -autostart $(DISK)

clean:
	rm -rf "$(BUILD)" .zig-cache zig-out

-include $(DEPS)
