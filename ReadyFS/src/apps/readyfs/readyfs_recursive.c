#include "readyfs_recursive.h"

#include "readyfs_journal.h"
#include "readyfs_overlay.h"
#include "readyfs_plan.h"
#include "readyfs_reu.h"

#include <string.h>


typedef struct {
    ReadyFsPlan plan;
    ReadyFsExecutor executor;
    ReadyFsJournal journal;
    unsigned char magic;
    unsigned char started;
    unsigned char finished;
    unsigned char current_action;
    unsigned char current_backend;
    unsigned char current_kind;
} ReadyFsRecursiveState;

typedef union {
    ReadyFsPlanCall plan;
    ReadyFsExecCall exec;
    ReadyFsJournalCall journal;
    ReadyFsBackendCall backend;
} ReadyFsRecursiveNestedCall;

typedef struct {
    ReadyFsRecursiveState state;
    ReadyFsNestedCall nested;
    ReadyFsRecursiveNestedCall call;
    ReadyFsPlanRecord record;
    ReadyFsBackendRequest request;
} ReadyFsRecursiveScratch;

#define RF_RECURSIVE_MAGIC 0x58u

#ifdef __CC65__
extern unsigned char readyfs_pipeline_scratch[RF_PIPELINE_SCRATCH_BYTES];
typedef char ReadyFsRecursiveScratchFits[
    sizeof(ReadyFsRecursiveScratch) <= RF_PIPELINE_SCRATCH_BYTES];
#else
static ReadyFsRecursiveScratch host_scratch;
static unsigned char host_plan[RF_REU_PLAN_BYTES];
static unsigned char host_journal[RF_REU_JOURNAL_BYTES];

static unsigned char host_plan_write(unsigned int offset, const void *data,
                                     unsigned int length) {
    if (offset > sizeof(host_plan) ||
        length > (unsigned int)(sizeof(host_plan) - offset)) return 0u;
    memcpy(host_plan + offset, data, length);
    return 1u;
}

static unsigned char host_plan_read(unsigned int offset, void *data,
                                    unsigned int length) {
    if (offset > sizeof(host_plan) ||
        length > (unsigned int)(sizeof(host_plan) - offset)) return 0u;
    memcpy(data, host_plan + offset, length);
    return 1u;
}

static unsigned char host_journal_write(unsigned int offset, const void *data,
                                        unsigned int length) {
    if (offset > sizeof(host_journal) ||
        length > (unsigned int)(sizeof(host_journal) - offset)) return 0u;
    memcpy(host_journal + offset, data, length);
    return 1u;
}

static unsigned char host_journal_read(unsigned int offset, void *data,
                                       unsigned int length) {
    if (offset > sizeof(host_journal) ||
        length > (unsigned int)(sizeof(host_journal) - offset)) return 0u;
    memcpy(data, host_journal + offset, length);
    return 1u;
}
#endif

unsigned int readyfs_recursive_abi(void) { return RF_RECURSIVE_ABI; }

static ReadyFsRecursiveScratch *scratch(void) {
#ifdef __CC65__
    return (ReadyFsRecursiveScratch *)readyfs_pipeline_scratch;
#else
    return &host_scratch;
#endif
}

static unsigned char state_store(ReadyFsRecursiveScratch *work) {
#ifdef __CC65__
    return readyfs_reu_session_store(RF_REU_RECURSIVE_OFF, &work->state,
                                     sizeof(work->state));
#else
    (void)work;
    return 1u;
#endif
}

static unsigned char state_fetch(ReadyFsRecursiveScratch *work) {
#ifdef __CC65__
    return readyfs_reu_session_fetch(RF_REU_RECURSIVE_OFF, &work->state,
                                     sizeof(work->state));
#else
    (void)work;
    return 1u;
#endif
}

static unsigned char nested(ReadyFsRecursiveScratch *work,
                            unsigned char operation, void *call) {
#ifdef __CC65__
    work->nested.operation = operation | RF_NESTED_RESIDENT;
    work->nested.call = call;
    return readyfs_overlay_nested_from_backend(&work->nested);
#else
    (void)work;
    if (operation == RF_NESTED_PLAN)
        return readyfs_plan_dispatch((ReadyFsPlanCall *)call);
    if (operation == RF_NESTED_EXEC)
        return readyfs_exec_dispatch((ReadyFsExecCall *)call);
    if (operation == RF_NESTED_JOURNAL)
        return readyfs_journal_dispatch((ReadyFsJournalCall *)call);
    if (operation == RF_NESTED_BACKEND)
        return readyfs_backend_dispatch((ReadyFsBackendCall *)call);
    return 0u;
#endif
}

