#include "readyfs_console.h"
#include "readyfs_driveui.h"

#include "readyfs_driver.h"
#include "readyfs_cmdpath.h"
#include "readyfs_path.h"
#include "readyfs_reu.h"
#include "readyfs_overlay.h"

#include <conio.h>
#include <string.h>

unsigned int readyfs_driveui_abi(void) { return RF_DRIVEUI_ABI; }

/* cc65 character literals use PETSCII: source 'i' is $49 while shifted
 * keyboard input can arrive as $C9.  Clear the PETSCII case bit; ASCII's
 * OR-$20 folding would make every ordinary C64 uppercase command miss. */
#define FOLD_CHAR(value) ((unsigned char)(value) & 0x7Fu)

static unsigned char operation_code(const char *name) {
    unsigned char first;
    unsigned char second;
    first = (unsigned char)name[0];
    second = (unsigned char)name[1];
    first = FOLD_CHAR(first);
    second = FOLD_CHAR(second);
    if (first == 'o') return RF_CMDPATH_OPEN_FILE;
    if (first == 'd') return RF_CMDPATH_DIRECTORY;
    if (first == 's') return RF_CMDPATH_SCRATCH;
    if (first == 'u') return RF_CMDPATH_UNMOUNT;
    if (first == 'm') return second == 'o' ? RF_CMDPATH_MOUNT :
                                            RF_CMDPATH_MKDIR;
    if (first == 'r') return second == 'e' ? RF_CMDPATH_RENAME :
                                            RF_CMDPATH_RMDIR;
    return 0u;
}

static void print_profile(unsigned char kind) {
    static const char * const names[] = {
        "unknown", "legacy", "sd2iec", "cmd", "pi1541", "ultimate", "softiec"
    };
    cputs(names[kind <= RF_DRIVER_SOFTIEC ? kind : 0u]);
}

static unsigned char parse_drive(ReadyFsDriveUiCall *call,
                                 ReadyFsPath *path) {
    const char *kind;
    kind = call->args[1];
    if (call->argc < 3u ||
        FOLD_CHAR(kind[0]) != 'i' ||
        FOLD_CHAR(kind[1]) != 'e' ||
        FOLD_CHAR(kind[2]) != 'c' || kind[3] != 0 ||
        readyfs_path_parse(call->args[2], path) != RF_PATH_OK ||
        path->endpoint != RF_EP_IEC || path->partition != 0u ||
        call->args[2][path->path_offset] != 0) return 0u;
    call->device = path->unit;
    return 1u;
}

static unsigned int profile_offset(unsigned char device) {
    return (unsigned int)(RF_REU_DRIVE_PROFILE_OFF +
           (unsigned char)((device - 8u) << 2));
}

unsigned char readyfs_driveui_reset(void) {
    unsigned char device;
    unsigned char record[4];
    memset(record, 0, sizeof(record));
    for (device = 8u; device <= 30u; ++device) {
        if (!readyfs_reu_session_store(profile_offset(device), record, 4u)) {
            return 0u;
        }
    }
    return 1u;
}

static unsigned char profile_store(ReadyFsDriveUiCall *call) {
    unsigned char record[4];
    record[0] = 0x52u;
    record[1] = call->device;
    record[2] = call->kind;
    record[3] = call->flags;
    return readyfs_reu_session_store(profile_offset(call->device), record, 4u);
}

static unsigned char profile_fetch(ReadyFsDriveUiCall *call) {
    unsigned char record[4];
    if (!readyfs_reu_session_fetch(profile_offset(call->device), record, 4u) ||
        record[0] != 0x52u || record[1] != call->device) return 0u;
    call->kind = record[2];
    call->flags = record[3];
    return 1u;
}

static void render_profile(ReadyFsDriveUiCall *call) {
    cputs("profile: ");
    print_profile(call->kind);
    cputs(" p"); cputc('0' + (call->flags & 1u));
    cputs(" f"); cputc('0' + ((call->flags >> 1u) & 1u));
    cputs(" i"); cputc('0' + ((call->flags >> 2u) & 1u));
    cputs("\r\n");
}

