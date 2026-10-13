#include <stdio.h>
#include <string.h>

#include "src/apps/readyfs/readyfs_tree.h"

static int fails;

static void check(unsigned char truth, const char *message) {
    if (!truth) {
        fprintf(stderr, "FAIL tree %s\n", message);
        ++fails;
    }
}

static void reset_call(ReadyFsTreeCall *call, char *output) {
    memset(call, 0, sizeof(*call));
    call->output = output;
    call->output_capacity = 256u;
}

int main(void) {
    ReadyFsTreeCall call;
    char output[256];
    unsigned int directory_used;

    reset_call(&call, output);
    call.operation = RF_TREE_CALL_INIT;
    call.max_depth = 2u;
    call.limit = 4u;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_OK,
          "initialize");
    check(call.queue_used == 3u, "root ledger bytes");

    call.operation = RF_TREE_CALL_NEXT;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_OK &&
          output[0] == 0 && call.depth == 0u, "yield root");

    call.operation = RF_TREE_CALL_ADD;
    call.kind = RF_TREE_KIND_DIR;
    call.parent = "";
    call.name = "one";
    call.selected = 1u;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_OK &&
          strcmp(output, "one") == 0 && call.depth == 1u,
          "add root directory");
    check(call.queue_used > 3u, "directory retained in ledger");
    directory_used = call.queue_used;

    call.kind = RF_TREE_KIND_FILE;
    call.name = "root.prg";
    call.selected = 0u;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_OK &&
          strcmp(output, "root.prg") == 0, "add filtered root file");
    check(call.queue_used > directory_used,
          "filtered file retained in ledger");

    call.operation = RF_TREE_CALL_NEXT;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_OK &&
          strcmp(output, "one") == 0 && call.depth == 1u,
          "yield queued directory");

    call.operation = RF_TREE_CALL_ADD;
    call.kind = RF_TREE_KIND_DIR;
    call.parent = "one";
    call.name = "two";
    call.selected = 1u;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_OK &&
          strcmp(output, "one/two") == 0 && call.depth == 2u,
          "add depth-two directory");

    call.kind = RF_TREE_KIND_FILE;
    call.name = "../bad";
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_BAD_NAME,
          "reject separator child");
    call.kind = RF_TREE_KIND_DIR;
    call.parent = "one/two";
    call.name = "three";
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_TOO_DEEP,
          "enforce depth bound");

    call.operation = RF_TREE_CALL_NEXT;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_OK &&
          strcmp(output, "one/two") == 0, "yield deepest directory");
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_DONE,
          "walk completes without recursion stack");

    call.operation = RF_TREE_CALL_ADD;
    call.kind = RF_TREE_KIND_FILE;
    call.parent = "one/two";
    call.name = "leaf";
    call.selected = 1u;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_OK,
          "fill exact entry limit");
    call.name = "overflow";
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_FULL,
          "reject partial entry beyond limit");

    call.operation = RF_TREE_CALL_REPORT;
    check(readyfs_tree_dispatch(&call) && call.result == RF_TREE_FULL &&
          call.entries == 4u && call.files == 2u &&
          call.directories == 2u && call.selected_entries == 3u,
          "report exact frozen counts after overflow");

    if (fails != 0) return 1;
    puts("readyfs cooperative tree tests passed");
    return 0;
}
