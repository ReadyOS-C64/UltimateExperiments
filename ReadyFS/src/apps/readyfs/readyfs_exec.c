#include "readyfs_exec.h"

#include <string.h>

#ifdef __CC65__
#include "readyfs_reu.h"
#endif


unsigned int readyfs_exec_abi(void) { return RF_EXEC_ABI; }

#ifndef __CC65__
unsigned char readyfs_exec_init(ReadyFsExecutor *exec, ReadyFsPlan *plan,
                                unsigned char mode,
                                unsigned char stop_on_error) {
    if (exec == 0 || plan == 0 ||
        (mode != RF_EXEC_MODE_COPY && mode != RF_EXEC_MODE_MOVE &&
         mode != RF_EXEC_MODE_DELETE)) return 0u;
    memset(exec, 0, sizeof(*exec));
    exec->plan = plan;
    exec->mode = mode;
    exec->stop_on_error = stop_on_error;
    exec->pending = RF_PLAN_END;
    if (mode == RF_EXEC_MODE_DELETE) {
        exec->reverse = 1u;
        exec->cursor = plan->last;
    } else exec->cursor = readyfs_plan_first(plan);
    return 1u;
}

static unsigned char action_for(const ReadyFsExecutor *exec,
                                const ReadyFsPlanRecord *record) {
    if (exec->mode == RF_EXEC_MODE_COPY) {
        return record->kind == RF_PLAN_KIND_DIR ? RF_EXEC_ACTION_MKDIR :
                                                 RF_EXEC_ACTION_COPY_FILE;
    }
    if (exec->mode == RF_EXEC_MODE_MOVE) {
        if (exec->reverse) {
            return record->kind == RF_PLAN_KIND_DIR ? RF_EXEC_ACTION_RMDIR :
                                                     RF_EXEC_ACTION_DONE;
        }
        return record->kind == RF_PLAN_KIND_DIR ? RF_EXEC_ACTION_MKDIR :
                                                 RF_EXEC_ACTION_MOVE_FILE;
    }
    return record->kind == RF_PLAN_KIND_DIR ? RF_EXEC_ACTION_RMDIR :
                                             RF_EXEC_ACTION_DELETE_FILE;
}

static unsigned char read_pending(ReadyFsExecutor *exec,
                                  ReadyFsPlanRecord *record, char *stem,
                                  unsigned int stem_capacity) {
    unsigned int ignored;

    if (!readyfs_plan_read(exec->plan, exec->pending, record, stem,
                           stem_capacity, &ignored)) {
        exec->stopped = 1u;
        return RF_EXEC_ACTION_ERROR;
    }
    return exec->action;
}

unsigned char readyfs_exec_next(ReadyFsExecutor *exec,
                                ReadyFsPlanRecord *record, char *stem,
                                unsigned int stem_capacity) {
    unsigned int offset;
    unsigned int next;
    unsigned char action;

    if (exec == 0 || exec->plan == 0 || record == 0 || stem == 0 ||
        stem_capacity == 0u || exec->stopped) return RF_EXEC_ACTION_ERROR;
    if (exec->pending_valid) {
        return read_pending(exec, record, stem, stem_capacity);
    }
    for (;;) {
        if (exec->cursor == RF_PLAN_END) {
            if (exec->mode == RF_EXEC_MODE_MOVE && !exec->reverse) {
                exec->reverse = 1u;
                exec->cursor = exec->plan->last;
                continue;
            }
            return RF_EXEC_ACTION_DONE;
        }
        offset = exec->cursor;
        if (!readyfs_plan_read(exec->plan, offset, record, stem,
                               stem_capacity, &next)) {
            exec->stopped = 1u;
            return RF_EXEC_ACTION_ERROR;
        }
        exec->cursor = exec->reverse ? record->previous : next;
        if ((record->flags & RF_PLAN_SELECTED) == 0u ||
            record->stem_len == 0u) continue;
        action = action_for(exec, record);
        if (action == RF_EXEC_ACTION_DONE) continue;
        exec->pending = offset;
        exec->pending_valid = 1u;
        exec->action = action;
        return action;
    }
}

