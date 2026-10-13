#include <stdio.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_plan.h"
#include "src/apps/readyfs/readyfs_walk.h"
#include "src/apps/readyfs/readyfs_exec.h"

static unsigned char storage[512];
static int fails;

static unsigned char write_plan(unsigned int offset, const void *data,
                                unsigned int length) {
    if (offset > sizeof(storage) || length > sizeof(storage) - offset) return 0u;
    memcpy(storage + offset, data, length);
    return 1u;
}

static unsigned char read_plan(unsigned int offset, void *data,
                               unsigned int length) {
    if (offset > sizeof(storage) || length > sizeof(storage) - offset) return 0u;
    memcpy(data, storage + offset, length);
    return 1u;
}

static void check(unsigned char truth, const char *message) {
    if (!truth) {
        fprintf(stderr, "FAIL plan %s\n", message);
        ++fails;
    }
}

int main(void) {
    ReadyFsPlan plan;
    ReadyFsPlanRecord record;
    char stem[256];
    char too_long[257];
    unsigned int cursor;
    unsigned int next;
    unsigned int second;
    unsigned int used;
    ReadyFsWalk walk;
    ReadyFsPlanCall call;
    ReadyFsExecutor exec;
    ReadyFsExecCall exec_call;
    unsigned char action;
    unsigned char depth;
    unsigned char rc;

    memset(storage, 0xA5, sizeof(storage));
    readyfs_plan_init(&plan, sizeof(storage), write_plan, read_plan);
    check(readyfs_plan_first(&plan) == RF_PLAN_END, "empty first");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_DIR, RF_PLAN_SELECTED, ""),
          "add root");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_DIR, 0u, "one"), "add dir");
    second = plan.last;
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, RF_PLAN_SELECTED,
                           "one/file.prg"), "add file");
    check(plan.count == 3u && plan.files == 1u && plan.directories == 2u &&
          plan.selected_files == 1u && plan.selected_directories == 1u,
          "counters");

    cursor = readyfs_plan_first(&plan);
    check(readyfs_plan_read(&plan, cursor, &record, stem, sizeof(stem), &next) &&
          record.kind == RF_PLAN_KIND_DIR && stem[0] == 0 &&
          record.previous == RF_PLAN_END, "read root");
    cursor = next;
    check(cursor == second &&
          readyfs_plan_read(&plan, cursor, &record, stem, sizeof(stem), &next) &&
          strcmp(stem, "one") == 0 && record.previous == 0u, "read second");
    cursor = next;
    check(readyfs_plan_read(&plan, cursor, &record, stem, sizeof(stem), &next) &&
          strcmp(stem, "one/file.prg") == 0 && next == RF_PLAN_END &&
          record.previous == second, "read last");

    used = plan.used;
    memset(too_long, 'x', sizeof(too_long));
    too_long[256] = 0;
    check(!readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, 0u, too_long) &&
          plan.used == used, "reject overlong stem atomically");

    readyfs_plan_init(&plan, 12u, write_plan, read_plan);
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, 0u, "abcd"),
          "exact bounded add");
    used = plan.used;
    check(!readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, 0u, "x") &&
          plan.overflow && plan.used == used && plan.count == 1u,
          "capacity overflow is pre-mutation");

    readyfs_plan_init(&plan, sizeof(storage), write_plan, read_plan);
    readyfs_walk_init(&walk, &plan, 2u);
    check(readyfs_walk_seed(&walk, 1u) == RF_WALK_OK, "walk seed");
    check(readyfs_walk_next_directory(&walk, stem, sizeof(stem), &depth) ==
          RF_WALK_OK && stem[0] == 0 && depth == 0u, "walk root");
    check(readyfs_walk_add_child(&walk, "", "one", RF_PLAN_KIND_DIR, 1u,
                                 stem, sizeof(stem)) == RF_WALK_OK,
          "walk add directory");
    check(readyfs_walk_add_child(&walk, "", "root.prg", RF_PLAN_KIND_FILE,
                                 0u, stem, sizeof(stem)) == RF_WALK_OK,
          "walk add filtered file");
    check(readyfs_walk_next_directory(&walk, stem, sizeof(stem), &depth) ==
          RF_WALK_OK && strcmp(stem, "one") == 0 && depth == 1u,
          "walk queued directory");
    check(readyfs_walk_add_child(&walk, "one", "two", RF_PLAN_KIND_DIR, 1u,
                                 stem, sizeof(stem)) == RF_WALK_OK,
          "walk add depth two");
    rc = readyfs_walk_add_child(&walk, "one/two", "three",
                                RF_PLAN_KIND_DIR, 1u, stem, sizeof(stem));
    check(rc == RF_WALK_TOO_DEEP, "walk depth bound");
    check(readyfs_walk_add_child(&walk, "one", "../bad", RF_PLAN_KIND_FILE,
                                 1u, stem, sizeof(stem)) == RF_WALK_BAD_NAME,
          "walk rejects separator child");
    check(readyfs_walk_next_directory(&walk, stem, sizeof(stem), &depth) ==
          RF_WALK_OK && strcmp(stem, "one/two") == 0 && depth == 2u,
          "walk deepest queued directory");
    check(readyfs_walk_next_directory(&walk, stem, sizeof(stem), &depth) ==
          RF_WALK_DONE, "walk done without recursion stack");

    memset(&call, 0, sizeof(call));
    call.operation = RF_PLAN_CALL_READ;
    call.plan = &plan;
    call.offset = 0u;
    call.record = &record;
    call.output = stem;
    call.output_capacity = sizeof(stem);
    check(readyfs_plan_dispatch(&call) && record.kind == RF_PLAN_KIND_DIR &&
          stem[0] == 0, "dispatch read");

    readyfs_plan_init(&plan, sizeof(storage), write_plan, read_plan);
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_DIR, RF_PLAN_SELECTED, ""),
          "exec add sentinel root");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_DIR, RF_PLAN_SELECTED, "one"),
          "exec add selected dir");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, RF_PLAN_SELECTED,
                           "root.prg"), "exec add root file");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, RF_PLAN_SELECTED,
                           "one/a.prg"), "exec add nested file");
    check(readyfs_plan_add(&plan, RF_PLAN_KIND_FILE, 0u, "skip.seq"),
          "exec add filtered file");

    check(readyfs_exec_init(&exec, &plan, RF_EXEC_MODE_COPY, 1u),
          "copy executor init");
    action = readyfs_exec_next(&exec, &record, stem, sizeof(stem));
    check(action == RF_EXEC_ACTION_MKDIR && strcmp(stem, "one") == 0,
          "copy mkdir first");
    action = readyfs_exec_next(&exec, &record, stem, sizeof(stem));
    check(action == RF_EXEC_ACTION_MKDIR && strcmp(stem, "one") == 0,
          "pending action replays until ack");
    check(readyfs_exec_ack(&exec, 1u), "ack mkdir");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_COPY_FILE && strcmp(stem, "root.prg") == 0,
          "copy root file");
    check(readyfs_exec_ack(&exec, 1u), "ack root copy");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_COPY_FILE && strcmp(stem, "one/a.prg") == 0,
          "copy nested file");
    check(readyfs_exec_ack(&exec, 1u), "ack nested copy");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_DONE && exec.completed == 3u && exec.failed == 0u,
          "copy skips sentinel and filtered records");

    check(readyfs_exec_init(&exec, &plan, RF_EXEC_MODE_MOVE, 1u),
          "move executor init");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_MKDIR, "move mkdir destination");
    check(readyfs_exec_ack(&exec, 1u), "ack move mkdir");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_MOVE_FILE && strcmp(stem, "root.prg") == 0,
          "move root file");
    check(readyfs_exec_ack(&exec, 1u), "ack root move");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_MOVE_FILE && strcmp(stem, "one/a.prg") == 0,
          "move nested file");
    check(readyfs_exec_ack(&exec, 1u), "ack nested move");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_RMDIR && strcmp(stem, "one") == 0,
          "move removes source dirs in reverse phase");
    check(readyfs_exec_ack(&exec, 1u), "ack source rmdir");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_DONE, "move done");

    check(readyfs_exec_init(&exec, &plan, RF_EXEC_MODE_DELETE, 1u),
          "delete executor init");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_DELETE_FILE && strcmp(stem, "one/a.prg") == 0,
          "delete nested file first");
    check(readyfs_exec_ack(&exec, 1u), "ack nested delete");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_DELETE_FILE && strcmp(stem, "root.prg") == 0,
          "delete root file second");
    check(readyfs_exec_ack(&exec, 1u), "ack root delete");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_RMDIR && strcmp(stem, "one") == 0,
          "delete directory last");
    check(readyfs_exec_ack(&exec, 1u), "ack delete rmdir");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_DONE, "delete done");

    check(readyfs_exec_init(&exec, &plan, RF_EXEC_MODE_COPY, 1u),
          "stop-on-error init");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_MKDIR && readyfs_exec_ack(&exec, 0u),
          "record failed action");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_ERROR && exec.failed == 1u,
          "stop policy blocks later actions");

    check(readyfs_exec_init(&exec, &plan, RF_EXEC_MODE_COPY, 0u),
          "continue-on-error init");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_MKDIR && readyfs_exec_ack(&exec, 0u),
          "continue policy records failure");
    check(readyfs_exec_next(&exec, &record, stem, sizeof(stem)) ==
          RF_EXEC_ACTION_COPY_FILE && strcmp(stem, "root.prg") == 0,
          "continue policy advances");

    memset(&exec_call, 0, sizeof(exec_call));
    exec_call.operation = RF_EXEC_CALL_INIT;
    exec_call.exec = &exec;
    exec_call.plan = &plan;
    exec_call.mode = RF_EXEC_MODE_DELETE;
    exec_call.stop_on_error = 1u;
    check(readyfs_exec_dispatch(&exec_call), "executor dispatcher init");
    exec_call.operation = RF_EXEC_CALL_NEXT;
    exec_call.record = &record;
    exec_call.stem = stem;
    exec_call.stem_capacity = sizeof(stem);
    check(readyfs_exec_dispatch(&exec_call) == RF_EXEC_ACTION_DELETE_FILE &&
          strcmp(stem, "one/a.prg") == 0, "executor dispatcher next");
    exec_call.operation = RF_EXEC_CALL_ACK;
    exec_call.succeeded = 1u;
    check(readyfs_exec_dispatch(&exec_call), "executor dispatcher ack");

    if (fails != 0) return 1;
    puts("readyfs plan tests passed");
    return 0;
}