static unsigned char prepare_partition(ReadyFsDriveUiCall *call,
                                       ReadyFsPath *path) {
    call->device = path->unit;
    if (call->native_operation != RF_CMDPATH_NATIVE_DIR) {
        if (!profile_fetch(call)) {
            cputs(RF_ERROR "unprobed\r\n");
            return 0u;
        }
        if (!readyfs_driver_allows_operation(call->flags,
                                             call->native_operation)) {
            cputs(RF_ERROR "denied\r\n");
            return 0u;
        }
    }
    call->path.operation = call->native_operation;
    call->path.source = call->source;
    call->path.destination = call->destination;
    call->path.output = call->output;
    call->path.output_capacity = call->output_capacity;
    call->path.followup = call->followup;
    call->path.followup_capacity = call->followup_capacity;
    call->nested.operation = RF_NESTED_CMDPATH | RF_NESTED_RETURN_DRIVE;
    call->nested.call = &call->path;
    if (!readyfs_overlay_nested_from_backend(
            (ReadyFsNestedCall *)&call->nested)) {
        cputs(RF_ERROR "path err\r\n");
        return 0u;
    }
    return 1u;
}

static unsigned char nested_backend(ReadyFsDriveUiCall *call,
                                    unsigned char operation,
                                    unsigned char action) {
    ReadyFsBackendCall *backend;

    backend = call->backend;
    if (backend == 0 || call->state == 0) return 0u;
    memset(backend, 0, sizeof(*backend));
    backend->operation = operation;
    backend->action = action;
    backend->force = call->io_ok;
    /* Completion journals the source_root stem for every action.  MKDIR also
     * uses destination_root for endpoint validation, but must retain the same
     * canonical path here so a rejected device command can be ACKed cleanly. */
    backend->source_root = call->source;
    backend->destination_root = action == RF_EXEC_ACTION_MKDIR ? call->source :
                                (action == RF_EXEC_ACTION_MOVE_FILE ?
                                 call->destination : 0);
    backend->state = call->state;
    call->nested.operation = RF_NESTED_BACKEND | RF_NESTED_RETURN_DRIVE;
    call->nested.call = backend;
    return readyfs_overlay_nested_from_backend(
           (ReadyFsNestedCall *)&call->nested);
}

static unsigned char command_action(unsigned char operation) {
    if (operation == RF_CMDPATH_MKDIR) return RF_EXEC_ACTION_MKDIR;
    if (operation == RF_CMDPATH_SCRATCH) return RF_EXEC_ACTION_DELETE_FILE;
    if (operation == RF_CMDPATH_RENAME) return RF_EXEC_ACTION_MOVE_FILE;
    return RF_EXEC_ACTION_RMDIR;
}

