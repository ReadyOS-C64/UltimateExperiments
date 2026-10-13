#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_recursive.h"

static void check(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL recursive %s\n", message);
        exit(1);
    }
}

static ReadyFsRecursiveCall call;
static char stem[256];
static char source[256];
static char destination[256];
static const char *source_root = "8:/";
static const char *destination_root = "u:/usb1/out";

static void base(unsigned char operation) {
    call.operation = operation;
    call.source_root = source_root;
    call.destination_root = destination_root;
    call.stem = stem;
    call.stem_capacity = sizeof(stem);
    call.source_text = source;
    call.source_capacity = sizeof(source);
    call.destination_text = destination;
    call.destination_capacity = sizeof(destination);
}

static void add(unsigned char kind, unsigned char selected, const char *text) {
    base(RF_RECURSIVE_CALL_ADD);
    call.kind = kind;
    call.flags = selected ? RF_PLAN_SELECTED : 0u;
    strcpy(stem, text);
    check(readyfs_recursive_dispatch(&call), "add record");
}

static void ack(unsigned char succeeded) {
    base(RF_RECURSIVE_CALL_ACK);
    call.succeeded = succeeded;
    check(readyfs_recursive_dispatch(&call), "ack action");
}

static unsigned char next(void) {
    base(RF_RECURSIVE_CALL_NEXT);
    check(readyfs_recursive_dispatch(&call), "next action");
    return call.action;
}

static void copy_continue_suite(void) {
    memset(&call, 0, sizeof(call));
    base(RF_RECURSIVE_CALL_INIT);
    call.mode = RF_EXEC_MODE_COPY;
    check(readyfs_recursive_dispatch(&call), "copy init");
    add(RF_PLAN_KIND_DIR, 1u, "one");
    add(RF_PLAN_KIND_FILE, 1u, "root.prg");
    add(RF_PLAN_KIND_FILE, 1u, "one/a.prg");
    add(RF_PLAN_KIND_FILE, 0u, "skip.seq");
    base(RF_RECURSIVE_CALL_START);
    call.mode = RF_EXEC_MODE_COPY;
    call.stop_on_error = 0u;
    check(readyfs_recursive_dispatch(&call), "copy start");

    check(next() == RF_EXEC_ACTION_MKDIR && strcmp(stem, "one") == 0 &&
          strcmp(destination, "u:/usb1/out/one") == 0,
          "mkdir request");
    ack(1u);
    check(next() == RF_EXEC_ACTION_COPY_FILE &&
          strcmp(source, "8:/root.prg") == 0 &&
          strcmp(destination, "u:/usb1/out/root.prg") == 0,
          "root cross-backend request");
    check(next() == RF_EXEC_ACTION_COPY_FILE &&
          strcmp(stem, "root.prg") == 0,
          "pending action replay");
    ack(0u);
    check(next() == RF_EXEC_ACTION_COPY_FILE &&
          strcmp(source, "8:/one/a.prg") == 0 &&
          strcmp(destination, "u:/usb1/out/one/a.prg") == 0,
          "nested cross-backend request");
    ack(1u);
    check(next() == RF_EXEC_ACTION_DONE && call.attempted == 3u &&
          call.completed == 2u && call.failures == 1u,
          "copy continue totals");
}

static void move_reverse_suite(void) {
    memset(&call, 0, sizeof(call));
    base(RF_RECURSIVE_CALL_INIT);
    call.mode = RF_EXEC_MODE_MOVE;
    check(readyfs_recursive_dispatch(&call), "move init");
    add(RF_PLAN_KIND_DIR, 1u, "one");
    add(RF_PLAN_KIND_FILE, 1u, "one/a.prg");
    base(RF_RECURSIVE_CALL_START);
    call.mode = RF_EXEC_MODE_MOVE;
    check(readyfs_recursive_dispatch(&call), "move start");
    check(next() == RF_EXEC_ACTION_MKDIR, "move mkdir"); ack(1u);
    check(next() == RF_EXEC_ACTION_MOVE_FILE, "move file"); ack(1u);
    check(next() == RF_EXEC_ACTION_RMDIR && strcmp(stem, "one") == 0,
          "move reverse rmdir");
    ack(1u);
    check(next() == RF_EXEC_ACTION_DONE && call.completed == 3u,
          "move totals");
}

