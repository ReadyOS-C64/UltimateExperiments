#include <stdio.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_backend.h"
#include "src/apps/readyfs/readyfs_exec.h"
#include "src/apps/readyfs/readyfs_journal.h"
#include "src/apps/readyfs/readyfs_plan.h"

static unsigned char plan_storage[1024];
static unsigned char journal_storage[2048];
static int fails;

static unsigned char plan_write(unsigned int offset, const void *data,
                                unsigned int length) {
    if (offset > sizeof(plan_storage) ||
        length > sizeof(plan_storage) - offset) return 0u;
    memcpy(plan_storage + offset, data, length);
    return 1u;
}

static unsigned char plan_read(unsigned int offset, void *data,
                               unsigned int length) {
    if (offset > sizeof(plan_storage) ||
        length > sizeof(plan_storage) - offset) return 0u;
    memcpy(data, plan_storage + offset, length);
    return 1u;
}

static unsigned char journal_write(unsigned int offset, const void *data,
                                   unsigned int length) {
    if (offset > sizeof(journal_storage) ||
        length > sizeof(journal_storage) - offset) return 0u;
    memcpy(journal_storage + offset, data, length);
    return 1u;
}

static unsigned char journal_read(unsigned int offset, void *data,
                                  unsigned int length) {
    if (offset > sizeof(journal_storage) ||
        length > sizeof(journal_storage) - offset) return 0u;
    memcpy(data, journal_storage + offset, length);
    return 1u;
}

static void check(unsigned char truth, const char *message) {
    if (!truth) {
        fprintf(stderr, "FAIL pipeline %s\n", message);
        ++fails;
    }
}

static void check_single_action(unsigned char requested,
                                unsigned char expected_kind,
                                unsigned char expected_mode) {
    ReadyFsActionState state;
    ReadyFsActionCall call;

    memset(&call, 0, sizeof(call));
    call.operation = RF_ACTION_CALL_BEGIN;
    call.action = requested;
    call.state = &state;
    call.capacity = sizeof(plan_storage);
    call.write = plan_write;
    call.read = plan_read;
    check(readyfs_action_dispatch(&call), "general action begins");
    check(state.action == requested && state.record.kind == expected_kind &&
          state.executor.mode == expected_mode &&
          state.executor.pending_valid && state.executor.attempted == 0u,
          "general action yields exact pending kind/mode");
    call.operation = RF_ACTION_CALL_ACK;
    call.succeeded = 1u;
    check(readyfs_action_dispatch(&call), "general action acknowledges");
    check(state.executor.attempted == 1u &&
          state.executor.completed == 1u && state.executor.failed == 0u &&
          !state.executor.pending_valid, "general action success totals");
    check(!readyfs_action_dispatch(&call),
          "general action rejects duplicate acknowledgement");
}

