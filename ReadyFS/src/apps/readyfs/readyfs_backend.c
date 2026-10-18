#include "readyfs_console.h"
#include "readyfs_backend.h"

#include "readyfs_exec.h"

#include <string.h>

#ifdef READYFS_BACKEND_SIDECAR
#include <conio.h>
#include "readyfs_nativeplan.h"
#include "readyfs_overlay.h"
#endif

#ifdef __CC65__
#include "readyfs_journal.h"
#include "readyfs_overlay.h"
#include "readyfs_plan.h"
#include "readyfs_reu.h"

extern unsigned char readyfs_pipeline_scratch[RF_PIPELINE_SCRATCH_BYTES];

typedef union {
    ReadyFsPlanCall plan;
    ReadyFsExecCall exec;
    ReadyFsActionCall action;
    ReadyFsJournalCall journal;
    ReadyFsJournalOne one;
} ReadyFsPipelineCall;

typedef struct {
    ReadyFsNestedCall nested;
    ReadyFsPlan plan;
    ReadyFsExecutor exec;
    ReadyFsJournal journal;
    ReadyFsBackendRequest request;
    ReadyFsPlanRecord plan_record;
    ReadyFsJournalRecord journal_record;
    ReadyFsPipelineCall call;
    char stem[16];
    char source[24];
    char destination[32];
    char replay[16];
} ReadyFsPipelineState;
#endif

typedef struct {
    const char *root;
    const char *stem;
    char *output;
    unsigned int capacity;
    ReadyFsPath *path;
} ReadyFsBackendJoin;

/* The backend overlay is cooperative and non-reentrant. Keeping its join
 * context in the overlay avoids fragile nested multi-argument cc65 calls. */
static ReadyFsBackendJoin join_context;
static ReadyFsBackendRequest selftest_request;
static ReadyFsBackendCall selftest_call;
static char selftest_source[16];
static char selftest_destination[24];
#ifdef __CC65__
static unsigned char endpoint_ok(unsigned char endpoint);
static ReadyFsPath execute_path;

static unsigned char execute_root_ok(const char *root) {
    return (unsigned char)(root != 0 &&
        readyfs_path_parse(root, &execute_path) == RF_PATH_OK &&
        execute_path.absolute && endpoint_ok(execute_path.endpoint));
}
#endif

#ifdef __CC65__
static unsigned char pipeline_nested(ReadyFsPipelineState *state,
                                     unsigned char operation, void *call) {
    state->nested.operation = operation;
    state->nested.call = call;
    return readyfs_overlay_nested_from_backend(&state->nested);
}

/* The former boot-time end-to-end pipeline probe lived here and consumed over
 * a kilobyte of the closed backend sidecar. Real action/RFJ1 VICE suites now
 * provide the stronger executable oracle. Keep boot admission to the ABI and
 * compact build-one probe below so this sidecar can host native planning. */