unsigned char readyfs_exec_ack(ReadyFsExecutor *exec,
                               unsigned char succeeded) {
    if (exec == 0 || !exec->pending_valid || exec->stopped) return 0u;
    ++exec->attempted;
    if (succeeded) ++exec->completed;
    else {
        ++exec->failed;
        if (exec->stop_on_error) exec->stopped = 1u;
    }
    exec->pending_valid = 0u;
    exec->pending = RF_PLAN_END;
    exec->action = RF_EXEC_ACTION_DONE;
    return 1u;
}

unsigned char readyfs_exec_dispatch(ReadyFsExecCall *call) {
    if (call == 0 || call->exec == 0) return 0u;
    if (call->operation == RF_EXEC_CALL_INIT) {
        return readyfs_exec_init(call->exec, call->plan, call->mode,
                                 call->stop_on_error);
    }
    if (call->operation == RF_EXEC_CALL_NEXT) {
        return readyfs_exec_next(call->exec, call->record, call->stem,
                                 call->stem_capacity);
    }
    if (call->operation == RF_EXEC_CALL_ACK) {
        return readyfs_exec_ack(call->exec, call->succeeded);
    }
    return 0u;
}
#else

/* The C64 overlay boundary is one-pointer only. In particular, do not call
 * the six-argument readyfs_plan_read() from executor code: nested cc65 stack
 * packing was proven to lose arguments. This resident-addressed call record
 * is inside OVERLAY2 but is used only while OVERLAY2 remains loaded. */
static ReadyFsPlanCall exec_plan_call;

unsigned char readyfs_exec_dispatch(ReadyFsExecCall *call) {
    ReadyFsExecutor *exec;
    unsigned int offset;
    unsigned int next;
    unsigned char action;

    if (call == 0 || call->exec == 0) return 0u;
    exec = call->exec;
    if (call->operation == RF_EXEC_CALL_INIT) {
        if (call->plan == 0 ||
            (call->mode != RF_EXEC_MODE_COPY &&
             call->mode != RF_EXEC_MODE_MOVE &&
             call->mode != RF_EXEC_MODE_DELETE)) return 0u;
        memset(exec, 0, sizeof(*exec));
        exec->plan = call->plan;
        exec->mode = call->mode;
        exec->stop_on_error = call->stop_on_error;
        exec->pending = RF_PLAN_END;
        if (call->mode == RF_EXEC_MODE_DELETE) {
            exec->reverse = 1u;
            exec->cursor = call->plan->last;
        } else exec->cursor = call->plan->count != 0u ? 0u : RF_PLAN_END;
        return 1u;
    }
    if (call->operation == RF_EXEC_CALL_ACK) {
        if (!exec->pending_valid || exec->stopped) return 0u;
        ++exec->attempted;
        if (call->succeeded) ++exec->completed;
        else {
            ++exec->failed;
            if (exec->stop_on_error) exec->stopped = 1u;
        }
        exec->pending_valid = 0u;
        exec->pending = RF_PLAN_END;
        exec->action = RF_EXEC_ACTION_DONE;
        return 1u;
    }
    if (call->operation != RF_EXEC_CALL_NEXT || exec->plan == 0 ||
        exec->stopped) {
        return RF_EXEC_ACTION_ERROR;
    }
    for (;;) {
        if (exec->pending_valid) offset = exec->pending;
        else {
            if (exec->cursor == RF_PLAN_END) {
                if (exec->mode == RF_EXEC_MODE_MOVE && !exec->reverse) {
                    exec->reverse = 1u;
                    exec->cursor = exec->plan->last;
                    continue;
                }
                return RF_EXEC_ACTION_DONE;
            }
            offset = exec->cursor;
        }
        exec_plan_call.operation = RF_PLAN_CALL_READ;
        exec_plan_call.plan = exec->plan;
        exec_plan_call.offset = offset;
        exec_plan_call.record = call->record;
        exec_plan_call.output = call->stem;
        exec_plan_call.output_capacity = call->stem_capacity;
        if (!readyfs_plan_dispatch(&exec_plan_call)) {
            exec->stopped = 1u;
            return RF_EXEC_ACTION_ERROR;
        }
        if (exec->pending_valid) return exec->action;
        next = exec_plan_call.next;
        exec->cursor = exec->reverse ? call->record->previous : next;
        if ((call->record->flags & RF_PLAN_SELECTED) == 0u ||
            call->record->stem_len == 0u) continue;
        if (exec->mode == RF_EXEC_MODE_COPY) {
            action = call->record->kind == RF_PLAN_KIND_DIR ?
                     RF_EXEC_ACTION_MKDIR : RF_EXEC_ACTION_COPY_FILE;
        } else if (exec->mode == RF_EXEC_MODE_MOVE) {
            if (exec->reverse) {
                action = call->record->kind == RF_PLAN_KIND_DIR ?
                         RF_EXEC_ACTION_RMDIR : RF_EXEC_ACTION_DONE;
            } else {
                action = call->record->kind == RF_PLAN_KIND_DIR ?
                         RF_EXEC_ACTION_MKDIR : RF_EXEC_ACTION_MOVE_FILE;
            }
        } else {
            action = call->record->kind == RF_PLAN_KIND_DIR ?
                     RF_EXEC_ACTION_RMDIR : RF_EXEC_ACTION_DELETE_FILE;
        }
        if (action == RF_EXEC_ACTION_DONE) continue;
        exec->pending = offset;
        exec->pending_valid = 1u;
        exec->action = action;
        return action;
    }
}
#endif

