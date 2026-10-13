#include "readyfs_iec.h"
#include "readyfs_path.h"
#include <string.h>
#include <conio.h>
#include "readyfs_console.h"
#include "readyfs_result.h"

#ifdef __CC65__
extern unsigned char __fastcall__ readyfs_same_word(const char *, const char *);
#else
extern unsigned char readyfs_same_word(const char *, const char *);
#endif
#define same readyfs_same_word

static unsigned char number(const char *s, unsigned char *out) {
    unsigned int n;
    if (!*s) return 0u;
    n = 0u;
    while (*s) {
        if (*s < '0' || *s > '9') return 0u;
        n = n * 10u + (unsigned char)(*s++ - '0');
        if (n > 255u) return 0u;
    }
    *out = (unsigned char)n;
    return 1u;
}

static void decimal(unsigned char *out, unsigned char n) {
    if (n >= 100u) { *out++ = '0' + n / 100u; n %= 100u; }
    else if (n < 10u) { *out++ = '0' + n; *out = 0u; return; }
    *out++ = '0' + n / 10u;
    *out++ = '0' + n % 10u;
    *out = 0u;
}

static unsigned char hex(unsigned char ch) {
    if (ch >= '0' && ch <= '9') return ch - '0';
    ch &= 0x7Fu;
    /* Numeric bounds also accept host ASCII tests and shifted PETSCII. */
    if (ch >= 97u && ch <= 102u) ch -= 32u;
    return ch >= 65u && ch <= 70u ? ch - 55u : 255u;
}