#if 0
static unsigned char pipeline_selftest(void) {
    ReadyFsPipelineState *state;
    unsigned int journal_offset;
    unsigned int plan_offset;

    state = (ReadyFsPipelineState *)readyfs_pipeline_scratch;
    memset(state, 0, sizeof(*state));

    state->call.plan.operation = RF_PLAN_CALL_INIT;
    state->call.plan.plan = &state->plan;
    state->call.plan.capacity = RF_REU_PLAN_BYTES;
    if (!pipeline_nested(state, RF_NESTED_PLAN, &state->call.plan)) return 0u;

    strcpy(state->stem, "d/a.prg");
    memset(&state->call, 0, sizeof(state->call));
    state->call.plan.operation = RF_PLAN_CALL_ADD;
    state->call.plan.plan = &state->plan;
    state->call.plan.kind = RF_PLAN_KIND_FILE;
    state->call.plan.flags = RF_PLAN_SELECTED;
    state->call.plan.stem = state->stem;
    if (!pipeline_nested(state, RF_NESTED_PLAN, &state->call.plan)) return 0u;

    memset(&state->call, 0, sizeof(state->call));
    state->call.exec.operation = RF_EXEC_CALL_INIT;
    state->call.exec.mode = RF_EXEC_MODE_COPY;
    state->call.exec.exec = &state->exec;
    state->call.exec.plan = &state->plan;
    if (!pipeline_nested(state, RF_NESTED_EXEC, &state->call.exec)) return 0u;

    memset(&state->call, 0, sizeof(state->call));
    state->call.exec.operation = RF_EXEC_CALL_NEXT;
    state->call.exec.exec = &state->exec;
    state->call.exec.record = &state->plan_record;
    state->call.exec.stem = state->stem;
    state->call.exec.stem_capacity = sizeof(state->stem);
    if (pipeline_nested(state, RF_NESTED_EXEC, &state->call.exec) !=
        RF_EXEC_ACTION_COPY_FILE) return 0u;

    state->request.source_text = state->source;
    state->request.source_capacity = sizeof(state->source);
    state->request.destination_text = state->destination;
    state->request.destination_capacity = sizeof(state->destination);
    selftest_call.operation = RF_BACKEND_CALL_BUILD;
    selftest_call.action = RF_EXEC_ACTION_COPY_FILE;
    selftest_call.source_root = "8:/";
    selftest_call.destination_root = "u:/usb1/out";
    selftest_call.stem = state->stem;
    selftest_call.request = &state->request;
    if (!readyfs_backend_build(&selftest_call) ||
        strcmp(state->source, "8:/d/a.prg") != 0 ||
        strcmp(state->destination, "u:/usb1/out/d/a.prg") != 0) return 0u;

    memset(&state->call, 0, sizeof(state->call));
    state->call.journal.operation = RF_JOURNAL_CALL_INIT;
    state->call.journal.mode = RF_EXEC_MODE_COPY;
    state->call.journal.journal = &state->journal;
    state->call.journal.capacity = RF_REU_JOURNAL_BYTES;
    state->call.journal.write = readyfs_reu_session_store;
    state->call.journal.read = readyfs_reu_session_fetch;
    if (!pipeline_nested(state, RF_NESTED_JOURNAL,
                         &state->call.journal)) return 0u;

    plan_offset = state->exec.pending;
    memset(&state->call, 0, sizeof(state->call));
    state->call.journal.operation = RF_JOURNAL_CALL_APPEND;
    state->call.journal.journal = &state->journal;
    state->call.journal.action = RF_EXEC_ACTION_COPY_FILE;
    state->call.journal.result = 82u;
    state->call.journal.backend = RF_EP_ULTIMATE;
    state->call.journal.kind = state->plan_record.kind;
    state->call.journal.detail = 82u;
    state->call.journal.plan_offset = plan_offset;
    state->call.journal.stem = state->stem;
    if (!pipeline_nested(state, RF_NESTED_JOURNAL,
                         &state->call.journal)) return 0u;

    memset(&state->call, 0, sizeof(state->call));
    state->call.exec.operation = RF_EXEC_CALL_ACK;
    state->call.exec.exec = &state->exec;
    state->call.exec.succeeded = 0u;
    if (!pipeline_nested(state, RF_NESTED_EXEC, &state->call.exec)) return 0u;

    memset(&state->call, 0, sizeof(state->call));
    state->call.journal.operation = RF_JOURNAL_CALL_FINISH;
    state->call.journal.journal = &state->journal;
    if (!pipeline_nested(state, RF_NESTED_JOURNAL,
                         &state->call.journal)) return 0u;

    journal_offset = RF_JOURNAL_HEADER_BYTES;
    memset(&state->call, 0, sizeof(state->call));
    state->call.journal.operation = RF_JOURNAL_CALL_READ;
    state->call.journal.journal = &state->journal;
    state->call.journal.offset = journal_offset;
    state->call.journal.record = &state->journal_record;
    state->call.journal.output = state->replay;
    state->call.journal.output_capacity = sizeof(state->replay);
    if (!pipeline_nested(state, RF_NESTED_JOURNAL,
                         &state->call.journal)) return 0u;
    return state->exec.attempted == 1u && state->exec.failed == 1u &&
           state->journal.count == 1u && state->journal.failed == 1u &&
           state->journal_record.result == 82u &&
           state->journal_record.detail == 82u &&
           state->journal_record.plan_offset == plan_offset &&
           state->call.journal.next == RF_JOURNAL_END &&
           strcmp(state->replay, "d/a.prg") == 0;
}
#endif
#endif

unsigned int readyfs_backend_abi(void) { return RF_BACKEND_ABI; }

#ifdef READYFS_BACKEND_SIDECAR
static unsigned char native_same(const char *left, const char *right) {
    while (*left != 0 && *right != 0 &&
           (((unsigned char)*left & 0x7Fu) ==
            ((unsigned char)*right & 0x7Fu))) {
        ++left;
        ++right;
    }
    return (unsigned char)(*left == 0 && *right == 0);
}

static unsigned char native_find(ReadyFsNativePlanCall *call,
                                 const char *name) {
    unsigned char index;
    for (index = 0u; index < call->argc; ++index) {
        if (native_same(call->args[index], name)) return (unsigned char)(index + 1u);
    }
    return 0u;
}

