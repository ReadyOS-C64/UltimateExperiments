#include "readyfs_driver.h"
#include "readyfs_cmdpath.h"

static unsigned char folded(unsigned char value) {
    if (value >= 'A' && value <= 'Z') return (unsigned char)(value + 32u);
    return value;
}

static unsigned char contains(const char *text, const char *wanted) {
    const char *start;
    const char *left;
    const char *right;

    if (text == 0 || wanted == 0 || *wanted == 0) return 0u;
    for (start = text; *start != 0; ++start) {
        left = start;
        right = wanted;
        while (*left != 0 && *right != 0 &&
               folded((unsigned char)*left) ==
               folded((unsigned char)*right)) {
            ++left;
            ++right;
        }
        if (*right == 0) return 1u;
    }
    return 0u;
}

unsigned int readyfs_driver_abi(void) { return RF_DRIVER_ABI; }

unsigned char readyfs_driver_classify(ReadyFsDriverCall *call) {
    if (call == 0 || call->status == 0) return 0u;
    call->kind = RF_DRIVER_UNKNOWN;
    call->flags = 0u;
    if (contains(call->status, "sd2iec")) {
        call->kind = RF_DRIVER_SD2IEC;
        call->flags = RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS |
                      RF_DRIVER_IMAGES;
    } else if (contains(call->status, "softiec")) {
        call->kind = RF_DRIVER_SOFTIEC;
        call->flags = RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS |
                      RF_DRIVER_IMAGES;
    } else if (contains(call->status, "cmd")) {
        call->kind = RF_DRIVER_CMD;
        call->flags = RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS;
    } else if (contains(call->status, "pi1541")) {
        call->kind = RF_DRIVER_PI1541;
    } else if (contains(call->status, "ultimate") ||
               contains(call->status, "u64")) {
        call->kind = RF_DRIVER_ULTIMATE;
    } else if (contains(call->status, "1541") ||
               contains(call->status, "1571") ||
               contains(call->status, "1581") ||
               contains(call->status, "vice") ||
               contains(call->status, "virtual drive emulation")) {
        call->kind = RF_DRIVER_LEGACY;
    }
    return 1u;
}

unsigned char readyfs_driver_allows_operation(unsigned char flags,
                                              unsigned char operation) {
    unsigned char required;
    if (operation == RF_CMDPATH_OPEN_FILE ||
        operation == RF_CMDPATH_SCRATCH) {
        required = RF_DRIVER_PARTITIONS;
    } else if (operation == RF_CMDPATH_DIRECTORY ||
               operation == RF_CMDPATH_MKDIR ||
               operation == RF_CMDPATH_RMDIR ||
               operation == RF_CMDPATH_RENAME) {
        required = RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS;
    } else if (operation == RF_CMDPATH_MOUNT ||
               operation == RF_CMDPATH_UNMOUNT) {
        required = RF_DRIVER_PARTITIONS | RF_DRIVER_FOLDERS |
                   RF_DRIVER_IMAGES;
    } else return 0u;
    return (unsigned char)((flags & required) == required);
}

#ifndef __CC65__
const char *readyfs_driver_name(unsigned char kind) {
    switch (kind) {
        case RF_DRIVER_LEGACY: return "legacy";
        case RF_DRIVER_SD2IEC: return "sd2iec";
        case RF_DRIVER_CMD: return "cmd";
        case RF_DRIVER_PI1541: return "pi1541";
        case RF_DRIVER_ULTIMATE: return "ultimate";
        case RF_DRIVER_SOFTIEC: return "softiec";
        default: return "unknown";
    }
}
#endif
