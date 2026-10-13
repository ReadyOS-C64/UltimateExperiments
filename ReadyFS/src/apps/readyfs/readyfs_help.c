#include "readyfs_console.h"
#include "readyfs_help.h"

#include "readyfs_overlay.h"

#include <conio.h>

#ifdef READYFS_FULL_HELP
static unsigned char same_word(const char *left, const char *right) {
    unsigned char a;
    unsigned char b;
    while (*left != 0 && *right != 0) {
        a = (unsigned char)*left++;
        b = (unsigned char)*right++;
        if (a >= 'A' && a <= 'Z') a = (unsigned char)(a + 32u);
        if (b >= 'A' && b <= 'Z') b = (unsigned char)(b + 32u);
        if (a != b) return 0u;
    }
    return (unsigned char)(*left == 0 && *right == 0);
}

static unsigned char native_operation(const char *name) {
    if (same_word(name, "open")) return RF_CMDPATH_OPEN_FILE;
    if (same_word(name, "dir")) return RF_CMDPATH_DIRECTORY;
    if (same_word(name, "scratch")) return RF_CMDPATH_SCRATCH;
    if (same_word(name, "mkdir")) return RF_CMDPATH_MKDIR;
    if (same_word(name, "rmdir")) return RF_CMDPATH_RMDIR;
    if (same_word(name, "rename")) return RF_CMDPATH_RENAME;
    if (same_word(name, "mount")) return RF_CMDPATH_MOUNT;
    if (same_word(name, "unmount")) return RF_CMDPATH_UNMOUNT;
    return 0u;
}
#endif

unsigned int readyfs_help_abi(void) { return RF_HELP_ABI; }

void readyfs_help_show(void) {
#ifdef READYFS_FULL_HELP
    cputs("probe all|uci|udos|softiec|recover\r\n");
    cputs("drives cd dir stat status type head tail crc32\r\n");
    cputs("find alias unalias config capabilities test run\r\n");
    cputs("new write append copy move rename delete\r\n");
    cputs("mkdir rmdir mount dismount swap format\r\n");
    cputs("help command: usage and options\r\n");
    cputs("path 8:/ u:/ s3:/ t:/\r\n");
    cputs(".d81!/file\r\n");
#else
    cputs("probe drives cd dir stat type\r\n");
    cputs("new append copy move delete\r\n");
#endif
}

#ifdef READYFS_FULL_HELP
unsigned char readyfs_help_native(ReadyFsNativeUiCall *call) {
    unsigned char operation;

    if (call == 0 || call->argc < 3u) {
        cputs("native OP PATH [DEST]\r\n");
        return 1u;
    }
    operation = native_operation(call->args[1]);
    if (operation == 0u ||
        (operation == RF_CMDPATH_RENAME && call->argc < 4u)) {
        cputs(RF_ERROR "bad native op\r\n");
        return 1u;
    }
    call->path.operation = operation;
    call->path.source = call->args[2];
    call->path.destination = operation == RF_CMDPATH_RENAME ?
                             call->args[3] : 0;
    call->path.output = call->output;
    call->path.output_capacity = 256u;
    call->path.followup = call->followup;
    call->path.followup_capacity = 256u;
    call->nested.operation = RF_NESTED_CMDPATH;
    call->nested.call = &call->path;
    if (!readyfs_overlay_nested_from_backend(
            (ReadyFsNestedCall *)&call->nested)) {
        cputs(RF_ERROR "native error\r\n");
        return 1u;
    }
    cputs("native: "); cputs(call->output); cputs("\r\n");
    if (operation == RF_CMDPATH_UNMOUNT && call->followup[0] != 0) {
        cputs("then: "); cputs(call->followup); cputs("\r\n");
    }
    return 1u;
}
#endif
