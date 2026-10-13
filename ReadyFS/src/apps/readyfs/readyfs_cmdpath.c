#include "readyfs_cmdpath.h"

#include "readyfs_path.h"

#include <string.h>

#ifdef __CC65__
#define RF_NATIVE_SCRATCH "s"
#define RF_NATIVE_MKDIR   "md"
#define RF_NATIVE_RMDIR   "rd"
#define RF_NATIVE_RENAME  "r"
#define RF_NATIVE_CD      "cd"
#else
#define RF_NATIVE_SCRATCH "S"
#define RF_NATIVE_MKDIR   "MD"
#define RF_NATIVE_RMDIR   "RD"
#define RF_NATIVE_RENAME  "R"
#define RF_NATIVE_CD      "CD"
#endif

unsigned int readyfs_cmdpath_abi(void) { return RF_CMDPATH_ABI; }

#ifdef __CC65__
static ReadyFsCmdPathCall selftest_call;
static char selftest_output[20];
#endif

static unsigned char append_char(char **cursor, unsigned int *left,
                                 char value) {
    if (*left <= 1u) return 0u;
    **cursor = value;
    ++*cursor;
    --*left;
    **cursor = 0;
    return 1u;
}

static unsigned char append_bytes(char **cursor, unsigned int *left,
                                  const char *text, unsigned int length) {
    if (length >= *left) return 0u;
    memmove(*cursor, text, length);
    *cursor += length;
    *left = (unsigned int)(*left - length);
    **cursor = 0;
    return 1u;
}

static unsigned char append_partition(char **cursor, unsigned int *left,
                                      unsigned char partition) {
    if (partition >= 100u) {
        if (!append_char(cursor, left,
                         (char)('0' + partition / 100u))) return 0u;
        partition = (unsigned char)(partition % 100u);
        if (!append_char(cursor, left,
                         (char)('0' + partition / 10u))) return 0u;
    } else if (partition >= 10u) {
        if (!append_char(cursor, left,
                         (char)('0' + partition / 10u))) return 0u;
    }
    return append_char(cursor, left, (char)('0' + partition % 10u));
}