#ifdef __CC65__
extern void __fastcall__ readyfs_recursive_decode_name(char *text);
extern void __fastcall__ readyfs_recursive_strip_type(char *text);

static void decode_ultimate_stem(char *text, unsigned char file) {
    readyfs_recursive_decode_name(text);
    if (file) readyfs_recursive_strip_type(text);
}
#else
static unsigned char hex_value(unsigned char value) {
    if (value >= '0' && value <= '9') return (unsigned char)(value - '0');
    if (value >= 'a' && value <= 'f')
        return (unsigned char)(value - 'a' + 10u);
    if (value >= 'A' && value <= 'F')
        return (unsigned char)(value - 'A' + 10u);
    return 0xFFu;
}

static unsigned char lower_ascii(unsigned char value) {
    return (value >= 'A' && value <= 'Z') ?
           (unsigned char)(value + ('a' - 'A')) : value;
}

static unsigned char type_suffix(const char *start, const char *end) {
    unsigned char a;
    unsigned char b;
    unsigned char c;

    if ((unsigned int)(end - start) < 4u || end[-4] != '.') return 0u;
    a = lower_ascii((unsigned char)end[-3]);
    b = lower_ascii((unsigned char)end[-2]);
    c = lower_ascii((unsigned char)end[-1]);
    if (a == 's' && b == 'e' && c == 'q') return 1u;
    if (a == 'p' && b == 'r' && c == 'g') return 2u;
    if (a == 'u' && b == 's' && c == 'r') return 3u;
    if (a == 'r' && b == 'e' && c == 'l') return 4u;
    return 0u;
}

/* UltimateDOS READ_DIR uses bracketed hex as an access spelling for host
 * bytes that are not safe in its C64-facing name field, then appends a type
 * suffix. Keep that spelling on the Ultimate source path, but turn the
 * destination stem back into a normal C64 name for IEC/SoftwareIEC targets.
 * Decoding is in-place and can only shorten the request. */
static void decode_ultimate_stem(char *text, unsigned char file) {
    char *read;
    char *write;
    char *close;
    char *scan;
    char *end;
    char *component;
    unsigned char high;
    unsigned char low;
    unsigned char type;

    read = write = text;
    while (*read != 0) {
        if (*read == '[') {
            close = strchr(read + 1, ']');
            if (close != 0 && ((unsigned int)(close - read) & 1u) != 0u) {
                scan = read + 1;
                while (scan < close) {
                    high = hex_value((unsigned char)scan[0]);
                    low = hex_value((unsigned char)scan[1]);
                    if (high == 0xFFu || low == 0xFFu) break;
                    *write++ = (char)((high << 4u) | low);
                    scan += 2;
                }
                if (scan == close) { read = close + 1; continue; }
            }
        }
        *write++ = *read++;
    }
    *write = 0;
    if (!file) return;
    component = strrchr(text, '/');
    component = component == 0 ? text : component + 1;
    end = component + strlen(component);
    type = type_suffix(component, end);
    if (type == 0u) return;
    end[-4] = 0; /* UltimateDOS type annotation. */
    end -= 4;
    if (type_suffix(component, end) == type) end[-4] = 0;
}
#endif

static void report(ReadyFsRecursiveCall *call,
                   const ReadyFsRecursiveState *state) {
    call->attempted = state->executor.attempted;
    call->completed = state->executor.completed;
    call->failures = state->executor.failed;
    call->flags = state->executor.stopped ? RF_RECURSIVE_STOPPED : 0u;
}

static unsigned char initialize(ReadyFsRecursiveCall *outer,
                                ReadyFsRecursiveScratch *work) {
    memset(work, 0, sizeof(*work));
    work->state.magic = RF_RECURSIVE_MAGIC;
    memset(&work->call, 0, sizeof(work->call));
    work->call.plan.operation = RF_PLAN_CALL_INIT;
    work->call.plan.plan = &work->state.plan;
    work->call.plan.capacity = RF_REU_PLAN_BYTES;
#ifndef __CC65__
    work->call.plan.write = host_plan_write;
    work->call.plan.read = host_plan_read;
#endif
    if (!nested(work, RF_NESTED_PLAN, &work->call.plan)) return 0u;
    memset(&work->call, 0, sizeof(work->call));
    work->call.journal.operation = RF_JOURNAL_CALL_INIT;
    work->call.journal.mode = outer->mode;
    work->call.journal.journal = &work->state.journal;
    work->call.journal.capacity = RF_REU_JOURNAL_BYTES;
#ifdef __CC65__
    work->call.journal.write = readyfs_reu_session_store;
    work->call.journal.read = readyfs_reu_session_fetch;
#else
    work->call.journal.write = host_journal_write;
    work->call.journal.read = host_journal_read;
#endif
    if (!nested(work, RF_NESTED_JOURNAL, &work->call.journal)) return 0u;
    return state_store(work);
}