static unsigned char plan(ReadyFsIecCall *c) {
    ReadyFsPath path;
    const char *verb;
    const char *arg;
    unsigned char n;
    unsigned char hi;
    unsigned char lo;
    unsigned int len;
    if (c->argc < 3u || readyfs_path_parse(c->args[1], &path) != RF_PATH_OK ||
        path.endpoint != RF_EP_IEC || path.partition ||
        c->args[1][path.path_offset]) return 0u;
    c->device = path.unit;
    c->flags = RF_IEC_SD_ONLY; c->operation = RF_IEC_TEXT; c->expected = 3u;
    c->new_device = 0u; c->length = 0u; c->command[0] = 0u;
    verb = c->args[2];
    arg = c->argc > 3u ? c->args[3] : "";
    if (same(verb, "dos")) {
        if (c->argc == 5u && same(arg, "--hex")) {
            arg = c->args[4];
            while (*arg) {
                while (*arg == ' ') ++arg;
                if (!*arg) break;
                hi = hex(*arg++);
                if (!*arg) return 0u;
                lo = hex(*arg++);
                if (hi > 15u || lo > 15u ||
                    (*arg && *arg != ' ') || c->length >= RF_IEC_COMMAND_CAP - 1u)
                    return 0u;
                c->command[c->length++] = (hi << 4u) | lo;
            }
        } else if (c->argc == 4u) {
            len = strlen(arg);
            if (!len || len >= RF_IEC_COMMAND_CAP || strchr(arg, '\r') ||
                strchr(arg, '\n')) return 0u;
            memcpy(c->command, arg, len); c->length = (unsigned char)len;
        } else return 0u;
        c->flags = RF_IEC_INVALIDATE | RF_IEC_RAW;
        c->expected = 255u; /* raw DOS: preserve and interpret returned status */
        return c->length != 0u;
    }
    if (same(verb, "address")) {
        if ((c->argc != 4u && c->argc != 5u) || !number(arg, &n) ||
            n < 8u || n > 30u || n == c->device) return 0u;
        c->flags = RF_IEC_SD_ONLY | RF_IEC_INVALIDATE;
        if (c->argc == 5u) {
            if (!same(c->args[4], "--save")) return 0u;
            c->flags |= RF_IEC_SAVE;
        }
        strcpy((char *)c->command, "u0>"); c->command[3] = n;
        c->command[4] = 13u; c->length = 5u; c->new_device = n; c->operation = RF_IEC_ADDRESS;
        return 1u;
    }
    if (same(verb, "partitions") && c->argc == 3u) {
        c->operation = RF_IEC_PARTITIONS; return 1u;
    }
    if (same(verb, "partition")) {
        n = 0u;
        if (c->argc > 3u && !number(arg, &n)) return 0u;
        c->flags = RF_IEC_SD_ONLY;
        if (c->argc == 5u && same(c->args[4], "--select") && n) {
            strcpy((char *)c->command, "cp"); decimal(c->command + 2u, n);
            c->flags |= RF_IEC_INVALIDATE; c->expected = 2u;
        } else if (c->argc == 3u || c->argc == 4u) {
            strcpy((char *)c->command, "g-p");
            c->length = 3u;
            if (c->argc == 4u) {
                c->command[3] = n; c->command[4] = 13u; c->length = 5u;
            }
            c->operation = RF_IEC_PARTITION; return 1u;
        } else return 0u;
    } else if (same(verb, "extensions")) {
        if (c->argc != 4u || !number(arg, &n) || n > 4u) return 0u;
        strcpy((char *)c->command, "xe0"); c->command[2] += n;

    } else if (same(verb, "hide-extensions")) {
        if (c->argc != 4u || (!same(arg, "on") && !same(arg, "off"))) return 0u;
        strcpy((char *)c->command, "xe-");
        if (same(arg, "on")) c->command[2] = '+';

    } else if (same(verb, "images")) {
        if (c->argc != 4u) return 0u;
        if (same(arg, "files")) n = 0u;
        else if (same(arg, "dirs")) n = 1u;
        else if (same(arg, "both")) n = 2u;
        else return 0u;
        strcpy((char *)c->command, "xi0"); c->command[2] += n; c->expected = 0u;

    } else if (same(verb, "wildcard")) {
        if (c->argc != 4u || (!same(arg, "1541") && !same(arg, "1581"))) return 0u;
        strcpy((char *)c->command, "x*-");
        if (same(arg, "1581")) c->command[2] = '+';

    } else if (same(verb, "reset")) {
        if (c->argc != 4u || (!same(arg, "soft") && !same(arg, "hard"))) return 0u;
        strcpy((char *)c->command, "uj");
        c->flags = RF_IEC_INVALIDATE;
        c->expected = 73u;
        if (same(arg, "hard")) {
            c->flags |= RF_IEC_SD_ONLY;
            c->command[1] = 0xCAu; c->operation = RF_IEC_RESTART;
        }
    } else {
        if (c->argc != 3u) return 0u;
        if (same(verb, "status")) { c->flags = 0u; c->expected = 255u; return 1u; }
        if (same(verb, "version")) {
            strcpy((char *)c->command, "ui"); c->expected = 73u; c->flags = 0u;
        } else if (same(verb, "initialize")) {
            strcpy((char *)c->command, "i"); c->flags = RF_IEC_INVALIDATE; c->expected = 0u;
        } else if (same(verb, "config")) {
            strcpy((char *)c->command, "x"); c->flags = RF_IEC_SD_ONLY;
            c->expected = 3u;
        } else if (same(verb, "save-config")) {
            strcpy((char *)c->command, "xw"); c->flags = RF_IEC_SD_ONLY;
            c->expected = 3u;
        } else return 0u;
    }
    c->length = (unsigned char)strlen((char *)c->command);
    return 1u;
}

unsigned int readyfs_iec_plan_abi(void) { return RF_IEC_PLAN_ABI; }
unsigned char readyfs_iec_plan(ReadyFsIecCall *c) {
    if (plan(c)) return 1u;
    *c->status = RF_RESULT_USAGE;
    cputs(RF_ERROR "usage: iec 10: subcommand [value]\r\nhelp iec for examples\r\n");
    return 0u;
}