static unsigned char same_ascii(const char *left, const char *right) {
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

static unsigned char image_extension_ok(const char *leaf) {
    const char *dot;
    dot = strrchr(leaf, '.');
    if (dot == 0) return 0u;
    return same_ascii(dot, ".d64") || same_ascii(dot, ".d71") ||
           same_ascii(dot, ".d81") || same_ascii(dot, ".dnp");
}

static unsigned char component_ok(const char *start, unsigned int length) {
    if (length == 0u || length > RF_CMDPATH_COMPONENT_MAX) return 0u;
    if (length == 1u && start[0] == '.') return 0u;
    if (length == 2u && start[0] == '.' && start[1] == '.') return 0u;
    return 1u;
}

static unsigned char prepare(const char *text, ReadyFsPath *path,
                             const char **body) {
    if (text == 0 || readyfs_path_parse(text, path) != RF_PATH_OK ||
        path->endpoint != RF_EP_IEC || !path->absolute ||
        path->partition == 0u || path->partition > 254u) {
        return RF_CMDPATH_BAD_PATH;
    }
    *body = text + path->path_offset;
    if (**body == '/') ++*body;
    return RF_CMDPATH_OK;
}

static unsigned char append_components(const char *body,
                                       unsigned char directory,
                                       char **cursor, unsigned int *left,
                                       unsigned int *native_length,
                                       const char **leaf_out) {
    const char *component;
    const char *slash;
    unsigned int length;

    component = body;
    *leaf_out = 0;
    if (*component == 0) return directory ? RF_CMDPATH_OK :
                                           RF_CMDPATH_BAD_PATH;
    for (;;) {
        if (strchr(component, '!') != 0) return RF_CMDPATH_IMAGE_STATEFUL;
        slash = strchr(component, '/');
        length = slash == 0 ? strlen(component) :
                              (unsigned int)(slash - component);
        if (!component_ok(component, length)) {
            return length > RF_CMDPATH_COMPONENT_MAX ?
                   RF_CMDPATH_COMPONENT_TOO_LONG : RF_CMDPATH_BAD_PATH;
        }
        if (slash == 0 && !directory) {
            *leaf_out = component;
            return RF_CMDPATH_OK;
        }
        if (!append_bytes(cursor, left, component, length) ||
            !append_char(cursor, left, '/')) {
            return RF_CMDPATH_OUTPUT_TOO_SMALL;
        }
        *native_length = (unsigned int)(*native_length + length + 1u);
        if (*native_length > RF_CMDPATH_DIRECTORY_MAX) {
            return RF_CMDPATH_NATIVE_TOO_LONG;
        }
        if (slash == 0) return RF_CMDPATH_OK;
        component = slash + 1u;
        if (*component == 0) return RF_CMDPATH_OK;
    }
}

static unsigned char build_reference(const char *text,
                                     unsigned char directory,
                                     char *output, unsigned int capacity,
                                     ReadyFsPath *path) {
    const char *body;
    const char *leaf;
    char *cursor;
    unsigned int left;
    unsigned int native_length;
    unsigned char result;

    if (output == 0 || capacity == 0u) return RF_CMDPATH_OUTPUT_TOO_SMALL;
    result = prepare(text, path, &body);
    if (result != RF_CMDPATH_OK) return result;
    if (path->image_depth != 0u) return RF_CMDPATH_IMAGE_STATEFUL;
    output[0] = 0;
    cursor = output;
    left = capacity;
    if (!append_partition(&cursor, &left, path->partition) ||
        !append_bytes(&cursor, &left, "//", 2u)) {
        return RF_CMDPATH_OUTPUT_TOO_SMALL;
    }
    native_length = 2u;
    result = append_components(body, directory, &cursor, &left,
                               &native_length, &leaf);
    if (result != RF_CMDPATH_OK) return result;
    if (!directory) {
        if (!append_char(&cursor, &left, ':') ||
            !append_bytes(&cursor, &left, leaf, strlen(leaf))) {
            return RF_CMDPATH_OUTPUT_TOO_SMALL;
        }
    }
    return RF_CMDPATH_OK;
}

static unsigned char prefix(char *text, unsigned int capacity,
                            const char *value) {
    unsigned int prefix_length;
    unsigned int text_length;
    prefix_length = strlen(value);
    text_length = strlen(text);
    if (prefix_length + text_length + 1u > capacity) return 0u;
    memmove(text + prefix_length, text, text_length + 1u);
    memcpy(text, value, prefix_length);
    return 1u;
}

static unsigned char mount_command(ReadyFsCmdPathCall *call,
                                   ReadyFsPath *path) {
    const char *body;
    const char *leaf;
    char *cursor;
    unsigned int left;
    unsigned int native_length;
    unsigned char result;

    if (call->output == 0 || call->output_capacity == 0u) {
        return RF_CMDPATH_OUTPUT_TOO_SMALL;
    }
    call->output[0] = 0;
    result = prepare(call->source, path, &body);
    if (result != RF_CMDPATH_OK) return result;
    if (path->image_depth != 0u) return RF_CMDPATH_IMAGE_STATEFUL;
    cursor = call->output;
    left = call->output_capacity;
    if (!append_bytes(&cursor, &left, RF_NATIVE_CD, 2u) ||
        !append_partition(&cursor, &left, path->partition) ||
        !append_bytes(&cursor, &left, "//", 2u)) {
        return RF_CMDPATH_OUTPUT_TOO_SMALL;
    }
    native_length = 2u;
    result = append_components(body, 0u, &cursor, &left,
                               &native_length, &leaf);
    if (result != RF_CMDPATH_OK) return result;
    if (!image_extension_ok(leaf)) return RF_CMDPATH_IMAGE_REQUIRED;
    if (!append_bytes(&cursor, &left, leaf, strlen(leaf))) {
        return RF_CMDPATH_OUTPUT_TOO_SMALL;
    }
    return RF_CMDPATH_OK;
}

static unsigned char unmount_commands(ReadyFsCmdPathCall *call,
                                      ReadyFsPath *path) {
    const char *body;
    unsigned char result;
    result = prepare(call->source, path, &body);
    if (result != RF_CMDPATH_OK || *body != 0) return RF_CMDPATH_BAD_PATH;
    if (call->output == 0 || call->output_capacity < 5u ||
        call->followup == 0 || call->followup_capacity < 4u) {
        return RF_CMDPATH_OUTPUT_TOO_SMALL;
    }
    strcpy(call->output, RF_NATIVE_CD "//");
    call->followup[0] = RF_NATIVE_CD[0];
    call->followup[1] = RF_NATIVE_CD[1];
    call->followup[2] = (char)RF_CMDPATH_SD2IEC_BACK;
    call->followup[3] = 0;
    return RF_CMDPATH_OK;
}

static unsigned char native_directory_pattern(ReadyFsCmdPathCall *call,
                                              ReadyFsPath *path) {
    const char *body;
    unsigned int length;

    if (call->output == 0 || call->output_capacity == 0u) {
        return RF_CMDPATH_OUTPUT_TOO_SMALL;
    }
    call->output[0] = 0;
    if (readyfs_path_parse(call->source, path) != RF_PATH_OK ||
        path->endpoint != RF_EP_IEC || !path->absolute ||
        path->partition != 0u || path->image_depth != 0u) {
        return RF_CMDPATH_BAD_PATH;
    }
    body = call->source + path->path_offset;
    if (*body == '/') ++body;
    length = strlen(body);
    if (length == 0u || strchr(body, '/') != 0) return RF_CMDPATH_BAD_PATH;
    if (length > RF_CMDPATH_COMPONENT_MAX) {
        return RF_CMDPATH_COMPONENT_TOO_LONG;
    }
    if (strchr(body, '*') == 0 && strchr(body, '?') == 0) {
        return RF_CMDPATH_PATTERN_REQUIRED;
    }
    if (length + 3u > call->output_capacity) {
        return RF_CMDPATH_OUTPUT_TOO_SMALL;
    }
    call->output[0] = '$';
    call->output[1] = ':';
    strcpy(call->output + 2u, body);
    return RF_CMDPATH_OK;
}

unsigned char readyfs_cmdpath_dispatch(ReadyFsCmdPathCall *call) {
    ReadyFsPath source_path;
    ReadyFsPath destination_path;
    unsigned char result;

    if (call == 0 || call->source == 0) return 0u;
    if (call->operation == RF_CMDPATH_NATIVE_DIR) {
        result = native_directory_pattern(call, &source_path);
    } else if (call->operation == RF_CMDPATH_MOUNT) {
        result = mount_command(call, &source_path);
    } else if (call->operation == RF_CMDPATH_UNMOUNT) {
        result = unmount_commands(call, &source_path);
    } else if (call->operation == RF_CMDPATH_RENAME) {
        if (call->destination == 0 || call->output == 0 ||
            call->followup == 0) {
            result = RF_CMDPATH_BAD_PATH;
        } else {
            /* CMD/SD2IEC rename syntax is R:new=old.  Keep the source in the
             * follow-up scratch buffer while composing the destination in
             * the returned command buffer. */
            result = build_reference(call->source, 0u,
                     call->followup, call->followup_capacity, &source_path);
            if (result == RF_CMDPATH_OK) {
                result = build_reference(call->destination, 0u,
                         call->output, call->output_capacity,
                         &destination_path);
            }
            if (result == RF_CMDPATH_OK &&
                (source_path.unit != destination_path.unit ||
                 source_path.partition != destination_path.partition)) {
                result = RF_CMDPATH_CROSS_LOCATION;
            }
            if (result == RF_CMDPATH_OK &&
                (!prefix(call->output, call->output_capacity,
                         RF_NATIVE_RENAME) ||
                 strlen(call->output) + strlen(call->followup) + 2u >
                 call->output_capacity)) {
                result = RF_CMDPATH_OUTPUT_TOO_SMALL;
            }
            if (result == RF_CMDPATH_OK) {
                strcat(call->output, "=");
                strcat(call->output, call->followup);
            }
        }
    } else {
        result = build_reference(call->source,
                  call->operation == RF_CMDPATH_DIRECTORY,
                  call->output, call->output_capacity, &source_path);
        if (result == RF_CMDPATH_OK &&
            call->operation == RF_CMDPATH_DIRECTORY &&
            !prefix(call->output, call->output_capacity, "$")) {
            result = RF_CMDPATH_OUTPUT_TOO_SMALL;
        } else if (result == RF_CMDPATH_OK &&
                   call->operation == RF_CMDPATH_SCRATCH &&
                   !prefix(call->output, call->output_capacity,
                           RF_NATIVE_SCRATCH)) {
            result = RF_CMDPATH_OUTPUT_TOO_SMALL;
        } else if (result == RF_CMDPATH_OK &&
                   call->operation == RF_CMDPATH_MKDIR &&
                   !prefix(call->output, call->output_capacity,
                           RF_NATIVE_MKDIR)) {
            result = RF_CMDPATH_OUTPUT_TOO_SMALL;
        } else if (result == RF_CMDPATH_OK &&
                   call->operation == RF_CMDPATH_RMDIR &&
                   !prefix(call->output, call->output_capacity,
                           RF_NATIVE_RMDIR)) {
            result = RF_CMDPATH_OUTPUT_TOO_SMALL;
        } else if (result == RF_CMDPATH_OK &&
                   call->operation != RF_CMDPATH_OPEN_FILE &&
                   call->operation != RF_CMDPATH_DIRECTORY &&
                   call->operation != RF_CMDPATH_SCRATCH &&
                   call->operation != RF_CMDPATH_MKDIR &&
                   call->operation != RF_CMDPATH_RMDIR) {
            result = RF_CMDPATH_UNSUPPORTED;
        }
    }
    call->result = result;
    if (result == RF_CMDPATH_OK) {
        call->device = source_path.unit;
        call->partition = source_path.partition;
        call->image_depth = source_path.image_depth;
        return 1u;
    }
    return 0u;
}

unsigned char readyfs_cmdpath_selftest(void) {
#ifdef __CC65__
    selftest_call.operation = RF_CMDPATH_NATIVE_DIR;
    selftest_call.source = "8:/a*.prg";
    selftest_call.output = selftest_output;
    selftest_call.output_capacity = sizeof(selftest_output);
    return readyfs_cmdpath_dispatch(&selftest_call) &&
           selftest_call.device == 8u &&
           same_ascii(selftest_output, "$:a*.prg");
#else
    return 1u;
#endif
}

#ifndef __CC65__
const char *readyfs_cmdpath_error(unsigned char result) {
    switch (result) {
        case RF_CMDPATH_OK: return "ok";
        case RF_CMDPATH_BAD_PATH: return "not an absolute partitioned iec path";
        case RF_CMDPATH_UNSUPPORTED: return "operation unsupported by cmd profile";
        case RF_CMDPATH_COMPONENT_TOO_LONG: return "native component exceeds 16 bytes";
        case RF_CMDPATH_NATIVE_TOO_LONG: return "native directory path exceeds 234 bytes";
        case RF_CMDPATH_OUTPUT_TOO_SMALL: return "translated command buffer too small";
        case RF_CMDPATH_CROSS_LOCATION: return "rename crosses device or partition";
        case RF_CMDPATH_IMAGE_REQUIRED: return "supported disk image name required";
        case RF_CMDPATH_IMAGE_STATEFUL: return "image path needs stateful mount transaction";
        case RF_CMDPATH_PATTERN_REQUIRED: return "native directory pattern requires wildcard";
        default: return "unknown cmd path error";
    }
}
#endif