static unsigned char add_record(ReadyFsRecursiveCall *outer,
                                ReadyFsRecursiveScratch *work) {
    if (outer->stem == 0 || !state_fetch(work) ||
        work->state.magic != RF_RECURSIVE_MAGIC || work->state.started) {
        return 0u;
    }
    memset(&work->call, 0, sizeof(work->call));
    work->call.plan.operation = RF_PLAN_CALL_ADD;
    work->call.plan.plan = &work->state.plan;
    work->call.plan.kind = outer->kind;
    work->call.plan.flags = outer->flags;
    work->call.plan.stem = outer->stem;
    if (!nested(work, RF_NESTED_PLAN, &work->call.plan)) return 0u;
    return state_store(work);
}

#ifdef __CC65__
static unsigned char import_tree(ReadyFsRecursiveCall *outer,
                                 ReadyFsRecursiveScratch *work) {
    unsigned char header[2];
    unsigned int cursor;
    unsigned int bytes;
    unsigned int entries;
    unsigned int selected;

    if (outer->stem == 0 || outer->stem_capacity == 0u ||
        outer->attempted < 3u || outer->attempted > RF_REU_TREE_QUEUE_BYTES) {
        return 0u;
    }
    cursor = entries = selected = 0u;
    while (cursor < outer->attempted) {
        if (cursor > RF_REU_TREE_QUEUE_BYTES - 2u ||
            !readyfs_reu_overlay_fetch(
                (unsigned int)(RF_REU_TREE_QUEUE_OFF + cursor), header, 2u)) {
            return 0u;
        }
        bytes = (unsigned int)header[0] + 1u;
        if (bytes > outer->stem_capacity ||
            bytes + 2u > (unsigned int)(outer->attempted - cursor) ||
            !readyfs_reu_overlay_fetch(
                (unsigned int)(RF_REU_TREE_QUEUE_OFF + cursor + 2u),
                outer->stem, bytes) || outer->stem[bytes - 1u] != 0) {
            return 0u;
        }
        cursor = (unsigned int)(cursor + bytes + 2u);
        if (bytes == 1u) continue;
        outer->kind = (header[1] & 0x80u) ? RF_PLAN_KIND_FILE :
                                                 RF_PLAN_KIND_DIR;
        outer->flags = (header[1] & 0x40u) ? RF_PLAN_SELECTED : 0u;
        if (!add_record(outer, work)) return 0u;
        ++entries;
        if (outer->flags) ++selected;
    }
    outer->attempted = entries;
    outer->completed = selected;
    return 1u;
}
#endif

static unsigned char start(ReadyFsRecursiveCall *outer,
                           ReadyFsRecursiveScratch *work) {
    if (!state_fetch(work) || work->state.magic != RF_RECURSIVE_MAGIC ||
        work->state.started) return 0u;
    memset(&work->call, 0, sizeof(work->call));
    work->call.exec.operation = RF_EXEC_CALL_INIT;
    work->call.exec.mode = outer->mode;
    work->call.exec.stop_on_error = outer->stop_on_error;
    work->call.exec.exec = &work->state.executor;
    work->call.exec.plan = &work->state.plan;
    if (!nested(work, RF_NESTED_EXEC, &work->call.exec)) return 0u;
    work->state.started = 1u;
    return state_store(work);
}

static unsigned char finish(ReadyFsRecursiveCall *outer,
                            ReadyFsRecursiveScratch *work) {
    memset(&work->call, 0, sizeof(work->call));
    work->call.journal.operation = RF_JOURNAL_CALL_FINISH;
    work->call.journal.journal = &work->state.journal;
    if (!nested(work, RF_NESTED_JOURNAL, &work->call.journal)) return 0u;
    work->state.finished = 1u;
    outer->action = RF_EXEC_ACTION_DONE;
    report(outer, &work->state);
    return state_store(work);
}