static const char *native_option(ReadyFsNativePlanCall *call,
                                 const char *name) {
    unsigned char index;
    index = native_find(call, name);
    return index != 0u && index < call->argc ? call->args[index] : 0;
}

static unsigned char native_is_dry(ReadyFsNativePlanCall *call) {
    return (unsigned char)(native_find(call, "--dry-run") ||
                           native_find(call, "--whatif"));
}

static void native_print_u16(unsigned int value) {
    char reverse[5];
    unsigned char used;
    used = 0u;
    do {
        reverse[used++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value != 0u);
    while (used != 0u) cputc(reverse[--used]);
}

unsigned char readyfs_backend_native_plan(ReadyFsNativePlanCall *call) {
    ReadyFsPath *parsed;
    ReadyFsRecursiveCall *recursive;
    const char *pattern;

    if (call->phase == RF_NATIVEPLAN_PREPARE) {
        if (!native_is_dry(call)) {
            if (!native_find(call, "--apply")) {
                cputs(RF_ERROR "need --apply\r\n");
                return 0u;
            }
        }
        parsed = call->source_path;
        if (call->source == 0 || call->pattern == 0 || parsed == 0 ||
            readyfs_path_parse(call->source, parsed) != RF_PATH_OK) return 0u;
        memset(&call->path, 0, sizeof(call->path));
        call->path.operation = RF_CMDPATH_NATIVE_DIR;
        call->path.source = call->source;
        call->path.output = call->pattern;
        call->path.output_capacity = RF_PATH_MAX + 1u;
        call->nested.operation = RF_NESTED_CMDPATH |
                                 RF_NESTED_RETURN_BACKEND;
        call->nested.call = &call->path;
        if (!readyfs_overlay_nested_from_backend(
                (ReadyFsNestedCall *)&call->nested)) return 0u;
        call->device = call->path.device;
        call->source[parsed->path_offset + 1u] = 0;
        return 1u;
    }
    if (call->phase == RF_NATIVEPLAN_REPORT) {
        cputs(RF_SUMMARY "recursive plan f"); native_print_u16(call->entries);
        cputs(" selected "); native_print_u16(call->selected); cputs("\r\n");
        call->dry_run = native_is_dry(call);
        if (call->dry_run) {
            cputs(RF_SUMMARY "plan w");
            native_print_u16(call->mode == RF_EXEC_MODE_DELETE ?
                             0u : call->selected);
            cputs(" d");
            native_print_u16(call->mode == RF_EXEC_MODE_COPY ?
                             0u : call->selected);
            cputs(" m0; done w0 d0 m0\r\n");
        }
        return 1u;
    }
    if (call->phase != RF_NATIVEPLAN_ADD || call->stem == 0) return 0u;
    if ((unsigned char)(call->file_type - RF_NATIVE_TYPE_FIRST) >=
        RF_NATIVE_TYPE_COUNT) return 0u;
    call->flags = RF_PLAN_SELECTED;
    call->match.stem = call->stem;
    pattern = native_option(call, "--include");
    if (pattern != 0) {
        call->match.pattern = pattern;
        call->nested.operation = RF_NESTED_MATCH |
                                 RF_NESTED_RETURN_BACKEND;
        call->nested.call = &call->match;
        if (!readyfs_overlay_nested_from_backend(
                (ReadyFsNestedCall *)&call->nested)) call->flags = 0u;
    }
    pattern = native_option(call, "--exclude");
    if (pattern != 0) {
        call->match.pattern = pattern;
        call->nested.operation = RF_NESTED_MATCH |
                                 RF_NESTED_RETURN_BACKEND;
        call->nested.call = &call->match;
        if (readyfs_overlay_nested_from_backend(
                (ReadyFsNestedCall *)&call->nested)) call->flags = 0u;
    }
    recursive = call->recursive;
    memset(recursive, 0, sizeof(*recursive));
    recursive->operation = RF_RECURSIVE_CALL_ADD;
    recursive->kind = RF_PLAN_KIND_FILE;
    recursive->flags = call->flags;
    recursive->stem = call->stem;
    call->nested.operation = RF_NESTED_RECURSIVE |
                             RF_NESTED_RETURN_BACKEND;
    call->nested.call = recursive;
    if (!readyfs_overlay_nested_from_backend(
            (ReadyFsNestedCall *)&call->nested)) return 0u;
    if (call->display && (call->flags & RF_PLAN_SELECTED)) {
        cputs("target "); cputs(call->stem);
        cputs(" type $"); cputhex8(call->file_type); cputs("\r\n");
    }
    return 1u;
}
#endif

static unsigned char endpoint_ok(unsigned char endpoint) {
    return (unsigned char)(endpoint >= RF_EP_IEC && endpoint <= RF_EP_TAPE);
}

static unsigned char action_needs_source(unsigned char action) {
    return (unsigned char)(action >= RF_EXEC_ACTION_COPY_FILE &&
                           action <= RF_EXEC_ACTION_RMDIR);
}

static unsigned char action_needs_destination(unsigned char action) {
    return (unsigned char)(action >= RF_EXEC_ACTION_MKDIR &&
                           action <= RF_EXEC_ACTION_MOVE_FILE);
}

static unsigned char join_path(ReadyFsBackendJoin *join) {
    unsigned int root_len;
    unsigned int stem_len;
    unsigned char separator;

    if (join == 0 || join->root == 0 || join->stem == 0 ||
        join->output == 0 || join->capacity == 0u || *join->root == 0 ||
        *join->stem == '/' || readyfs_path_has_parent_escape(join->stem)) {
        return 0u;
    }
    root_len = strlen(join->root);
    stem_len = strlen(join->stem);
    separator = join->root[root_len - 1u] != '/' && *join->stem != 0;
    if (root_len + stem_len + separator + 1u > join->capacity) return 0u;
    memcpy(join->output, join->root, root_len);
    if (separator) join->output[root_len++] = '/';
    memcpy(join->output + root_len, join->stem, stem_len + 1u);
    return 1u;
}

static unsigned char build_one(ReadyFsBackendJoin *join) {
    if (!join_path(join) ||
        readyfs_path_parse(join->output, join->path) != RF_PATH_OK ||
        !join->path->absolute || !endpoint_ok(join->path->endpoint)) return 0u;
    return 1u;
}

unsigned char readyfs_backend_build(ReadyFsBackendCall *call) {
    ReadyFsBackendRequest *request;
    unsigned char needs_source;
    unsigned char needs_destination;

    if (call == 0 || call->request == 0 || call->stem == 0) return 0u;
    request = call->request;
    needs_source = action_needs_source(call->action);
    needs_destination = action_needs_destination(call->action);
    if ((!needs_source && !needs_destination) ||
        (needs_source &&
         (call->source_root == 0 || request->source_text == 0)) ||
        (needs_destination &&
         (call->destination_root == 0 ||
          request->destination_text == 0))) return 0u;
    request->action = call->action;
    request->has_source = 0u;
    request->has_destination = 0u;
    if (needs_source) {
        join_context.root = call->source_root;
        join_context.stem = call->stem;
        join_context.output = request->source_text;
        join_context.capacity = request->source_capacity;
        join_context.path = &request->source;
        if (!build_one(&join_context)) return 0u;
        request->has_source = 1u;
    }
    if (needs_destination) {
        join_context.root = call->destination_root;
        join_context.stem = call->stem;
        join_context.output = request->destination_text;
        join_context.capacity = request->destination_capacity;
        join_context.path = &request->destination;
        if (!build_one(&join_context)) return 0u;
        request->has_destination = 1u;
    }
    return 1u;
}

unsigned char readyfs_backend_dispatch(ReadyFsBackendCall *call) {
#ifdef __CC65__
    ReadyFsPipelineState *state;
#endif

    if (call == 0) return 0u;
#ifdef READYFS_BACKEND_SIDECAR
    if (call->operation == RF_BACKEND_CALL_NATIVE_PLAN) {
        return readyfs_backend_native_plan((ReadyFsNativePlanCall *)call);
    }
#endif
    if (call->operation == RF_BACKEND_CALL_BUILD) {
        return readyfs_backend_build(call);
    }
    if (call->operation == RF_BACKEND_CALL_SELFTEST) {
        return readyfs_backend_selftest();
    }
#ifndef __CC65__
    if (call->operation == RF_BACKEND_CALL_CAPABILITIES) {
        return readyfs_backend_capabilities(call->source_root,
                                            call->capabilities);
    }
#endif
#ifdef __CC65__
    if ((call->operation == RF_BACKEND_CALL_BEGIN ||
         call->operation == RF_BACKEND_CALL_COMPLETE) &&
        call->action >= RF_EXEC_ACTION_MKDIR &&
        call->action <= RF_EXEC_ACTION_RMDIR &&
        call->state != 0 &&
        (!action_needs_source(call->action) ||
         execute_root_ok(call->source_root)) &&
        (!action_needs_destination(call->action) ||
         execute_root_ok(call->destination_root))) {
        state = (ReadyFsPipelineState *)readyfs_pipeline_scratch;
        if (call->operation == RF_BACKEND_CALL_BEGIN) {
            memset(&state->call, 0, sizeof(state->call));
            state->call.action.operation = RF_ACTION_CALL_BEGIN;
            state->call.action.action = call->action;
            state->call.action.state = call->state;
            return pipeline_nested(state, RF_NESTED_ACTION,
                                   &state->call.action);
        }
        memset(state, 0, sizeof(*state));
        state->call.one.operation = RF_JOURNAL_CALL_ONE;
        state->call.one.action = call->action;
        state->call.one.result = call->force ? 0u : 1u;
        state->call.one.backend = execute_path.endpoint;
        state->call.one.kind = call->state->record.kind;
        state->call.one.detail = call->force ? 0u : 1u;
        state->call.one.stem = call->source_root;
        if (!pipeline_nested(state, RF_NESTED_JOURNAL,
                             &state->call.one)) return 0u;
        memset(&state->call, 0, sizeof(state->call));
        state->call.action.operation = RF_ACTION_CALL_ACK;
        state->call.action.state = call->state;
        state->call.action.succeeded = call->force;
        return pipeline_nested(state, RF_NESTED_ACTION,
                               &state->call.action);
    }
#endif
    return 0u;
}

#ifndef __CC65__
unsigned char readyfs_backend_capabilities(
    const char *text, ReadyFsBackendCapabilities *capabilities) {
    ReadyFsPath path;

    if (text == 0 || capabilities == 0 ||
        readyfs_path_parse(text, &path) != RF_PATH_OK ||
        !path.absolute || !endpoint_ok(path.endpoint)) return 0u;
    memset(capabilities, 0, sizeof(*capabilities));
    capabilities->endpoint = path.endpoint;
    capabilities->unit = path.unit;
    capabilities->partition = path.partition;
    capabilities->path_limit = RF_PATH_MAX;
    if (path.endpoint == RF_EP_IEC) {
        capabilities->leaf_limit = 16u;
        capabilities->size_units = RF_SIZE_BLOCKS;
        if (path.partition == 0u) {
            capabilities->flags = RF_CAP_READ | RF_CAP_WRITE | RF_CAP_DELETE |
                                  RF_CAP_RENAME | RF_CAP_FREE;
        } else capabilities->provisional = 1u;
    } else if (path.endpoint == RF_EP_ULTIMATE) {
        capabilities->leaf_limit = RF_PATH_MAX;
        capabilities->size_units = RF_SIZE_BYTES;
        capabilities->flags = RF_CAP_READ | RF_CAP_WRITE | RF_CAP_DELETE |
                              RF_CAP_RENAME | RF_CAP_MKDIR | RF_CAP_RECURSE |
                              RF_CAP_IMAGES | RF_CAP_MOUNT;
    } else if (path.endpoint == RF_EP_SOFTIEC) {
        capabilities->leaf_limit = RF_PATH_MAX;
        capabilities->size_units = RF_SIZE_BYTES;
        capabilities->flags = RF_CAP_READ | RF_CAP_WRITE | RF_CAP_DELETE |
                              RF_CAP_RENAME | RF_CAP_MKDIR | RF_CAP_MOUNT;
        capabilities->provisional = 1u;
    } else {
        capabilities->leaf_limit = 16u;
        capabilities->flags = RF_CAP_READ | RF_CAP_WRITE |
                              RF_CAP_SEQUENTIAL;
    }
    return 1u;
}
#endif

unsigned char readyfs_backend_selftest(void) {
    selftest_request.source_text = selftest_source;
    selftest_request.source_capacity = sizeof(selftest_source);
    selftest_request.destination_text = selftest_destination;
    selftest_request.destination_capacity = sizeof(selftest_destination);
    selftest_call.operation = RF_BACKEND_CALL_BUILD;
    selftest_call.action = RF_EXEC_ACTION_COPY_FILE;
    selftest_call.source_root = "8:/";
    selftest_call.destination_root = "u:/usb1/out";
    selftest_call.stem = "d/a.prg";
    selftest_call.request = &selftest_request;
    if (!(readyfs_backend_build(&selftest_call) &&
           selftest_request.has_source && selftest_request.has_destination &&
           selftest_request.source.endpoint == RF_EP_IEC &&
           selftest_request.destination.endpoint == RF_EP_ULTIMATE &&
           strcmp(selftest_source, "8:/d/a.prg") == 0 &&
           strcmp(selftest_destination, "u:/usb1/out/d/a.prg") == 0)) {
        return 0u;
    }
#ifdef __CC65__
    return 1u;
#else
    return 1u;
#endif
}