static void stop_suite(void) {
    memset(&call, 0, sizeof(call));
    base(RF_RECURSIVE_CALL_INIT);
    call.mode = RF_EXEC_MODE_COPY;
    check(readyfs_recursive_dispatch(&call), "stop init");
    add(RF_PLAN_KIND_FILE, 1u, "bad.prg");
    add(RF_PLAN_KIND_FILE, 1u, "never.prg");
    base(RF_RECURSIVE_CALL_START);
    call.mode = RF_EXEC_MODE_COPY;
    call.stop_on_error = 1u;
    check(readyfs_recursive_dispatch(&call), "stop start");
    check(next() == RF_EXEC_ACTION_COPY_FILE, "stop first");
    ack(0u);
    base(RF_RECURSIVE_CALL_NEXT);
    check(readyfs_recursive_dispatch(&call) &&
          call.action == RF_EXEC_ACTION_DONE &&
          (call.flags & RF_RECURSIVE_STOPPED) != 0u &&
          call.attempted == 1u && call.failures == 1u,
          "policy stop is a completed controller result");
}

static void ultimate_name_translation_suite(void) {
    unsigned char action;
    source_root = "u:/usb1/in";
    destination_root = "s0:/out";
    memset(&call, 0, sizeof(call));
    base(RF_RECURSIVE_CALL_INIT);
    call.mode = RF_EXEC_MODE_COPY;
    check(readyfs_recursive_dispatch(&call), "ultimate-name init");
    add(RF_PLAN_KIND_DIR, 1u, "[6e6573746564]");
    add(RF_PLAN_KIND_FILE, 1u, "[736661].[736571].SEQ");
    add(RF_PLAN_KIND_FILE, 1u,
        "[6e6573746564]/[696e73696465].[736571].SEQ");
    add(RF_PLAN_KIND_FILE, 1u, "[666f6f].[747874].SEQ");
    base(RF_RECURSIVE_CALL_START);
    call.mode = RF_EXEC_MODE_COPY;
    check(readyfs_recursive_dispatch(&call), "ultimate-name start");
    action = next();
    if (action != RF_EXEC_ACTION_MKDIR ||
        strcmp(destination, "s0:/out/nested") != 0) {
        fprintf(stderr, "ultimate-name first action=%u source=%s dest=%s\n",
                action, source, destination);
    }
    check(action == RF_EXEC_ACTION_MKDIR &&
          strcmp(destination, "s0:/out/nested") == 0,
          "decode directory destination only");
    ack(1u);
    check(next() == RF_EXEC_ACTION_COPY_FILE &&
          strcmp(source, "u:/usb1/in/[736661].[736571].SEQ") == 0 &&
          strcmp(destination, "s0:/out/sfa") == 0,
          "decode seq destination only");
    ack(1u);
    check(next() == RF_EXEC_ACTION_COPY_FILE &&
          strcmp(source,
                 "u:/usb1/in/[6e6573746564]/[696e73696465].[736571].SEQ") == 0 &&
          strcmp(destination, "s0:/out/nested/inside") == 0,
          "decode nested destination only");
    ack(1u);
    check(next() == RF_EXEC_ACTION_COPY_FILE &&
          strcmp(destination, "s0:/out/foo.txt") == 0,
          "preserve non-type host extension");
    ack(1u);
    check(next() == RF_EXEC_ACTION_DONE && call.completed == 4u,
          "ultimate-name totals");
    source_root = "8:/";
    destination_root = "u:/usb1/out";
}

int main(void) {
    check(readyfs_recursive_abi() == RF_RECURSIVE_ABI, "abi");
    copy_continue_suite();
    move_reverse_suite();
    stop_suite();
    ultimate_name_translation_suite();
    puts("readyfs recursive controller tests passed");
    return 0;
}