static ReadyFsPlanCall action_plan_call;
static ReadyFsExecCall action_exec_call;
#ifdef __CC65__
static unsigned char action_report[RF_REU_ACTION_REPORT_BYTES];
static ReadyFsActionCall action_selftest_call;
extern unsigned char readyfs_pipeline_scratch[];
#endif

/* One-pointer single-action controller. BEGIN creates a selected file token
 * and leaves the yielded action pending. ACK is a distinct later call so the
 * backend can persist RFJ1 before advancing executor state. */
unsigned char readyfs_action_dispatch(ReadyFsActionCall *call) {
    ReadyFsActionState *state;
    unsigned char kind;
    unsigned char mode;

    if (call == 0 || call->state == 0) return 0u;
    state = call->state;
    if (call->operation == RF_ACTION_CALL_BEGIN) {
        if (call->action == RF_EXEC_ACTION_MKDIR) {
            kind = RF_PLAN_KIND_DIR;
            mode = RF_EXEC_MODE_COPY;
        } else if (call->action == RF_EXEC_ACTION_COPY_FILE) {
            kind = RF_PLAN_KIND_FILE;
            mode = RF_EXEC_MODE_COPY;
        } else if (call->action == RF_EXEC_ACTION_MOVE_FILE) {
            kind = RF_PLAN_KIND_FILE;
            mode = RF_EXEC_MODE_MOVE;
        } else if (call->action == RF_EXEC_ACTION_DELETE_FILE) {
            kind = RF_PLAN_KIND_FILE;
            mode = RF_EXEC_MODE_DELETE;
        } else if (call->action == RF_EXEC_ACTION_RMDIR) {
            kind = RF_PLAN_KIND_DIR;
            mode = RF_EXEC_MODE_DELETE;
        } else return 0u;
        memset(state, 0, sizeof(*state));
        memset(&action_plan_call, 0, sizeof(action_plan_call));
        action_plan_call.operation = RF_PLAN_CALL_INIT;
        action_plan_call.plan = &state->plan;
#ifdef __CC65__
        action_plan_call.capacity = RF_REU_PLAN_BYTES;
#else
        action_plan_call.capacity = call->capacity;
        action_plan_call.write = call->write;
        action_plan_call.read = call->read;
#endif
        if (!readyfs_plan_dispatch(&action_plan_call)) return 0u;
        state->stem[0] = 0x66u;
        state->stem[1] = 0u;
        memset(&action_plan_call, 0, sizeof(action_plan_call));
        action_plan_call.operation = RF_PLAN_CALL_ADD;
        action_plan_call.plan = &state->plan;
        action_plan_call.kind = kind;
        action_plan_call.flags = RF_PLAN_SELECTED;
        action_plan_call.stem = state->stem;
        if (!readyfs_plan_dispatch(&action_plan_call)) return 0u;
        memset(&action_exec_call, 0, sizeof(action_exec_call));
        action_exec_call.operation = RF_EXEC_CALL_INIT;
        action_exec_call.mode = mode;
        action_exec_call.exec = &state->executor;
        action_exec_call.plan = &state->plan;
        if (!readyfs_exec_dispatch(&action_exec_call)) return 0u;
        memset(&action_exec_call, 0, sizeof(action_exec_call));
        action_exec_call.operation = RF_EXEC_CALL_NEXT;
        action_exec_call.exec = &state->executor;
        action_exec_call.record = &state->record;
        action_exec_call.stem = state->stem;
        action_exec_call.stem_capacity = sizeof(state->stem);
        state->action = readyfs_exec_dispatch(&action_exec_call);
        if (state->action != call->action ||
            !state->executor.pending_valid) return 0u;
#ifdef __CC65__
        return readyfs_reu_session_store(RF_REU_ACTION_OFF, state,
                                         sizeof(*state));
#else
        return 1u;
#endif
    }
#ifdef __CC65__
    if (!readyfs_reu_session_fetch(RF_REU_ACTION_OFF, state,
                                   sizeof(*state))) return 0u;
#endif
    if (call->operation != RF_ACTION_CALL_ACK ||
        !state->executor.pending_valid) return 0u;
    memset(&action_exec_call, 0, sizeof(action_exec_call));
    action_exec_call.operation = RF_EXEC_CALL_ACK;
    action_exec_call.exec = &state->executor;
    action_exec_call.succeeded = call->succeeded;
    if (!readyfs_exec_dispatch(&action_exec_call)) return 0u;
    if (state->executor.attempted != 1u ||
        state->executor.pending_valid != 0u ||
        (call->succeeded ? state->executor.completed != 1u :
                           state->executor.failed != 1u)) return 0u;
#ifdef __CC65__
    action_report[0] = 0x52u; /* R */
    action_report[1] = 0x46u; /* F */
    action_report[2] = 0x41u; /* A */
    action_report[3] = 0x31u; /* 1 */
    action_report[4] = (unsigned char)state->executor.attempted;
    action_report[5] = (unsigned char)state->executor.completed;
    action_report[6] = (unsigned char)state->executor.failed;
    action_report[7] = state->executor.pending_valid;
    return readyfs_reu_session_store(RF_REU_ACTION_REPORT_OFF,
                                     action_report, sizeof(action_report));
#else
    return 1u;
#endif
}

#ifdef __CC65__
unsigned char readyfs_action_selftest(void) {
    ReadyFsActionState *state;
    unsigned char action;

    state = (ReadyFsActionState *)readyfs_pipeline_scratch;
    for (action = RF_EXEC_ACTION_MKDIR;
         action <= RF_EXEC_ACTION_RMDIR; ++action) {
        memset(&action_selftest_call, 0, sizeof(action_selftest_call));
        action_selftest_call.operation = RF_ACTION_CALL_BEGIN;
        action_selftest_call.action = action;
        action_selftest_call.state = state;
        if (!readyfs_action_dispatch(&action_selftest_call) ||
            state->action != action || !state->executor.pending_valid) {
            return 0u;
        }
        action_selftest_call.operation = RF_ACTION_CALL_ACK;
        action_selftest_call.succeeded = 1u;
        if (!readyfs_action_dispatch(&action_selftest_call) ||
            state->executor.attempted != 1u ||
            state->executor.completed != 1u ||
            state->executor.failed != 0u ||
            state->executor.pending_valid) return 0u;
    }
    return 1u;
}
#endif