unsigned char readyfs_driveui_dispatch(ReadyFsDriveUiCall *call) {
    ReadyFsPath path;
    ReadyFsDriverCall classify;

    if (call == 0) return 0u;
    if (call->operation == RF_DRIVEUI_COMMAND_BEGIN) {
        unsigned char action;
        call->handled = 0u;
        call->pending = 0u;
        if (call->source == 0 ||
            readyfs_path_parse(call->source, &path) != RF_PATH_OK ||
            path.endpoint != RF_EP_IEC ||
            (path.partition == 0u &&
             call->native_operation != RF_CMDPATH_NATIVE_DIR)) return 1u;
        /* File mutations on SD2IEC use the pinned stream service. Unknown
         * identities fall through to its automatic native preparation. */
        if ((unsigned char)(call->native_operation - RF_CMDPATH_DIRECTORY) <=
            RF_CMDPATH_RENAME - RF_CMDPATH_DIRECTORY) {
            call->device = path.unit;
            if (!profile_fetch(call) || call->kind == RF_DRIVER_SD2IEC) return 1u;
        }
        call->handled = 1u;
        if (call->native_operation < RF_CMDPATH_DIRECTORY ||
            call->native_operation > RF_CMDPATH_NATIVE_DIR) return 1u;
        if (call->native_operation != RF_CMDPATH_DIRECTORY &&
            call->native_operation != RF_CMDPATH_NATIVE_DIR &&
            call->native_operation != RF_CMDPATH_MKDIR &&
            !call->force) {
            cputs("use --force\r\n");
            return 1u;
        }
        if (!prepare_partition(call, &path)) return 1u;
        if (call->native_operation == RF_CMDPATH_DIRECTORY ||
            call->native_operation == RF_CMDPATH_NATIVE_DIR) {
            call->pending = 1u;
            return 1u;
        }
        if (call->native_operation >= RF_CMDPATH_MOUNT) {
            call->io_ok = 0u;
            call->pending = 1u;
            return 1u;
        }
        action = command_action(call->native_operation);
        call->io_ok = 0u;
        if (!nested_backend(call, RF_BACKEND_CALL_BEGIN, action)) {
            cputs(RF_ERROR "begin fail\r\n");
            return 1u;
        }
        call->pending = 1u;
        return 1u;
    }
    if (call->operation == RF_DRIVEUI_COMMAND_COMPLETE) {
        unsigned char action;
        if (!call->handled || !call->pending) return 1u;
        if (call->native_operation >= RF_CMDPATH_MOUNT) {
            call->pending = 0u;
            cputs(call->io_ok ? RF_SUMMARY "ok\r\n" : RF_ERROR "fail\r\n");
            return 1u;
        }
        action = command_action(call->native_operation);
        if (!nested_backend(call, RF_BACKEND_CALL_COMPLETE, action)) {
            cputs(RF_ERROR "end err\r\n");
            return 1u;
        }
        call->pending = 0u;
        if (action == RF_EXEC_ACTION_DELETE_FILE) {
            cputs(call->io_ok ? RF_SUMMARY "deleted\r\n" : RF_ERROR "del fail\r\n");
        } else if (action == RF_EXEC_ACTION_MOVE_FILE) {
            cputs(call->io_ok ? RF_SUMMARY "ren ok\r\n" : RF_ERROR "ren fail\r\n");
        } else if (call->io_ok) {
            cputs(action == RF_EXEC_ACTION_MKDIR ?
                  RF_SUMMARY "created\r\n" : RF_SUMMARY "removed\r\n");
        } else cputs(action == RF_EXEC_ACTION_MKDIR ?
                     RF_ERROR "md fail\r\n" : RF_ERROR "rd fail\r\n");
        return 1u;
    }
    if (call->operation == RF_DRIVEUI_QUERY) {
        if (!parse_drive(call, &path)) {
            cputs("profile iec N:\r\n");
            return 1u;
        }
        if (!profile_fetch(call)) {
            cputs(RF_ERROR "unprobed\r\n");
            return 1u;
        }
        render_profile(call);
        if (call->argc >= 4u) {
            unsigned char operation = operation_code(call->args[3]);
            if (operation == 0u) cputs("op: ?\r\n");
            else cputs(readyfs_driver_allows_operation(call->flags, operation) ?
                       "op: yes\r\n" : "op: no\r\n");
        }
        return 1u;
    }
    if (call->operation == RF_DRIVEUI_BEGIN) {
        call->pending = 0u;
        if (!parse_drive(call, &path)) {
            cputs("probe iec N:\r\n");
            return 1u;
        }
        call->pending = 1u;
        return 1u;
    }
    if (call->operation != RF_DRIVEUI_COMPLETE || call->status == 0) return 0u;
    call->pending = 0u;
    if (!call->io_ok) {
        cputs(RF_ERROR "absent\r\n");
        return 1u;
    }
    classify.status = call->status;
    if (!readyfs_driver_classify(&classify)) return 0u;
    call->kind = classify.kind;
    call->flags = classify.flags;
    if (!profile_store(call)) {
        cputs(RF_ERROR "save err\r\n");
        return 1u;
    }
    cputs("status: "); cputs(call->status); cputs("\r\n");
    render_profile(call);
    return 1u;
}