int main(void) {
    ReadyFsPlan plan;
    ReadyFsPlanRecord plan_record;
    ReadyFsExecutor exec;
    ReadyFsActionState action_state;
    ReadyFsActionCall action_call;
    ReadyFsBackendRequest request;
    ReadyFsBackendCall backend_call;
    ReadyFsJournal journal;
    ReadyFsJournalRecord journal_record;
    char stem[256];
    char source[256];
    char destination[256];
    char journal_stem[256];
    unsigned int plan_offset;
    unsigned int journal_offset;
    unsigned int next;
    unsigned int sequence;
    unsigned char action;
    unsigned char result;
    unsigned char backend;

    memset(plan_storage, 0, sizeof(plan_storage));
    memset(journal_storage, 0, sizeof(journal_storage));
    readyfs_plan_init(&plan, sizeof(plan_storage), plan_write, plan_read);
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_DIR, 0u, ""),
          "add traversal root");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_DIR, RF_PLAN_SELECTED, "one"),
          "add destination directory");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, RF_PLAN_SELECTED,
                           "root.prg"), "add root file");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, RF_PLAN_SELECTED,
                           "one/a.prg"), "add nested file");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, 0u, "ignored.seq"),
          "add filtered file");

    readyfs_journal_init(&journal, RF_EXEC_MODE_COPY, sizeof(journal_storage),
                         journal_write, journal_read);
    check(journal.open && memcmp(journal_storage, "RFJ1", 4u) == 0,
          "open RFJ1 journal");
    check(readyfs_exec_init(&exec, &plan, RF_EXEC_MODE_COPY, 0u),
          "start cooperative executor");

    memset(&request, 0, sizeof(request));
    request.source_text = source;
    request.source_capacity = sizeof(source);
    request.destination_text = destination;
    request.destination_capacity = sizeof(destination);
    memset(&backend_call, 0, sizeof(backend_call));
    backend_call.operation = RF_BACKEND_CALL_BUILD;
    backend_call.source_root = "8:/";
    backend_call.destination_root =
        "u:/usb1/READYFS_TEST/owned-copy";
    backend_call.request = &request;

    sequence = 0u;
    for (;;) {
        action = readyfs_exec_next(&exec, &plan_record, stem, sizeof(stem));
        if (action == RF_EXEC_ACTION_DONE) break;
        check(action != RF_EXEC_ACTION_ERROR, "executor yields action");
        if (action == RF_EXEC_ACTION_ERROR) break;
        plan_offset = exec.pending;
        backend_call.action = action;
        backend_call.stem = stem;
        check(readyfs_backend_dispatch(&backend_call),
              "backend composes selected action");
        if (sequence == 0u) {
            check(action == RF_EXEC_ACTION_MKDIR &&
                  !request.has_source && request.has_destination &&
                  strcmp(destination,
                         "u:/usb1/READYFS_TEST/owned-copy/one") == 0,
                  "mkdir endpoint composition");
            result = 0u;
        } else if (sequence == 1u) {
            check(action == RF_EXEC_ACTION_COPY_FILE &&
                  strcmp(source, "8:/root.prg") == 0 &&
                  strcmp(destination,
                         "u:/usb1/READYFS_TEST/owned-copy/root.prg") == 0,
                  "root cross-backend copy composition");
            result = 82u; /* Inject a target status failure. */
        } else {
            check(action == RF_EXEC_ACTION_COPY_FILE &&
                  strcmp(source, "8:/one/a.prg") == 0 &&
                  strcmp(destination,
                         "u:/usb1/READYFS_TEST/owned-copy/one/a.prg") == 0,
                  "nested cross-backend copy composition");
            result = 0u;
        }
        backend = request.has_destination ? request.destination.endpoint :
                                            request.source.endpoint;
        check(readyfs_journal_append(&journal, action, result, backend,
                                     plan_record.kind, result, plan_offset,
                                     stem), "journal backend outcome");
        check(readyfs_exec_ack(&exec, result == 0u),
              "acknowledge exact pending action");
        ++sequence;
    }
    check(sequence == 3u && exec.attempted == 3u && exec.completed == 2u &&
          exec.failed == 1u, "continue policy and executor totals");
    check(journal.count == 3u && journal.completed == 2u &&
          journal.failed == 1u && readyfs_journal_finish(&journal),
          "journal totals and terminal header");

    journal_offset = readyfs_journal_first(&journal);
    sequence = 0u;
    while (journal_offset != RF_JOURNAL_END) {
        check(readyfs_journal_read(&journal, journal_offset, &journal_record,
                                   journal_stem, sizeof(journal_stem), &next),
              "read pipeline journal record");
        if (sequence == 0u) {
            check(journal_record.action == RF_EXEC_ACTION_MKDIR &&
                  journal_record.result == 0u &&
                  strcmp(journal_stem, "one") == 0,
                  "first RFJ1 action");
        } else if (sequence == 1u) {
            check(journal_record.action == RF_EXEC_ACTION_COPY_FILE &&
                  journal_record.result == 82u &&
                  journal_record.backend == RF_EP_ULTIMATE &&
                  journal_record.detail == 82u &&
                  strcmp(journal_stem, "root.prg") == 0,
                  "failed RFJ1 action retains target status");
        } else {
            check(journal_record.action == RF_EXEC_ACTION_COPY_FILE &&
                  journal_record.result == 0u &&
                  strcmp(journal_stem, "one/a.prg") == 0,
                  "last RFJ1 action");
        }
        journal_offset = next;
        ++sequence;
    }
    check(sequence == 3u && journal_storage[6] == 0u,
          "closed RFJ1 stream is complete and replayable");

    memset(plan_storage, 0, sizeof(plan_storage));
    memset(&action_call, 0, sizeof(action_call));
    action_call.operation = RF_ACTION_CALL_BEGIN;
    action_call.action = RF_EXEC_ACTION_COPY_FILE;
    action_call.state = &action_state;
    action_call.capacity = sizeof(plan_storage);
    action_call.write = plan_write;
    action_call.read = plan_read;
    check(readyfs_action_dispatch(&action_call),
          "single-action controller begins");
    check(action_state.plan.count == 1u &&
          action_state.plan.selected_files == 1u &&
          action_state.action == RF_EXEC_ACTION_COPY_FILE &&
          action_state.executor.pending_valid &&
          action_state.executor.attempted == 0u,
          "single-action controller yields pending copy");
    action_call.operation = RF_ACTION_CALL_ACK;
    action_call.succeeded = 1u;
    check(readyfs_action_dispatch(&action_call),
          "single-action controller acknowledges success");
    check(action_state.executor.attempted == 1u &&
          action_state.executor.completed == 1u &&
          action_state.executor.failed == 0u &&
          !action_state.executor.pending_valid,
          "single-action success totals");
    check(!readyfs_action_dispatch(&action_call),
          "single-action controller rejects duplicate acknowledgement");

    action_call.operation = RF_ACTION_CALL_BEGIN;
    check(readyfs_action_dispatch(&action_call),
          "single-action controller restarts");
    action_call.operation = RF_ACTION_CALL_ACK;
    action_call.succeeded = 0u;
    check(readyfs_action_dispatch(&action_call),
          "single-action controller acknowledges failure");
    check(action_state.executor.attempted == 1u &&
          action_state.executor.completed == 0u &&
          action_state.executor.failed == 1u &&
          !action_state.executor.pending_valid,
          "single-action failure totals");

    check_single_action(RF_EXEC_ACTION_MKDIR, RF_PLAN_KIND_DIR,
                        RF_EXEC_MODE_COPY);
    check_single_action(RF_EXEC_ACTION_MOVE_FILE, RF_PLAN_KIND_FILE,
                        RF_EXEC_MODE_MOVE);
    check_single_action(RF_EXEC_ACTION_DELETE_FILE, RF_PLAN_KIND_FILE,
                        RF_EXEC_MODE_DELETE);
    check_single_action(RF_EXEC_ACTION_RMDIR, RF_PLAN_KIND_DIR,
                        RF_EXEC_MODE_DELETE);

    if (fails != 0) return 1;
    puts("readyfs pipeline tests passed");
    return 0;
}