static unsigned char next_action(ReadyFsRecursiveCall *outer,
                                 ReadyFsRecursiveScratch *work) {
    unsigned char action;
    if (outer->stem == 0 || outer->stem_capacity == 0u ||
        outer->source_root == 0 || !state_fetch(work) ||
        work->state.magic != RF_RECURSIVE_MAGIC || !work->state.started ||
        work->state.finished) return 0u;
    memset(&work->call, 0, sizeof(work->call));
    work->call.exec.operation = RF_EXEC_CALL_NEXT;
    work->call.exec.exec = &work->state.executor;
    work->call.exec.record = &work->record;
    work->call.exec.stem = outer->stem;
    work->call.exec.stem_capacity = outer->stem_capacity;
    action = nested(work, RF_NESTED_EXEC, &work->call.exec);
    if (action == RF_EXEC_ACTION_DONE) return finish(outer, work);
    if (action == RF_EXEC_ACTION_ERROR) {
        work->state.executor.stopped = 1u;
        /* A policy stop is a completed controller outcome, not an overlay or
         * transport failure. Surface DONE+stopped so another batch can start
         * in the same shell session without treating this as lost capability. */
        return finish(outer, work);
    }
    work->request.source_text = outer->source_text;
    work->request.source_capacity = outer->source_capacity;
    work->request.destination_text = outer->destination_text;
    work->request.destination_capacity = outer->destination_capacity;
    memset(&work->call, 0, sizeof(work->call));
    work->call.backend.operation = RF_BACKEND_CALL_BUILD;
    work->call.backend.action = action;
    work->call.backend.source_root = outer->source_root;
    work->call.backend.destination_root = outer->destination_root;
    work->call.backend.stem = outer->stem;
    work->call.backend.request = &work->request;
    if (!nested(work, RF_NESTED_BACKEND, &work->call.backend)) return 0u;
    if (work->request.has_destination && outer->source_root[1] == ':' &&
        (outer->source_root[0] == 'u' || outer->source_root[0] == 'U') &&
        work->request.destination.endpoint != RF_EP_ULTIMATE) {
        unsigned int root_length;
        char *relative;
        root_length = strlen(outer->destination_root);
        relative = outer->destination_text + root_length;
        if (*relative == '/') ++relative;
        decode_ultimate_stem(relative,
                             work->record.kind == RF_PLAN_KIND_FILE);
    }
    work->state.current_action = action;
    work->state.current_kind = work->record.kind;
    work->state.current_backend = work->request.has_destination ?
        work->request.destination.endpoint : work->request.source.endpoint;
    outer->action = action;
    report(outer, &work->state);
    return state_store(work);
}

static unsigned char acknowledge(ReadyFsRecursiveCall *outer,
                                 ReadyFsRecursiveScratch *work) {
    unsigned char action;
    if (outer->stem == 0 || outer->stem_capacity == 0u ||
        !state_fetch(work) || work->state.magic != RF_RECURSIVE_MAGIC ||
        !work->state.started || work->state.finished ||
        !work->state.executor.pending_valid) return 0u;
    memset(&work->call, 0, sizeof(work->call));
    work->call.exec.operation = RF_EXEC_CALL_NEXT;
    work->call.exec.exec = &work->state.executor;
    work->call.exec.record = &work->record;
    work->call.exec.stem = outer->stem;
    work->call.exec.stem_capacity = outer->stem_capacity;
    action = nested(work, RF_NESTED_EXEC, &work->call.exec);
    if (action != work->state.current_action) return 0u;
    memset(&work->call, 0, sizeof(work->call));
    work->call.journal.operation = RF_JOURNAL_CALL_APPEND;
    work->call.journal.journal = &work->state.journal;
    work->call.journal.action = action;
    work->call.journal.result = outer->succeeded ? 0u : 1u;
    work->call.journal.backend = work->state.current_backend;
    work->call.journal.kind = work->state.current_kind;
    work->call.journal.detail = outer->succeeded ? 0u : 1u;
    work->call.journal.plan_offset = work->state.executor.pending;
    work->call.journal.stem = outer->stem;
    if (!nested(work, RF_NESTED_JOURNAL, &work->call.journal)) return 0u;
    memset(&work->call, 0, sizeof(work->call));
    work->call.exec.operation = RF_EXEC_CALL_ACK;
    work->call.exec.exec = &work->state.executor;
    work->call.exec.succeeded = outer->succeeded;
    if (!nested(work, RF_NESTED_EXEC, &work->call.exec)) return 0u;
    work->state.current_action = RF_EXEC_ACTION_DONE;
    report(outer, &work->state);
    return state_store(work);
}

unsigned char readyfs_recursive_dispatch(ReadyFsRecursiveCall *call) {
    ReadyFsRecursiveScratch *work;
    if (call == 0) return 0u;
    work = scratch();
    if (call->operation == RF_RECURSIVE_CALL_INIT) return initialize(call, work);
    if (call->operation == RF_RECURSIVE_CALL_ADD) return add_record(call, work);
    if (call->operation == RF_RECURSIVE_CALL_START) return start(call, work);
    if (call->operation == RF_RECURSIVE_CALL_NEXT) return next_action(call, work);
    if (call->operation == RF_RECURSIVE_CALL_ACK) return acknowledge(call, work);
#ifdef __CC65__
    if (call->operation == RF_RECURSIVE_CALL_IMPORT_TREE)
        return import_tree(call, work);
#endif
    return 0u;
}
