#include "readyfs_present.h"
#include "readyfs_plan.h"
#include "readyfs_exec.h"
#include "readyfs_reu.h"
#include "readyfs_console.h"
#include <conio.h>
#include <string.h>

#include "readyfs_path.h"

/* Read-only presentation of the serialized plan. No executor START/ACK,
 * journal completion, storage I/O or mutation is performed for what-if. */
unsigned char readyfs_transfer_plan(ReadyFsUtilityCall *call) {
    unsigned char header[RF_PLAN_HEADER_BYTES];
    unsigned int cursor = 0u;
    unsigned int length, end, i;
    char *stem = call->buffer;
    const char *verb = call->argc == RF_EXEC_MODE_COPY ? "copy " :
                       call->argc == RF_EXEC_MODE_MOVE ? "move " : "delete ";
    if (!readyfs_reu_session_fetch(RF_REU_RECURSIVE_ROOTS_OFF, stem, RF_PATH_MAX + 1u)) return 0u;
    cputs("from "); cputs(stem); cputs("\r\n");
    if (call->argc != RF_EXEC_MODE_DELETE) {
        if (!readyfs_reu_session_fetch(RF_REU_RECURSIVE_ROOTS_OFF + RF_PATH_MAX + 1u, stem, RF_PATH_MAX + 1u)) return 0u;
        cputs("to   "); cputs(stem); cputs("\r\n");
    }
    for (i = 0u; i < call->value_low; ++i) {
        if (cursor > RF_REU_PLAN_BYTES - RF_PLAN_HEADER_BYTES ||
            !readyfs_reu_session_fetch(RF_REU_PLAN_OFF + cursor,
                                       header, sizeof(header))) return 0u;
        length = header[2] | ((unsigned int)header[3] << 8u);
        end = cursor + RF_PLAN_HEADER_BYTES + length + 1u;
        if ((header[0] != RF_PLAN_KIND_FILE && header[0] != RF_PLAN_KIND_DIR) ||
            length > RF_PATH_MAX || end <= cursor || end > RF_REU_PLAN_BYTES ||
            !readyfs_reu_session_fetch(RF_REU_PLAN_OFF + cursor + RF_PLAN_HEADER_BYTES,
                                       stem, length + 1u) || stem[length]) return 0u;
        cursor = end;
        if (!(header[1] & RF_PLAN_SELECTED)) continue;
        if (wherey() >= 20u) {
            cputs(RF_SUMMARY "-- more --" RF_NORMAL); cgetc(); clrscr();
        }
        cputs("would "); cputs(verb);
        if (header[0] == RF_PLAN_KIND_DIR) cputs("dir ");
        cputs(stem); cputs("\r\n");
    }
    cputs(RF_SUMMARY "whatif: no files changed\r\n");
    return 1u;
}

