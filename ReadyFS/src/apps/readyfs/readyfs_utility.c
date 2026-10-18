#include "readyfs_console.h"
#include "readyfs_utility.h"

#include "readyfs_backend.h"
#include "readyfs_path.h"
#include "readyfs_reu.h"

#include <conio.h>
#include <string.h>

#ifdef __CC65__
extern unsigned char __fastcall__ readyfs_same_word(const char *left, const char *right);
#define same_word readyfs_same_word
#else
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

#endif

static void print_u16(unsigned int value) {
    char reverse[5];
    unsigned char used;
    used = 0u;
    do {
        reverse[used++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value != 0u);
    while (used != 0u) cputc(reverse[--used]);
}

static unsigned char format_u16(ReadyFsUtilityCall *call) {
    char reverse[5];
    unsigned char used;
    char *output;
    unsigned int value;

    if (call->buffer == 0 || call->capacity < 6u) return 0u;
    output = call->buffer;
    value = call->value_low;
    used = 0u;
    do {
        reverse[used++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value != 0u);
    call->capacity = used;
    while (used != 0u) *output++ = reverse[--used];
    *output = 0;
    return 1u;
}

static unsigned char soft_cd(ReadyFsUtilityCall *call) {
#ifndef READYFS_UTILITY_SIDECAR
    char *translate;
#else
    extern void __fastcall__ readyfs_softname_normalize(char *text);
#endif
    const char *part;
    const char *slash;
    const char *last;
    unsigned int count;

    if (call->buffer == 0 || call->workspace == 0) return 0u;
    if (call->value_low == 0u) {
        /* Typed '_' is PETSCII $A4, while SoftwareIEC exposes a host '_' as
         * $5F.  Normalize only at this backend boundary; UltimateDOS and the
         * visible command line retain their original PETSCII spelling. */
#ifdef READYFS_UTILITY_SIDECAR
        readyfs_softname_normalize(call->buffer);
#else
        while ((translate = strchr(call->buffer, (char)0xA4u)) != 0)
            *translate = 0x5Fu;
#endif
        /* Resident first resets SoftwareIEC to its global virtual root with
         * cd:/.  Enter USB1 relatively: the unit's configured partition-0
         * default may still be the nonexistent legacy /USB0 path.  Keep the
         * C source lowercase so cc65 emits ordinary uppercase PETSCII bytes. */
        strcpy(call->workspace, "cd:usb1");
        call->value_low = 4u;
        call->capacity = 1u;
        return 1u;
    }
    last = strrchr(call->buffer, '/');
    part = call->buffer + call->value_low;
    if (last == 0 || part >= last) {
        call->capacity = 0u;
        return 1u;
    }
    slash = strchr(part, '/');
    if (slash == 0 || slash > last) slash = last;
    count = (unsigned int)(slash - part);
    strcpy(call->workspace, "cd:");
    memcpy(call->workspace + 3u, part, count);
    call->workspace[count + 3u] = 0;
    call->value_low = (unsigned int)(slash - call->buffer + 1u);
    call->capacity = 1u;
    return 1u;
}

static void print_u32(unsigned int high, unsigned int low) {
    unsigned char digits[10];
    unsigned char bit;
    unsigned char i;
    unsigned char carry;
    unsigned char next;
    unsigned char started;

    memset(digits, 0, sizeof(digits));
    for (bit = 0u; bit < 32u; ++bit) {
        carry = (unsigned char)((high & 0x8000u) != 0u);
        high = (unsigned int)((high << 1u) | (low >> 15u));
        low <<= 1u;
        for (i = 10u; i != 0u; --i) {
            next = (unsigned char)(digits[i - 1u] * 2u + carry);
            digits[i - 1u] = (unsigned char)(next % 10u);
            carry = (unsigned char)(next / 10u);
        }
    }
    started = 0u;
    for (i = 0u; i < 10u; ++i) {
        if (digits[i] != 0u || i == 9u) started = 1u;
        if (started) cputc((char)('0' + digits[i]));
    }
}

static unsigned char is_dry(const ReadyFsUtilityCall *call) {
    unsigned char i;
    for (i = 1u; i < call->argc; ++i) {
        if (same_word(call->args[i], "--dry-run") ||
            same_word(call->args[i], "--whatif")) return 1u;
    }
    return 0u;
}

static unsigned char preview(ReadyFsUtilityCall *call) {
    unsigned char i;
    unsigned char writes;
    unsigned char deletes;
    unsigned char mounts;

    if (!is_dry(call)) {
        cputs("use --dry-run\r\n");
        return 1u;
    }
    cputs("would ");
    for (i = 0u; i < call->argc; ++i) {
        if (!same_word(call->args[i], "--dry-run") &&
            !same_word(call->args[i], "--whatif")) {
            if (i != 0u) cputc(' ');
            cputs(call->args[i]);
        }
    }
    cputc('\r'); cputc('\n');
    writes = deletes = mounts = 0u;
    /* The resident passes the decoded ID so every alias has the same plan. */
    if (call->value_low == RF_COMMAND_COPY ||
        call->value_low == RF_COMMAND_NEW ||
        call->value_low == RF_COMMAND_WRITE ||
        call->value_low == RF_COMMAND_APPEND ||
        call->value_low == RF_COMMAND_MKDIR ||
        call->value_low == RF_COMMAND_RENAME ||
        (call->value_low == RF_COMMAND_CONFIG && call->argc > 1u &&
         same_word(call->args[1], "save"))) writes = 1u;
    if (call->value_low == RF_COMMAND_MOVE) writes = deletes = 1u;
    if (call->value_low == RF_COMMAND_DELETE ||
        call->value_low == RF_COMMAND_RMDIR) deletes = 1u;
    if (call->value_low >= RF_COMMAND_MOUNT &&
        call->value_low <= RF_COMMAND_SWAP) mounts = 1u;
    cputs(RF_SUMMARY "plan w"); print_u16(writes);
    cputs(" d"); print_u16(deletes);
    cputs(" m"); print_u16(mounts);
    cputs("; done w0 d0 m0\r\n");
    return 1u;
}

static unsigned char history(ReadyFsUtilityCall *call) {
    unsigned char count;
    unsigned char age;
    unsigned char number;

    if (call->buffer == 0 || call->capacity < RF_REU_HISTORY_BYTES) return 0u;
    count = readyfs_reu_history_count();
    if (count == 0u) {
        cputs("history empty\r\n");
        return 1u;
    }
    number = 1u;
    age = count;
    while (age != 0u) {
        --age;
        if (!readyfs_reu_history_get(age, call->buffer)) return 0u;
        print_u16(number++); cputs(": "); cputs(call->buffer);
        cputc('\r'); cputc('\n');
    }
    return 1u;
}

static unsigned char drives(ReadyFsUtilityCall *call) {
    unsigned int i;
    cputs("iec scan 8-30\r\n");
    for (i = 0u; i < call->capacity; ++i) {
        cputs("  "); print_u16((unsigned char)call->buffer[i]);
        cputs(": present\r\n");
    }
    if (call->value_high) {
        cputs("  u: ultimate dos\r\n  s: softiec bus ");
        print_u16(call->value_low); cputs("\r\n");
    }
    cputs("  t: sequential tape\r\n");
    return 1u;
}

static void print_cap(unsigned int flags, unsigned int bit,
                      const char *name) {
    if ((flags & bit) != 0u) { cputc(' '); cputs(name); }
}

static unsigned char capabilities(ReadyFsUtilityCall *call) {
    ReadyFsPath path;
    ReadyFsBackendCapabilities caps;

    if (call->buffer == 0 ||
        readyfs_path_parse(call->buffer, &path) != RF_PATH_OK ||
        !path.absolute || path.endpoint == RF_EP_ALIAS) {
        cputs("capabilities PATH\r\n");
        return 1u;
    }
    memset(&caps, 0, sizeof(caps));
    caps.endpoint = path.endpoint;
    caps.unit = path.unit;
    caps.partition = path.partition;
    caps.path_limit = RF_PATH_MAX;
    if (path.endpoint == RF_EP_IEC) {
        caps.leaf_limit = 16u;
        caps.size_units = RF_SIZE_BLOCKS;
        if (path.partition == 0u) {
            caps.flags = RF_CAP_READ | RF_CAP_WRITE | RF_CAP_DELETE |
                         RF_CAP_RENAME | RF_CAP_FREE;
        } else caps.provisional = 1u;
    } else if (path.endpoint == RF_EP_ULTIMATE) {
        caps.leaf_limit = RF_PATH_MAX;
        caps.size_units = RF_SIZE_BYTES;
        caps.flags = RF_CAP_READ | RF_CAP_WRITE | RF_CAP_DELETE |
                     RF_CAP_RENAME | RF_CAP_MKDIR | RF_CAP_RECURSE |
                     RF_CAP_IMAGES | RF_CAP_MOUNT;
    } else if (path.endpoint == RF_EP_SOFTIEC) {
        caps.leaf_limit = RF_PATH_MAX;
        caps.size_units = RF_SIZE_BYTES;
        caps.flags = RF_CAP_READ | RF_CAP_WRITE | RF_CAP_DELETE |
                     RF_CAP_RENAME | RF_CAP_MKDIR | RF_CAP_MOUNT;
        caps.provisional = 1u;
    } else if (path.endpoint == RF_EP_TAPE) {
        caps.leaf_limit = 16u;
        caps.flags = RF_CAP_READ | RF_CAP_WRITE | RF_CAP_SEQUENTIAL;
    } else {
        cputs("capabilities PATH\r\n");
        return 1u;
    }
    cputs("ep ");
    if (caps.endpoint == RF_EP_IEC) {
        cputs("iec "); print_u16(caps.unit);
        cputs(" p"); print_u16(caps.partition);
    } else if (caps.endpoint == RF_EP_ULTIMATE) cputs("ultimate dos");
    else if (caps.endpoint == RF_EP_SOFTIEC) {
        cputs("softiec "); print_u16(caps.unit);
    } else cputs("tape seq");
    cputs("\r\nmax path "); print_u16(caps.path_limit);
    cputs(" leaf "); print_u16(caps.leaf_limit);
    cputs("\r\nsize: ");
    if (caps.size_units == RF_SIZE_BLOCKS) cputs("c64 blocks");
    else if (caps.size_units == RF_SIZE_BYTES) cputs("bytes");
    else cputs("stream");
    cputs("\r\ncaps:");
    print_cap(caps.flags, RF_CAP_READ, "read");
    print_cap(caps.flags, RF_CAP_WRITE, "write");
    print_cap(caps.flags, RF_CAP_DELETE, "delete");
    print_cap(caps.flags, RF_CAP_RENAME, "rename");
    if ((caps.flags & (RF_CAP_MKDIR | RF_CAP_RECURSE | RF_CAP_IMAGES |
                       RF_CAP_MOUNT)) != 0u) cputs("\r\n");
    print_cap(caps.flags, RF_CAP_MKDIR, "mkdir");
    print_cap(caps.flags, RF_CAP_RECURSE, "recurse");
    print_cap(caps.flags, RF_CAP_IMAGES, "images");
    print_cap(caps.flags, RF_CAP_MOUNT, "mount");
    print_cap(caps.flags, RF_CAP_FREE, "free");
    print_cap(caps.flags, RF_CAP_SEQUENTIAL, "seq");
    cputs("\r\nprov ");
    cputs(caps.provisional ? "yes\r\n" : "no\r\n");
    return 1u;
}

unsigned int readyfs_utility_abi(void) { return RF_UTILITY_ABI; }

unsigned char readyfs_utility_dispatch(ReadyFsUtilityCall *call) {
    if (call == 0) return 0u;
    if (call->operation == RF_UTILITY_CAPABILITIES) return capabilities(call);
    if (call->operation == RF_UTILITY_PRINT_U32) {
        print_u32(call->value_high, call->value_low);
        return 1u;
    }
    if (call->operation == RF_UTILITY_PRINT_U16) {
        print_u16(call->value_low);
        return 1u;
    }
    if (call->operation == RF_UTILITY_FORMAT_U16) return format_u16(call);
    if (call->operation == RF_UTILITY_DRIVES) return drives(call);
    if (call->operation == RF_UTILITY_SOFT_CD) return soft_cd(call);
    if (call->args == 0) return 0u;
    if (call->operation == RF_UTILITY_PREVIEW) return preview(call);
    if (call->operation == RF_UTILITY_HISTORY) return history(call);
    return 0u;
}
