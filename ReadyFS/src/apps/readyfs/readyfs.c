/*
 * readyfs.c - standalone ReadyFS Lab shell
 *
 * This is intentionally not a ReadyOS app. It is the executable probe/lab for
 * the endpoint-first filesystem model that will later feed a ReadyOS service.
 */

#include <cbm.h>
#include <cbm_filetype.h>
#include <conio.h>
#include <string.h>

#include "readyfs_path.h"
#include "readyfs_stream.h"
#include "readyfs_volume.h"
#include "readyfs_match.h"
#include "readyfs_io.h"
#include "readyfs_overlay.h"
#include "readyfs_plan.h"
#include "readyfs_reu.h"
#include "readyfs_uci.h"
#include "readyfs_result.h"
#include "readyfs_tape.h"
#include "readyfs_ui.h"
#include "readyfs_console.h"
#include "readyfs_udos_status.h"

#define RF_LINE_CAP    255u
#define RF_ARG_CAP     12u
#define RF_UCI_DATA_CAP 64u
#define RF_UCI_STAT_CAP 32u
#define RF_DIR_LIMIT   512u
#define RF_DIR_PAGE    18u
#define RF_IO_CHUNK    32u
#define RF_ALIAS_SLOTS 8u
#define RF_ALIAS_NAME  16u
#define RF_KERNAL_STATUS (*(volatile unsigned char *)0x0090u)
typedef struct {
    char name[RF_ALIAS_NAME + 1u];
    char root[RF_LINE_CAP + 1u];
} ReadyFsAlias;

#define RF_ALIAS_SLOT_BYTES ((unsigned int)sizeof(ReadyFsAlias))
#define RF_ALIAS_TABLE_BYTES (RF_ALIAS_SLOTS * RF_ALIAS_SLOT_BYTES)

/* Linker-visible so the UI harness can resolve this moving BSS oracle. */
char line_buf[RF_LINE_CAP + 1u];
char *args[RF_ARG_CAP];
static char cwd_buf[RF_LINE_CAP + 1u] = "8:/";
static unsigned char uci_data[RF_UCI_DATA_CAP];
static union {
    unsigned char io[RF_IO_CHUNK];
    unsigned char status[RF_UCI_STAT_CAP];
} transfer_scratch;
#define io_buf transfer_scratch.io
#define uci_stat transfer_scratch.status
unsigned char readyfs_pipeline_scratch[RF_PIPELINE_SCRATCH_BYTES];
#define uci_cmd readyfs_pipeline_scratch
#ifdef READYFS_OVERLAY_RUNTIME
#define drive_ui (*(ReadyFsDriveUiCall *)(void *)readyfs_pipeline_scratch)
#define native_ui (*(ReadyFsNativeUiCall *)(void *)readyfs_pipeline_scratch)
#define utility_ui (*(ReadyFsUtilityCall *)(void *)readyfs_pipeline_scratch)
#define tree_ui (*(ReadyFsTreeCall *)(void *)readyfs_pipeline_scratch)
#define batch_ui (*(ReadyFsBatchCall *)(void *)readyfs_pipeline_scratch)
#define tape_call (*(ReadyFsTapeCall *)(void *)readyfs_pipeline_scratch)
#define iec_call (*(ReadyFsIecCall *)(void *)readyfs_pipeline_scratch)
#define files_call (*(ReadyFsFilesCall *)(void *)readyfs_pipeline_scratch)
#define stream_call (*(ReadyFsStreamCall *)(void *)readyfs_pipeline_scratch)
#else
static ReadyFsUtilityCall utility_ui;
#endif
/* Mutation commands are never re-entrant. One shared pair prevents each
 * command implementation from reserving another 512 bytes of resident BSS. */
static char temp_text[RF_LINE_CAP + 1u];
static ReadyFsUciTransfer uci_xfer;
#ifdef READYFS_SOFT_DIAG
#define SOFT_DIAG(value) \
    (readyfs_pipeline_scratch[RF_PIPELINE_SCRATCH_BYTES - 1u] = (value))
#else
#define SOFT_DIAG(value)
#endif
#ifdef READYFS_OVERLAY_RUNTIME
/* Alias resolution/config iteration finishes before a staged backup stream is
 * created. Tree uses alias scratch while backup is idle. Recursive execution
 * has a dedicated outer call below, so these two 272-byte lifetimes may share
 * one resident workspace without aliasing the sidecar's call record. */
static unsigned char alias_backup_storage[sizeof(ReadyFsAlias) + 2u];
#define alias_slot (*(ReadyFsAlias *)(void *)alias_backup_storage)
#else
static ReadyFsAlias alias_slot;
#endif
/* Exported only so automation can resolve these moving BSS sentinels from the
 * linker map instead of silently probing stale absolute addresses. */
unsigned char reu_available;
unsigned char overlay_available;
static unsigned char last_result;
#ifdef READYFS_OVERLAY_RUNTIME
static unsigned char batch_active;
static unsigned char batch_prompt_denied;
#endif

static unsigned char resolve_path(const char *input, char *out);
static void newline(void);
static unsigned char dispatch(unsigned char argc);

static void __fastcall__ result_unavailable(const char *message) {
    last_result = RF_RESULT_UNAVAILABLE;
    cputc(0x1Cu); cputs(message);
}

static void __fastcall__ result_unsupported(const char *message) {
    last_result = RF_RESULT_UNSUPPORTED;
    cputc(0x1Cu); cputs(message);
}

static void cmd_mutation_preview(unsigned char argc);
#ifdef READYFS_OVERLAY_RUNTIME
static unsigned char path_prepare(const char *text, ReadyFsStream *stream);
static unsigned char native_file(ReadyFsStream *stream, ReadyFsStream *other, unsigned char operation);
#endif
static unsigned char compare_one(const char *left_text, const char *right_text);
static unsigned char compare_prepared(void);
static unsigned char has_dry_run(unsigned char argc);
#ifdef READYFS_OVERLAY_RUNTIME
static void tree_add(const char *name, unsigned char kind);
static unsigned char tree_failed;
#endif
static const char *option_value(unsigned char argc, const char *option);
static unsigned char option_present(unsigned char argc, const char *option);
#ifdef READYFS_OVERLAY_RUNTIME
static void probe_iec_io(ReadyFsDriveUiCall *call);
static unsigned char drive_partition_command(const char *text,
                                             const char *destination,
                                             unsigned char argc,
                                             unsigned char operation);
static unsigned char recursive_batch(unsigned char argc,
                                     unsigned char mode);
#endif

#ifndef READYFS_OVERLAY_RUNTIME
static unsigned char plan_reu_write(unsigned int offset, const void *data,
                                    unsigned int length) {
    if (offset > RF_REU_PLAN_BYTES ||
        length > (unsigned int)(RF_REU_PLAN_BYTES - offset)) return 0u;
    return readyfs_reu_session_store((unsigned int)(RF_REU_PLAN_OFF + offset),
                                     data, length);
}
static unsigned char plan_reu_read(unsigned int offset, void *data,
                                   unsigned int length) {
    if (offset > RF_REU_PLAN_BYTES ||
        length > (unsigned int)(RF_REU_PLAN_BYTES - offset)) return 0u;
    return readyfs_reu_session_fetch((unsigned int)(RF_REU_PLAN_OFF + offset),
                                     data, length);
}
#endif

static void newline(void) { cputc('\r'); cputc('\n'); }

static char *format_u16(char *output, unsigned int value) {
    utility_ui.operation = RF_UTILITY_FORMAT_U16;
    utility_ui.buffer = output;
    utility_ui.capacity = 6u;
    utility_ui.value_low = value;
    if (!readyfs_overlay_utility(&utility_ui)) {
        output[0] = 0; return output;
    }
    return output + utility_ui.capacity;
}

void print_u16(unsigned int value) {
    utility_ui.operation = RF_UTILITY_PRINT_U16;
    utility_ui.value_low = value;
    if (!readyfs_overlay_utility(&utility_ui)) cputc('?');
}

static void print_u32_words(unsigned int high, unsigned int low) {
    utility_ui.operation = RF_UTILITY_PRINT_U32;
    utility_ui.value_high = high;
    utility_ui.value_low = low;
    if (!readyfs_overlay_utility(&utility_ui)) cputs("?");
}

#ifdef READYFS_OVERLAY_RUNTIME
extern unsigned char __fastcall__ readyfs_same_word(const char *a, const char *b);
#define same_word readyfs_same_word
#else
static unsigned char same_word(const char *a, const char *b) {
    unsigned char ca;
    unsigned char cb;

    while (*a != 0 && *b != 0) {
        /* Physical IEC directory readers can return the same PETSCII letters
         * with bit 7 set (for example D2 vs 52 on a mounted 1581 image). */
        ca = (unsigned char)*a++ & 0x7Fu;
        cb = (unsigned char)*b++ & 0x7Fu;
        if (ca >= 'A' && ca <= 'Z') ca = (unsigned char)(ca + 32u);
        if (cb >= 'A' && cb <= 'Z') cb = (unsigned char)(cb + 32u);
        if (ca != cb) return 0u;
    }
    return (unsigned char)(*a == 0 && *b == 0);
}
#endif

static unsigned int alias_reu_offset(unsigned char slot) {
    return (unsigned int)((unsigned int)slot * RF_ALIAS_SLOT_BYTES);
}

static unsigned char alias_fetch(unsigned char slot) {
    if (!reu_available || slot >= RF_ALIAS_SLOTS) return 0u;
    return readyfs_reu_session_fetch(alias_reu_offset(slot), &alias_slot,
                                     RF_ALIAS_SLOT_BYTES);
}

static unsigned char alias_store(unsigned char slot) {
    if (!reu_available || slot >= RF_ALIAS_SLOTS) return 0u;
    return readyfs_reu_session_store(alias_reu_offset(slot), &alias_slot,
                                     RF_ALIAS_SLOT_BYTES);
}

static void aliases_clear_reu(void) {
    unsigned char i;
    memset(&alias_slot, 0, sizeof(alias_slot));
    for (i = 0u; i < RF_ALIAS_SLOTS; ++i) (void)alias_store(i);
}

static signed char alias_find_name(const char *name, unsigned char name_len) {
    unsigned char i;
    unsigned char j;
    char probe[RF_ALIAS_NAME + 1u];

    if (name_len == 0u || name_len > RF_ALIAS_NAME) return -1;
    for (j = 0u; j < name_len; ++j) probe[j] = name[j];
    probe[name_len] = 0;
    for (i = 0u; i < RF_ALIAS_SLOTS; ++i) {
        if (!alias_fetch(i)) return -1;
        alias_slot.name[RF_ALIAS_NAME] = 0;
        if (strlen(alias_slot.name) == name_len &&
            same_word(alias_slot.name, probe)) return (signed char)i;
    }
    return -1;
}

static unsigned char resolve_path(const char *input, char *out) {
    ReadyFsPath parsed;
#ifdef READYFS_OVERLAY_RUNTIME
    ReadyFsResolveCall call;
#else
    const char *suffix;
    const char *colon;
    unsigned int root_len;
    unsigned int suffix_len;
#endif
    unsigned char rc;
    signed char slot;

    if (input == 0 || input[0] == 0) return RF_PATH_EMPTY;
    rc = readyfs_path_parse(input, &parsed);
#ifdef READYFS_OVERLAY_RUNTIME
    call.input = input;
    call.cwd = cwd_buf;
    call.alias_root = 0;
    call.output = out;
    if (rc == RF_PATH_OK && parsed.endpoint == RF_EP_ALIAS) {
        slot = alias_find_name(input + 1u, parsed.alias_len);
        if (slot < 0) return RF_PATH_BAD_ENDPOINT;
        if (!alias_fetch((unsigned char)slot)) return RF_PATH_BAD_ENDPOINT;
        call.alias_root = alias_slot.root;
    }
    if (!readyfs_overlay_match(RF_MATCH_RESOLVE_PATH, (const char *)&call))
        return RF_PATH_BAD_ENDPOINT;
    return call.result;
#else
    if (rc == RF_PATH_OK && parsed.endpoint != RF_EP_ALIAS) {
        strcpy(out, input);
        return readyfs_path_normalize(out, out);
    }
    if (rc == RF_PATH_OK && parsed.endpoint == RF_EP_ALIAS) {
        slot = alias_find_name(input + 1u, parsed.alias_len);
        if (slot < 0 || !alias_fetch((unsigned char)slot))
            return RF_PATH_BAD_ENDPOINT;
        suffix = input + parsed.path_offset;
        if (readyfs_path_has_parent_escape(suffix)) return RF_PATH_ESCAPE;
        root_len = strlen(alias_slot.root);
        suffix_len = strlen(suffix);
        if (root_len + suffix_len + 1u > RF_LINE_CAP)
            return RF_PATH_TOO_LONG;
        strcpy(out, alias_slot.root);
        if (root_len != 0u && out[root_len - 1u] == '/' && suffix[0] == '/') {
            ++suffix;
        } else if (root_len != 0u && out[root_len - 1u] != '/' &&
                   suffix[0] != '/' && suffix[0] != 0) {
            out[root_len++] = '/';
            out[root_len] = 0;
        }
        strcat(out, suffix);
        rc = readyfs_path_parse(out, &parsed);
        if (rc == RF_PATH_OK) rc = readyfs_path_normalize(out, out);
        return rc;
    }
    if (strchr(input, ':') != 0) return rc;
    if (input[0] == '/') {
        colon = strchr(cwd_buf, ':');
        if (colon == 0) return RF_PATH_BAD_ENDPOINT;
        root_len = (unsigned int)(colon - cwd_buf + 1u);
        if (root_len + strlen(input) > RF_LINE_CAP) return RF_PATH_TOO_LONG;
        memcpy(out, cwd_buf, root_len);
        strcpy(out + root_len, input);
    } else {
        root_len = strlen(cwd_buf);
        suffix_len = strlen(input);
        if (root_len + suffix_len + 2u > RF_LINE_CAP)
            return RF_PATH_TOO_LONG;
        strcpy(out, cwd_buf);
        if (root_len != 0u && out[root_len - 1u] != '/') {
            out[root_len++] = '/';
            out[root_len] = 0;
        }
        strcat(out, input);
    }
    rc = readyfs_path_parse(out, &parsed);
    if (rc == RF_PATH_OK) rc = readyfs_path_normalize(out, out);
    return rc;
#endif
}

#ifdef READYFS_OVERLAY_RUNTIME
static void cmd_alias_call(unsigned char argc, unsigned char remove) {
    unsigned char rc;
    if (!remove && argc >= 3u) {
        rc = resolve_path(args[2], temp_text);
        if (rc != RF_PATH_OK) { cputc(0x1Cu); cputs(readyfs_path_error(rc)); newline(); return; }
    }
    batch_ui.operation = RF_BATCH_ALIAS;
    batch_ui.argc = argc;
    batch_ui.args = args;
    batch_ui.buffer = temp_text;
    batch_ui.finish = remove;
    batch_ui.reu_available = reu_available;
    (void)readyfs_overlay_batch(&batch_ui);
}
static void cmd_alias(unsigned char argc) { cmd_alias_call(argc, 0u); }
static void cmd_unalias(unsigned char argc) { cmd_alias_call(argc, 1u); }
#else
static void cmd_alias(unsigned char argc) {
    ReadyFsPath path;
    signed char slot;
    unsigned char i;
    unsigned char name_len;
    unsigned char rc;

    if (!reu_available) { cputs(RF_ERROR "need reu\r\n"); return; }
    if (argc == 1u) {
        for (i = 0u; i < RF_ALIAS_SLOTS; ++i) {
            if (alias_fetch(i) && alias_slot.name[0] != 0) {
                cputc('@'); cputs(alias_slot.name); cputs(": ");
                cputs(alias_slot.root); newline();
            }
        }
        return;
    }
    if (argc < 3u) {
        cputs("alias N PATH\r\n");
        return;
    }
    name_len = strlen(args[1]);
    if (name_len == 0u || name_len > RF_ALIAS_NAME ||
        strchr(args[1], ':') != 0 || strchr(args[1], '/') != 0 ||
        strchr(args[1], '@') != 0) {
        cputs(RF_ERROR "bad alias\r\n");
        return;
    }
    rc = resolve_path(args[2], temp_text);
    if (rc != RF_PATH_OK || readyfs_path_parse(temp_text, &path) != RF_PATH_OK ||
        path.endpoint == RF_EP_ALIAS || !path.absolute) {
        if (rc == RF_PATH_OK) cputs("abs root");
        else { cputc(0x1Cu); cputs(readyfs_path_error(rc)); }
        newline();
        return;
    }
    slot = alias_find_name(args[1], name_len);
    if (slot < 0) {
        for (i = 0u; i < RF_ALIAS_SLOTS; ++i) {
            if (alias_fetch(i) && alias_slot.name[0] == 0) {
                slot = (signed char)i;
                break;
            }
        }
    }
    if (slot < 0) { cputs(RF_ERROR "aliases full\r\n"); return; }
    strcpy(alias_slot.name, args[1]);
    strcpy(alias_slot.root, temp_text);
    if (!alias_store((unsigned char)slot)) {
        cputs("alias reu\r\n");
        return;
    }
    cputs(RF_SUMMARY "alias set\r\n");
}

static void cmd_unalias(unsigned char argc) {
    signed char slot;
    if (argc < 2u) { cputs("unalias N\r\n"); return; }
    if (!reu_available) { cputs(RF_ERROR "need reu\r\n"); return; }
    slot = alias_find_name(args[1], strlen(args[1]));
    if (slot < 0) { cputs(RF_ERROR "noalias\r\n"); return; }
    memset(&alias_slot, 0, sizeof(alias_slot));
    (void)alias_store((unsigned char)slot);
    cputs(RF_SUMMARY "removed\r\n");
}

#endif

static unsigned char split_args(char *text) {
#ifdef READYFS_OVERLAY_RUNTIME
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_SPLIT_ARGS;
    tape_call.text = text;
    tape_call.args = args;
    if (!readyfs_overlay_tape(&tape_call)) return 0u;
    return tape_call.result;
#else
    unsigned char count;
    unsigned char quote;
    char *readp;
    char *writep;

    count = 0u;
    readp = text;
    writep = text;
    while (*readp != 0 && count < RF_ARG_CAP) {
        while (*readp == ' ') ++readp;
        if (*readp == 0) break;
        args[count++] = writep;
        quote = 0u;
        if (*readp == '"') {
            quote = 1u;
            ++readp;
        }
        while (*readp != 0) {
            if (quote) {
                if (*readp == '"') {
                    ++readp;
                    break;
                }
            } else if (*readp == ' ') {
                break;
            }
            *writep++ = *readp++;
        }
        if (!quote && *readp == ' ') ++readp;
        *writep++ = 0;
        while (*readp == ' ') ++readp;
    }
    return count;
#endif
}

static unsigned char dir_page_lines;
static unsigned char dispatch_command;

static void dir_page_line(void) {
    if (dir_page_lines == RF_DIR_PAGE) {
        cputs(RF_SUMMARY "-- more --" RF_NORMAL);
        (void)cgetc();
        clrscr();
        dir_page_lines = 0u;
    }
    ++dir_page_lines;
}

static void read_line(void) {
#ifdef READYFS_OVERLAY_RUNTIME
    batch_ui.operation = RF_BATCH_EDITOR;
    batch_ui.buffer = line_buf;
    batch_ui.capacity = sizeof(line_buf);
    batch_ui.reu_available = reu_available;
    if (!readyfs_overlay_batch(&batch_ui)) line_buf[0] = 0;
#else
    unsigned char ch;
    unsigned int length;
    length = 0u;
    cputs("rf> ");
    for (;;) {
        ch = cgetc();
        if (ch == CH_ENTER || ch == CH_STOP) break;
        if (ch == CH_DEL) {
            if (length != 0u) --length;
        } else if (ch >= 32u && length < RF_LINE_CAP) {
            line_buf[length++] = (char)ch;
        }
    }
    line_buf[length] = 0;
    newline();
#endif
}

static void setup_xfer(void) {
    uci_xfer.data = uci_data;
    uci_xfer.data_cap = sizeof(uci_data);
    uci_xfer.stat = uci_stat;
    uci_xfer.stat_cap = sizeof(uci_stat);
    uci_xfer.on_block = 0;
}

static unsigned char uci_status_ok(unsigned char target) {
    /* Target5 accepts binary success as well as firmware3.14's legacy ASCII.
     * Every target shares the strict nonempty ASCII00 fallback. */
    if (target == 5u && uci_xfer.stat_len != 0u && uci_stat[0] == 0u)
        return 1u;
    return (unsigned char)(uci_xfer.stat_len >= 2u &&
                           uci_stat[0] == '0' && uci_stat[1] == '0');
}

static void show_uci_failure(void) {
#ifdef READYFS_OVERLAY_RUNTIME
    utility_ui.operation = RF_PRESENT_UCI_ERROR;
    utility_ui.buffer = (char *)&uci_xfer;
    (void)readyfs_overlay_present(&utility_ui);
#else

    unsigned int i;

    if (uci_xfer.flags != 0u) {
        cputs("transport $");
        cputhex8(uci_xfer.flags);
        cputs(" st $");
        cputhex8(uci_xfer.last_status);
        cputs(" d/s ");
        print_u16(uci_xfer.data_seen);
        cputc('/');
        print_u16(uci_xfer.stat_seen);
        newline();
        return;
    }
    cputs("target: ");
    for (i = 0u; i < uci_xfer.stat_len; ++i) {
        if (uci_stat[i] >= 32u && uci_stat[i] < 127u) cputc(uci_stat[i]);
        else {
            cputc('$');
            cputhex8(uci_stat[i]);
            cputc(' ');
        }
    }
    newline();
#endif
}

static unsigned char uci_call(unsigned char target, unsigned char command,
                              const char *arg) {
    unsigned int len;

    uci_cmd[0] = target;
    uci_cmd[1] = command;
    len = 2u;
    if (arg != 0) {
        while (*arg != 0 && len < sizeof(uci_cmd)) uci_cmd[len++] = (unsigned char)*arg++;
    }
    setup_xfer();
    /* One complete state-driven transaction. The transport owns PUSH,
     * LAST/MORE, both queue drains, DATA_ACC, recovery, and quiet IDLE. */
    if (!readyfs_uci_command(uci_cmd, len, &uci_xfer)) {
        show_uci_failure();
        return 0u;
    }
    return 1u;
}

static unsigned char uci_call_raw(const unsigned char *command,
                                  unsigned int length) {
    setup_xfer();
    /* Sole app-level UCI command gateway: no caller paces this transaction or
     * interprets immediate IDLE as completion. */
    if (!readyfs_uci_command(command, length, &uci_xfer)) {
        show_uci_failure();
        return 0u;
    }
    return 1u;
}

static void print_data_text(void) {
#ifdef READYFS_OVERLAY_RUNTIME
    utility_ui.operation = RF_PRESENT_DATA_TEXT;
    utility_ui.buffer = (char *)uci_data;
    utility_ui.value_low = uci_xfer.data_len;
    (void)readyfs_overlay_present(&utility_ui);
#else
    unsigned int i;

    for (i = 0u; i < uci_xfer.data_len; ++i) {
        if (uci_data[i] >= 32u && uci_data[i] < 127u) cputc(uci_data[i]);
        else cputc('.');
    }
#endif
}

static void probe_target(unsigned char target, const char *name) {
    cputs(name);
    cputs(": ");
    if (!uci_call(target, 0x01u, 0)) return;
    if (!uci_status_ok(target)) {
        show_uci_failure();
        return;
    }
    print_data_text();
    newline();
}

static int iec_command_status(unsigned char device, const char *command) {
    int count;
    if (cbm_open(15u, device, 15u, command) != 0u) return -1;
    count = cbm_read(15u, io_buf, sizeof(io_buf) - 1u);
    cbm_close(15u);
    cbm_k_clrch();
    return count;
}

static unsigned char iec_command_ok(unsigned char device,
                                    const char *command) {
    return (unsigned char)(iec_command_status(device, command) >= 2 &&
                           io_buf[0] == '0' && io_buf[1] == '0');
}

#ifdef READYFS_OVERLAY_RUNTIME
static void probe_iec_io(ReadyFsDriveUiCall *call) {
    int count;

    call->io_ok = 0u;
    cbm_k_clall();
    count = iec_command_status(call->device,
                              call->output == 0 ? "ui" : call->output);
    if (count < 0) return;
    io_buf[count] = 0;
    call->io_ok = (unsigned char)(call->output == 0 ||
                         (count >= 2 && io_buf[0] == '0' &&
                                       io_buf[1] == '0'));
}
#endif

static void cmd_probe(unsigned char argc) {
    unsigned int base;
    unsigned char all;

    all = (unsigned char)(argc < 2u || same_word(args[1], "all"));
    if (!all && same_word(args[1], "recover")) {
        cputs("uci recover: ");
        if (!readyfs_uci_detect()) {
            cputs(RF_ERROR "off\r\n");
            return;
        }
        if (!readyfs_uci_recovery_probe()) {
            cputs(RF_ERROR "fail\r\n");
            return;
        }
        cputs("quiet\r\n");
        probe_target(1u, "udos1");
        return;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    if (!all && same_word(args[1], "iec")) {
        drive_ui.operation = RF_DRIVEUI_BEGIN;
        drive_ui.argc = argc;
        drive_ui.args = args;
        drive_ui.status = (char *)io_buf;
        drive_ui.output = 0;
        if (!readyfs_overlay_drive(&drive_ui)) {
            cputs(RF_ERROR "op failed\r\n");
            return;
        }
        if (drive_ui.pending) {
            probe_iec_io(&drive_ui);
            drive_ui.operation = RF_DRIVEUI_COMPLETE;
            (void)readyfs_overlay_drive(&drive_ui);
        }
        return;
    }
#endif
    if (all || same_word(args[1], "uci")) {
        base = readyfs_uci_base();
        if (base == 0u) cputs(RF_ERROR "uci: off\r\n");
        else {
            cputs("uci: base $");
            cputhex16(base);
            cputs(" id $");
            cputhex8(readyfs_uci_id());
            newline();
        }
    }
    if (!readyfs_uci_detect()) return;
    if (all || same_word(args[1], "udos")) probe_target(1u, "udos1");
    if (all || same_word(args[1], "softiec")) {
        probe_target(5u, "softiec");
        cputs("softiec bus: ");
        cputhex8(readyfs_uci_softiec_bus());
        newline();
    }
}

#ifndef READYFS_OVERLAY_RUNTIME
unsigned char readyfs_iec_present(unsigned char device) {
    unsigned char status;

    /* Discovery only needs the IEC listener handshake. Opening a complete
     * command channel for every absent unit can hold the shell for minutes;
     * actual operations still open their normal data/command channels and
     * report the device's DOS status. KERNAL ST bit 7 is device-not-present. */
    cbm_k_listen(device);
    status = cbm_k_readst();
    cbm_k_unlsn();
    cbm_k_clrch();
    return (unsigned char)((status & 0x80u) == 0u);
}
#endif

#ifdef READYFS_OVERLAY_RUNTIME
static void media(unsigned char mode, unsigned char unit, const char *path) {
    utility_ui.operation = RF_PRESENT_MEDIA;
    utility_ui.value_high = mode;
    utility_ui.value_low = unit;
    utility_ui.buffer = (char *)path;
    (void)readyfs_overlay_present(&utility_ui);
}
static void cmd_drives(void) { media(RF_MEDIA_DRIVES, 0u, 0); }
#else

static void cmd_drives(void) {
    unsigned char device;
    unsigned char count;
    unsigned char detected;

    detected = readyfs_uci_detect();
    count = 0u;
    for (device = 8u; device <= 30u; ++device) {
        if (readyfs_iec_present(device)) uci_data[count++] = device;
    }
    utility_ui.operation = RF_UTILITY_DRIVES;
    utility_ui.buffer = (char *)uci_data;
    utility_ui.capacity = count;
    utility_ui.value_high = detected;
    utility_ui.value_low = readyfs_uci_softiec_bus();
    if (!readyfs_overlay_utility(&utility_ui))
        result_unavailable("utility off\r\n");
}

#endif

typedef char ReadyFsDirentAbiFits[sizeof(struct cbm_dirent) == sizeof(ReadyFsDirectoryEntry)];
static unsigned int dir_stream_count;

static unsigned char dir_iec(unsigned char device, const char *native_directory,
                             unsigned char tree) {
    struct cbm_dirent entry;
    unsigned int count;
    unsigned char rc;

    if ((native_directory == 0 && cbm_opendir(2u, device) != 0u) ||
        (native_directory != 0 &&
         cbm_opendir(2u, device, native_directory) != 0u)) {
        if (!tree) cputs(RF_ERROR "dir open failed\r\n");
        return 0u;
    }
    count = 0u;
    if (!tree) {
#ifdef READYFS_OVERLAY_RUNTIME
        media(RF_MEDIA_SHOW, device, 0);
        dir_page_lines = (unsigned char)utility_ui.capacity;
#else
        dir_page_lines = 0u;
#endif
    }
    rc = cbm_readdir(2u, &entry);
    while (count < RF_DIR_LIMIT && rc == 0u) {
#ifdef READYFS_OVERLAY_RUNTIME
        if (tree) {
            if (entry.type != CBM_T_HEADER) {
                tree_add(entry.name, entry.type == CBM_T_DIR ?
                         RF_TREE_KIND_DIR : RF_TREE_KIND_FILE);
                ++count;
            }
            if (tree_failed) break;
        } else {
#endif
            dir_page_line();
            utility_ui.operation = RF_PRESENT_DIR;
            utility_ui.buffer = (char *)&entry;
            (void)readyfs_overlay_present(&utility_ui);
            ++count;
#ifdef READYFS_OVERLAY_RUNTIME
        }
#endif
        rc = cbm_readdir(2u, &entry);
    }
    cbm_closedir(2u);
    cbm_k_clrch();
#ifdef READYFS_OVERLAY_RUNTIME
    if (tree) return (unsigned char)(rc == 2u && !tree_failed);
#endif

    /* cc65 returns 2 for the terminal BASIC-directory line and leaves the
     * drive's full 16-bit BLOCKS FREE value in entry.size (important for
     * D71/D81 and CMD-class media; never truncate it to one byte). */
    if (rc == 2u) {
        utility_ui.operation = RF_PRESENT_FREE;
        utility_ui.value_low = entry.size;
        (void)readyfs_overlay_present(&utility_ui);
    }
    if (count >= RF_DIR_LIMIT) cputs(RF_ERROR "dir limit\r\n");
    return (unsigned char)(rc == 2u);
}

#ifdef READYFS_OVERLAY_RUNTIME
#define udos_call (*(ReadyFsUdosFilesCall *)(void *)readyfs_pipeline_scratch)
static unsigned char udos_open_targets;
static void udos_setup(ReadyFsStream *stream, unsigned char target,
                        unsigned char operation) {
    memset(&udos_call, 0, sizeof(udos_call));
    udos_call.stream = stream;
    udos_call.target = target;
    udos_call.operation = operation;
    udos_call.status = &last_result;
    udos_call.open_targets = &udos_open_targets;
    udos_call.access = temp_text;
    udos_call.name = temp_text + 80u;
    udos_call.wire = temp_text + 100u;
    if (stream) udos_call.type = stream->type;
}
static unsigned char udos_file(ReadyFsStream *stream, unsigned char target,
                               unsigned char operation) {
    unsigned char result;
    udos_setup(stream, target, operation);
    result = readyfs_overlay_udos(&udos_call);
    /* FIND may quietly report absence for destination admission. READ must
     * expose it as a command failure, including STAT/TYPE and COPY sources. */
    if (operation == RF_UDOS_READ && result == RF_LOOKUP_MISSING) {
        last_result = RF_RESULT_NOT_FOUND;
        cputs(RF_ERROR "not found\r\n");
    }
    return result;
}
#endif

static unsigned char udos_change_absolute(unsigned char target,
                                          const char *path) {
#ifdef READYFS_OVERLAY_RUNTIME
    udos_setup(0, target, RF_UDOS_CHANGE);
    udos_call.path = path;
    return readyfs_overlay_udos(&udos_call) == RF_LOOKUP_FOUND;
#else
    char segment[64];
    unsigned char len;

    if (!uci_call(target, 0x11u, "/")) return 0u;
    if (!uci_status_ok(target)) return 0u;
    while (*path == '/') ++path;
    while (*path != 0) {
        len = 0u;
        while (*path != 0 && *path != '/' && *path != '!') {
            if (len + 1u >= sizeof(segment)) return 0u;
            segment[len++] = *path++;
        }
        segment[len] = 0;
        while (*path == '/' || *path == '!') ++path;
        if (len == 0u) continue;
        if (!uci_call(target, 0x11u, segment) || !uci_status_ok(target)) {
            show_uci_failure();
            return 0u;
        }
    }
    return 1u;
#endif
}

/* OPEN_DIR has a successful empty result distinct from generic 00 OK.
 * READ_DIR must not follow it: firmware has no directory entry to return. */
static unsigned char udos_open_directory(unsigned char target) {
    static const unsigned char empty_status[]=RF_UDOS_EMPTY_BYTES;
    if (!uci_call(target, 0x13u, 0)) return 0u;
    if (uci_status_ok(target)) return 1u;
    if ((uci_xfer.stat_len == 18u
#ifdef READYFS_OVERLAY_RUNTIME
         || (uci_xfer.stat_len == 19u && uci_stat[18u] == 0u)
#endif
         ) && memcmp(uci_stat, empty_status, 18u) == 0)
        return 2u;
    return 0u;
}

static void dir_ultimate_block(const unsigned char *data,
                               unsigned int data_len,
                               const unsigned char *stat,
                               unsigned int stat_len) {
    (void)stat;
    (void)stat_len;
    if (data_len == 0u || dir_stream_count >= RF_DIR_LIMIT) return;
    dir_page_line();
    utility_ui.operation = RF_PRESENT_HOST;
    utility_ui.buffer = (char *)data + 1u;
    utility_ui.capacity = data_len - 1u;
    utility_ui.value_high = (data[0] & 0x10u) ? 2u : 4u;
    (void)readyfs_overlay_present(&utility_ui);
    ++dir_stream_count;
}

static unsigned char dir_ultimate_run(const char *path,
                                      ReadyFsUciBlockHandler handler) {
    unsigned char opened;
    if (!udos_change_absolute(1u, path)) {
        return 0u;
    }
    opened = udos_open_directory(1u);
    if (opened != 1u) return (unsigned char)(opened == 2u);
    uci_cmd[0] = 1u;
    uci_cmd[1] = 0x14u;
    setup_xfer();
    uci_xfer.on_block = handler;
    /* One complete state-driven streaming transaction. The transport owns
     * asynchronous PUSH/DATA_ACC, all entry blocks, and final quiet IDLE. */
    return readyfs_uci_command(uci_cmd, 2u, &uci_xfer);
}

static void dir_ultimate(const char *path) {
    dir_stream_count = 0u;
    dir_page_lines = 0u;
    if (!dir_ultimate_run(path, dir_ultimate_block)) {
        show_uci_failure();
        return;
    }
    if (dir_stream_count >= RF_DIR_LIMIT) cputs(RF_ERROR "dir limit\r\n");
}

static unsigned char iec_partition_driver_pending(const ReadyFsPath *path) {
    if (path->endpoint != RF_EP_IEC || path->partition == 0u) return 0u;
    result_unsupported("unsupported\r\n");
    return 1u;
}

static void cmd_dir(unsigned char argc) {
    ReadyFsPath path;
    const char *text;
    unsigned char rc;

    text = (argc >= 2u) ? args[1] : cwd_buf;
    rc = resolve_path(text, temp_text);
    if (rc == RF_PATH_OK) rc = readyfs_path_parse(temp_text, &path);
    if (rc != RF_PATH_OK) {
        cputc(0x1Cu); cputs(readyfs_path_error(rc));
        newline();
        return;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    if (argc > 2u && same_word(args[2], "--native-pattern")) {
        (void)drive_partition_command(text, 0, argc,
                                      RF_CMDPATH_NATIVE_DIR);
        return;
    }
    if (path.endpoint == RF_EP_IEC) {
        (void)drive_partition_command(text, 0, argc, RF_CMDPATH_DIRECTORY);
        return;
    }
#else
    if (iec_partition_driver_pending(&path)) return;
    if (path.endpoint == RF_EP_IEC) {
        if (temp_text[path.path_offset + 1u] != 0)
            result_unsupported("unsupported\r\n");
        else (void)dir_iec(path.unit, 0, 0u);
    }
    else
#endif
    if (path.endpoint == RF_EP_ULTIMATE) {
        dir_ultimate(temp_text + path.path_offset);
    } else if (path.endpoint == RF_EP_SOFTIEC) {
        if (!readyfs_uci_detect()) {
            result_unavailable("softiec off\r\n");
            return;
        }
        result_unsupported("unsupported\r\n");
    } else result_unsupported("unsupported\r\n");
}

static void cmd_cd(unsigned char argc) {
    if (argc < 2u) { cputs(cwd_buf); newline(); return; }
    utility_ui.operation = RF_PRESENT_CD;
    utility_ui.buffer = temp_text;
    utility_ui.workspace = cwd_buf;
    utility_ui.value_low = resolve_path(args[1], temp_text);
    (void)readyfs_overlay_present(&utility_ui);
}



static ReadyFsStream source;
/* Command dispatch is single-threaded. Single-path commands reuse source;
 * multi-stream staged operations retain the distinct workspaces below. */
#define command_stream source
static ReadyFsStream dest;
static ReadyFsStream temp;
#ifdef READYFS_OVERLAY_RUNTIME
#define backup (*(ReadyFsStream *)(void *)alias_backup_storage)
typedef char ReadyFsAliasBackupFits[
    sizeof(ReadyFsStream) <= sizeof(alias_backup_storage)];
static ReadyFsRecursiveCall recursive_call;
static unsigned char tree_find;
static const char *tree_include;
static const char *tree_exclude;
#else
static ReadyFsStream backup;
#endif
static ReadyFsSignature left_signature;
static ReadyFsSignature right_signature;
static ReadyFsIoCopyCall copy_call;
static unsigned char softiec_enter_parent(ReadyFsStream *stream);
static unsigned char iec_directory_command(unsigned char device,
                                           const char *verb,
                                           const char *name);
#ifdef READYFS_OVERLAY_RUNTIME
static ReadyFsBackendCall backend_call;
#define action_state (*(ReadyFsActionState *)(void *)&backup)
#define drive_command (*(ReadyFsDriveUiCall *)(void *)&source)
#define native_plan (*(ReadyFsNativePlanCall *)(void *)&dest)
typedef char ReadyFsNativePlanFits[
    sizeof(ReadyFsNativePlanCall) <= sizeof(ReadyFsStream)];
typedef char ReadyFsTreeCallFits[
    sizeof(ReadyFsTreeCall) <= RF_PIPELINE_SCRATCH_BYTES];

static unsigned char tree_filter_accept(char *stem, unsigned char kind) {
    ReadyFsUltimateMatchCall *match_call;
    match_call = (ReadyFsUltimateMatchCall *)(void *)readyfs_pipeline_scratch;
    match_call->include = tree_include;
    match_call->exclude = tree_exclude;
    match_call->stem = stem;
    match_call->file = dest.path.endpoint == RF_EP_ULTIMATE ?
                       (unsigned char)(kind == RF_TREE_KIND_FILE) :
                       RF_MATCH_RAW_STEM;
    return readyfs_overlay_match(RF_MATCH_ULTIMATE_FILTER,
                                 (const char *)match_call);
}

static void tree_add(const char *name, unsigned char kind) {
    unsigned int parent_len;
    unsigned int name_len;
    unsigned char selected;
    if (tree_failed) return;
    parent_len = strlen(alias_slot.root);
    name_len = strlen(name);
    if (parent_len + name_len + (parent_len == 0u ? 1u : 2u) >
        sizeof(temp_text)) { tree_failed = 1u; return; }
    memcpy(temp_text, alias_slot.root, parent_len);
    if (parent_len != 0u) temp_text[parent_len++] = '/';
    memcpy(temp_text + parent_len, name, (unsigned int)(name_len + 1u));
    selected = (unsigned char)(!tree_find ||
                               tree_filter_accept(temp_text, kind));
    tree_ui.operation = RF_TREE_CALL_ADD;
    tree_ui.kind = kind;
    tree_ui.parent = alias_slot.root;
    tree_ui.name = name;
    /* ADD rebuilds output from the untouched raw parent/name pointers. For
     * UltimateDOS, temp_text may therefore stay normalized for filtering. */
    tree_ui.output = temp_text;
    tree_ui.output_capacity = sizeof(temp_text);
    tree_ui.selected = selected;
    tree_ui.display = (unsigned char)(tree_find < 2u &&
                                      (!tree_find || selected));
    if (!readyfs_overlay_tree(&tree_ui) || tree_ui.result != RF_TREE_OK) {
        tree_failed = 1u;
        return;
    }
}

static void tree_ultimate_block(const unsigned char *data,
                                unsigned int data_len,
                                const unsigned char *stat,
                                unsigned int stat_len) {
    unsigned int name_len;
    (void)stat;
    (void)stat_len;
    if (tree_failed || data_len < 2u) return;
    name_len = (unsigned int)(data_len - 1u);
    if (name_len > RF_LINE_CAP) { tree_failed = 1u; return; }
    memcpy(source.canonical, data + 1u, name_len);
    source.canonical[name_len] = 0;
    tree_add(source.canonical,
             (data[0] & 0x10u) ? RF_TREE_KIND_DIR : RF_TREE_KIND_FILE);
}

static void cmd_tree(unsigned char argc, unsigned char find) {
    if (argc < 2u || resolve_path(args[1], dest.canonical) != RF_PATH_OK ||
        readyfs_path_parse(dest.canonical, &dest.path) != RF_PATH_OK ||
        !dest.path.absolute || dest.path.image_depth != 0u) {
        cputs(find ? "find P [P]\r\n" : "tree P\r\n");
        return;
    }
    dest.device = dest.path.endpoint == RF_EP_SOFTIEC ? 1u :
                  (dest.path.endpoint == RF_EP_IEC ? 2u : 0u);
    if (dest.path.endpoint != RF_EP_ULTIMATE && !dest.device) {
        result_unsupported("unsupported\r\n"); return;
    }
    dest.text = dest.device ? dest.canonical :
                dest.canonical + dest.path.path_offset;
    dest.native_name = dest.device == 1u ? source.canonical : temp_text;
    tree_ui.operation = RF_TREE_CALL_INIT;
    tree_ui.max_depth = 32u;
    tree_ui.limit = RF_DIR_LIMIT;
    if (!readyfs_overlay_tree(&tree_ui)) {
        result_unavailable("tree off\r\n"); return;
    }
    tree_find = find;
    tree_include = option_value(argc, "--include");
    tree_exclude = option_value(argc, "--exclude");
    if (find != 2u && tree_include == 0 && argc >= 3u && args[2][0] != '-')
        tree_include = args[2];
    tree_failed = 0u;
    for (;;) {
        tree_ui.operation = RF_TREE_CALL_NEXT;
        tree_ui.name = dest.text;
        tree_ui.relative = alias_slot.root;
        tree_ui.relative_capacity = sizeof(alias_slot.root);
        tree_ui.output = (char *)dest.native_name;
        tree_ui.output_capacity = sizeof(temp_text);
        if (!readyfs_overlay_tree(&tree_ui)) { tree_failed = 1u; break; }
        if (tree_ui.result == RF_TREE_DONE) break;
        if (tree_ui.result != RF_TREE_OK) { tree_failed = 1u; break; }
        /* ReadyIRC-derived UCI state machine owns async PUSH/DATA_ACC,
         * complete queue drains, recovery, and final quiet IDLE. */
        if (dest.device == 1u) {
            source.device = readyfs_uci_softiec_bus();
            if (!softiec_enter_parent(&source) ||
                !iec_directory_command(source.device,
                                       "cd:", source.native_name)) {
                tree_failed = 1u; break;
            }
            temp_text[0] = '$'; temp_text[1] = 0;
        }
        if (dest.device == 2u) {
            if (!drive_partition_command(temp_text, 0, 0u,
                                         RF_CMDPATH_DIRECTORY)) {
                tree_failed = 1u; break;
            }
            continue;
        }
        if (!(dest.device == 1u ?
              dir_iec(source.device, temp_text, 1u) :
               dir_ultimate_run(temp_text, tree_ultimate_block)) ||
            tree_failed) {
            tree_failed = 1u; break;
        }
    }
    tree_ui.operation = RF_TREE_CALL_REPORT;
    tree_ui.display = (unsigned char)(find + 1u);
    if (find == 2u) tree_ui.display = 0u;
    tree_ui.selected = (unsigned char)!tree_failed;
    if (!readyfs_overlay_tree(&tree_ui) || tree_ui.result == RF_TREE_FULL) {
        tree_failed = 1u;
    }
}

static unsigned char action_begin(unsigned char action, const char *source,
                                  const char *destination) {
    backend_call.operation = RF_BACKEND_CALL_BEGIN;
    backend_call.action = action;
    backend_call.source_root = source;
    backend_call.destination_root = destination;
    backend_call.state = &action_state;
    return readyfs_overlay_backend_call(&backend_call);
}

static unsigned char action_complete(unsigned char succeeded) {
    backend_call.operation = RF_BACKEND_CALL_COMPLETE;
    backend_call.force = succeeded;
    return readyfs_overlay_backend_call(&backend_call);
}

static unsigned char drive_partition_command(const char *text,
                                             const char *destination,
                                             unsigned char argc,
                                             unsigned char operation) {
    if (resolve_path(text, temp.canonical) != RF_PATH_OK) return 0u;
    if (destination != 0 &&
        resolve_path(destination, dest.canonical) != RF_PATH_OK) return 0u;
    drive_command.operation = operation == RF_CMDPATH_FORMAT ?
                              RF_UTILITY_FORMAT_MEDIA :
                              RF_DRIVEUI_COMMAND_BEGIN;
    drive_command.argc = argc;
    drive_command.source = temp.canonical;
    drive_command.destination = destination == 0 ? 0 : dest.canonical;
    drive_command.output = temp_text;
    drive_command.output_capacity = sizeof(temp_text);
    drive_command.followup = backup.canonical;
    drive_command.followup_capacity = sizeof(backup.canonical);
    drive_command.backend = &backend_call;
    drive_command.state = &action_state;
    drive_command.native_operation = operation;
    drive_command.force = option_present(argc, "--force");
    if (!readyfs_overlay_drive(&drive_command)) return 0u;
    if (!drive_command.handled) {
        if (operation != RF_CMDPATH_DIRECTORY ||
            !path_prepare(temp.canonical, &source) ||
            native_file(&source, 0, RF_FILES_DIRECTORY) != RF_LOOKUP_FOUND) return 0u;
        return dir_iec(source.device, temp_text, argc == 0u);
    }
    if (drive_command.pending) {
        if (operation == RF_CMDPATH_DIRECTORY ||
            operation == RF_CMDPATH_NATIVE_DIR) {
            if (argc == 0u)
                return dir_iec(drive_command.device, drive_command.output, 1u);
            (void)dir_iec(drive_command.device, drive_command.output, 0u);
        } else {
            if (operation == RF_CMDPATH_MOUNT || operation == RF_CMDPATH_UNMOUNT)
                media(RF_MEDIA_FORGET, drive_command.device, 0);
            probe_iec_io(&drive_command);
            if (operation == RF_CMDPATH_UNMOUNT && drive_command.io_ok &&
                drive_command.followup != 0 &&
                drive_command.followup[0] != 0) {
                drive_command.output = drive_command.followup;
                drive_command.followup = 0;
                probe_iec_io(&drive_command);
            }
            drive_command.operation = RF_DRIVEUI_COMMAND_COMPLETE;
            (void)readyfs_overlay_drive(&drive_command);
            if (!drive_command.io_ok) last_result = RF_RESULT_IO;
            else if (operation == RF_CMDPATH_MOUNT)
                media(RF_MEDIA_REMEMBER, drive_command.device, temp.canonical);
        }
    }
    return 1u;
}

#endif
static const char *copy_source_text;
static const char *copy_destination_text;
static unsigned char copy_force;

static const char *udos_enter_parent(ReadyFsStream *stream,
                                     unsigned char target) {
#ifdef READYFS_OVERLAY_RUNTIME
    if (udos_file(stream, target, RF_UDOS_PARENT) != RF_LOOKUP_FOUND) return 0;
    return strrchr(stream->native_name, '/') + 1u;
#else
    char *last;
    unsigned int len;

    last = strrchr(stream->native_name, '/');
    if (last == 0 || last[1] == 0) return 0;
    len = (unsigned int)(last - stream->native_name);
    if (len == 0u) strcpy(temp_text, "/");
    else {
        memcpy(temp_text, stream->native_name, len);
        temp_text[len] = 0;
    }
    if (!udos_change_absolute(target, temp_text)) return 0;
    return last + 1u;
#endif
}

static const char *udos_find_wanted;
static const char *udos_find_display;
#ifdef READYFS_OVERLAY_RUNTIME
static unsigned char udos_lookup_failed;
#endif
#define udos_find_call \
    (*(ReadyFsUltimateFindCall *)(void *)readyfs_pipeline_scratch)
static void udos_find_block(const unsigned char *data,
                            unsigned int data_len,
                            const unsigned char *stat,
                            unsigned int stat_len) {
#ifdef READYFS_OVERLAY_RUNTIME
    if (stat_len) {
        if (stat_len < 2u || stat[0] != '0' || stat[1] != '0') udos_lookup_failed = 1u;
        last_result = udos_lookup_failed ? RF_RESULT_IO : RF_RESULT_OK;
    }
#else
    (void)stat; (void)stat_len;
#endif
    if (temp_text[0] != 0 || data_len < 2u) return;
    udos_find_call.wanted = udos_find_wanted;
    udos_find_call.entry = data + 1u;
    udos_find_call.entry_length = (unsigned int)(data_len - 1u);
    udos_find_call.access = temp_text;
    udos_find_call.display = udos_find_display;
    (void)readyfs_overlay_match(RF_MATCH_ULTIMATE_FIND,
                                (const char *)&udos_find_call);
}

static const char *udos_find_leaf(ReadyFsStream *stream,
                                  unsigned char target) {
    const char *wanted;
    unsigned char opened;

#ifdef READYFS_OVERLAY_RUNTIME
    last_result = RF_RESULT_IO;
    udos_lookup_failed = 0u;
#endif
#ifdef READYFS_OVERLAY_RUNTIME
    opened = udos_file(stream, target, RF_UDOS_FIND);
    if (opened != RF_UDOS_HOST_LOOKUP)
        return opened == RF_LOOKUP_FOUND ? temp_text : 0;
    wanted = strrchr(stream->native_name, '/') + 1u;
    /* Preparation succeeded; a subsequent directory error is still IO. */
    last_result = RF_RESULT_IO;
#else
    wanted = udos_enter_parent(stream, target);
    if (wanted == 0) return 0;
#endif
    opened = udos_open_directory(target);
    if (!opened) return 0;
    if (opened == 2u) {
        temp_text[0] = 0;
#ifdef READYFS_OVERLAY_RUNTIME
        last_result = RF_RESULT_OK;
#endif
        return 0;
    }
    udos_find_wanted = wanted;
    temp_text[0] = 0;
    uci_cmd[0] = target;
    uci_cmd[1] = 0x14u;
    setup_xfer();
    uci_xfer.on_block = udos_find_block;
    /* One state-driven directory stream. The transport drains every entry
     * block and owns asynchronous DATA_ACC/final quiet IDLE. */
    if (!readyfs_uci_command(uci_cmd, 2u, &uci_xfer)) return 0;
#ifdef READYFS_OVERLAY_RUNTIME
    if (last_result != RF_RESULT_OK) return 0;
#endif
    if (temp_text[0] != 0) return temp_text;
    return 0;
}

static unsigned char option_present(unsigned char argc, const char *option) {
#ifdef READYFS_OVERLAY_RUNTIME
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_OPTION_PRESENT;
    tape_call.argc = argc;
    tape_call.args = args;
    tape_call.text = option;
    if (!readyfs_overlay_tape(&tape_call)) return 0u;
    return tape_call.result;
#else
    unsigned char i;
    unsigned char accept_yes;
    accept_yes = same_word(option, "--force");
    for (i = 1u; i < argc; ++i) {
        if (same_word(args[i], option) ||
            (accept_yes && same_word(args[i], "--yes"))) return 1u;
    }
    return 0u;
#endif
}

static unsigned char stream_uses_iec(const ReadyFsStream *stream) {
    return (unsigned char)(stream->path.endpoint == RF_EP_IEC ||
                           stream->path.endpoint == RF_EP_SOFTIEC);
}

static unsigned char path_prepare(const char *text, ReadyFsStream *stream) {
    unsigned char rc;
#ifndef READYFS_OVERLAY_RUNTIME
    char *name;
#endif

    /* Rebuild the descriptor without erasing an in-place canonical input.
     * Parse fills path; preparation fills device/name; open fills channel/type. */
    stream->open = 0u;
    rc = resolve_path(text, stream->canonical);
#ifdef READYFS_OVERLAY_RUNTIME
    if (rc != RF_PATH_OK) {
        cputc(0x1Cu); cputs(readyfs_path_error(rc)); newline(); return 0u;
    }
    stream_call.stream = stream;
    stream_call.status = &last_result;
    stream_call.reply = (unsigned char *)temp_text + 128u;
    return readyfs_overlay_stream(&stream_call);
#else
    if (rc == RF_PATH_OK) rc = readyfs_path_parse(stream->canonical,
                                                   &stream->path);
    if (rc != RF_PATH_OK || !stream->path.absolute ||
        (stream->path.endpoint != RF_EP_IEC &&
         stream->path.endpoint != RF_EP_SOFTIEC &&
         stream->path.endpoint != RF_EP_ULTIMATE
#ifdef READYFS_OVERLAY_RUNTIME
         && stream->path.endpoint != RF_EP_TAPE
#endif
         )) {
        if (rc == RF_PATH_OK) {
            result_unsupported("unsupported\r\n");
        }
        else {
            cputc(0x1Cu); cputs(readyfs_path_error(rc));
            newline();
        }
        return 0u;
    }
    if (iec_partition_driver_pending(&stream->path)) return 0u;
    name = stream->canonical + stream->path.path_offset;
    if (stream->path.endpoint == RF_EP_IEC
#ifdef READYFS_OVERLAY_RUNTIME
        || stream->path.endpoint == RF_EP_TAPE
#endif
        ) {
        while (*name == '/') ++name;
#ifdef READYFS_OVERLAY_RUNTIME
        stream->device = stream->path.endpoint == RF_EP_TAPE ? 1u :
                                                               stream->path.unit;
#else
        stream->device = stream->path.unit;
#endif
    } else if (stream->path.endpoint == RF_EP_SOFTIEC) {
        if (!readyfs_uci_detect()) {
            result_unavailable("softiec off\r\n");
            return 0u;
        }
        stream->device = readyfs_uci_softiec_bus();
        if (stream->device < 8u || stream->device > 30u) {
            cputs(RF_ERROR "bad soft bus\r\n");
            return 0u;
        }
        /* Canonical s3:/path becomes the native SoftwareIEC open string
         * 3:/path simply by omitting its endpoint letter. */
        name = stream->canonical + 1u;
    }
    if (*name == 0 || (stream->path.endpoint == RF_EP_ULTIMATE &&
                       name[0] == '/' && name[1] == 0)) {
        cputs(RF_ERROR "file required\r\n");
        return 0u;
    }
    if (stream->path.endpoint == RF_EP_IEC &&
        (strchr(name, '/') != 0 || strchr(name, '!') != 0)) {
        result_unsupported("cmd path\r\n");
        return 0u;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    if (stream->path.endpoint == RF_EP_TAPE &&
        (strlen(name) > 16u || strchr(name, '/') != 0 ||
         strchr(name, '!') != 0)) {
        result_unsupported("tape leaf 1-16\r\n");
        return 0u;
    }
#endif
    if (stream->path.endpoint == RF_EP_ULTIMATE && strchr(name, '!') != 0) {
        result_unsupported("image off\r\n");
        return 0u;
    }
    stream->text = stream->canonical;
    stream->native_name = name;
    return 1u;
#endif
}

#ifdef READYFS_OVERLAY_RUNTIME
#define RF_FOUND(value) ((value) == RF_LOOKUP_FOUND)
#define RF_MISSING(value) ((value) == RF_LOOKUP_MISSING)
#define RF_LOOKUP_FAILED(value) ((value) == RF_LOOKUP_ERROR)
static unsigned char native_file(ReadyFsStream *stream, ReadyFsStream *other, unsigned char operation) {
    files_call.stream = stream;
    files_call.other = other;
    files_call.directory = 0;
    files_call.request = temp_text;
    files_call.reply = (unsigned char *)temp_text + 128u;
    files_call.status = &last_result;
    files_call.operation = operation;
    return readyfs_overlay_files(&files_call);
}
#else
#define RF_FOUND(value) (value)
#define RF_MISSING(value) (!(value))
#define RF_LOOKUP_FAILED(value) 0u
static unsigned char iec_find_type(unsigned char device, char *name,
                                   unsigned char *type_out) {
    struct cbm_dirent entry;

    if (cbm_opendir(6u, device) != 0u) return 0u;
    while (cbm_readdir(6u, &entry) == 0u) {
#ifdef READYFS_SOFT_TRACE
        cputs(entry.name); newline();
#endif
        if (same_word(entry.name, name)) {
            if (type_out != 0) *type_out = entry.type;
            /* Open the exact native PETSCII spelling returned by hardware.
             * Mounted 1581 images can report letters with bit 7 set. */
            strcpy(name, entry.name);
            cbm_closedir(6u);
            cbm_k_clrch();
            return 1u;
        }
    }
    cbm_closedir(6u);
    cbm_k_clrch();
    return 0u;
}

#endif

static void iec_open_name(char *out, const char *name,
                          unsigned char type, char mode);

static unsigned char softiec_enter_parent(ReadyFsStream *stream) {
    char *last;

    SOFT_DIAG(0x10u);
    /* Complete the prior read channel before changing SoftIEC paths. This
     * exact target-5 CLOSE uses the ReadyIRC-derived state-driven transport. */
    if (!uci_call(5u, 0x14u, "\2")) return 0u;
    /* Serialize the firmware worker before returning to IEC command-channel
     * traffic. This is a complete UCI transaction, not a CPU-delay loop. */
    if (!uci_call(5u, 0x01u, 0)) return 0u;
    /* Firmware 3.14 has a short CD command limit. Reset to the known
     * partition-0 root, then enter one bounded component at a time. */
    last = strrchr(stream->canonical, '/');
    if (last[1] == 0) return 0u;
#ifdef READYFS_SOFT_TRACE
    cputc('r');
#endif
    SOFT_DIAG(0x11u);
    if (!iec_command_ok(stream->device, "cd:/")) return 0u;
    SOFT_DIAG(0x12u);
#ifdef READYFS_SOFT_TRACE
    cputc('s');
#endif
    utility_ui.operation = RF_UTILITY_SOFT_CD;
    utility_ui.buffer = stream->canonical;
    utility_ui.workspace = temp_text;
    utility_ui.value_low = 0u;
    for (;;) {
#ifdef READYFS_SOFT_TRACE
        cputc('u');
#endif
        SOFT_DIAG(0x13u);
        if (!readyfs_overlay_utility(&utility_ui)) return 0u;
        SOFT_DIAG(0x14u);
        if (utility_ui.capacity == 0u) break;
#ifdef READYFS_SOFT_TRACE
        cputc('v');
#endif
        SOFT_DIAG(0x15u);
        if (!iec_command_ok(stream->device, temp_text)) return 0u;
        SOFT_DIAG(0x16u);
#ifdef READYFS_SOFT_TRACE
        cputc('w');
#endif
    }
    stream->native_name = last + 1u;
    return 1u;
}

static unsigned char softiec_find_type(ReadyFsStream *stream) {
    unsigned char type;
    SOFT_DIAG(0x30u);
#ifdef READYFS_SOFT_TRACE
    cputc('a');
#endif
    if (!softiec_enter_parent(stream)) {
#ifdef READYFS_OVERLAY_RUNTIME
        last_result = RF_RESULT_IO; return RF_LOOKUP_ERROR;
#else
        return 0u;
#endif
    }
    SOFT_DIAG(0x31u);
#ifdef READYFS_SOFT_TRACE
    cputc('b');
#endif
    /* Firmware 3.14 can truncate its BASIC directory stream before all FAT
     * entries. Probe the three non-REL CBM types through ordinary OPEN and
     * consume DOS status after each attempt instead. This mirrors the
     * firmware's .seq/.prg/.usr mapping and never scans a directory. Never
     * probe REL this way: SoftwareIEC opens REL with OPEN_ALWAYS and would
     * create a missing file merely while checking existence.
     * An OPEN of a directory reports 62, so directory commands continue to
     * use their command-channel path. */
    for (type = CBM_T_SEQ; type <= CBM_T_USR; ++type) {
        iec_open_name(temp_text, stream->native_name, type, 'r');
        SOFT_DIAG(0x42u);
        (void)cbm_open(6u, stream->device, 6u, temp_text);
        SOFT_DIAG(0x43u);
        cbm_close(6u);
        cbm_k_clrch();
        /* Complete the exact probe channel through the ReadyIRC-derived UCI
         * transport before another path command or probe is attempted. */
        SOFT_DIAG(0x44u);
        (void)uci_call(5u, 0x14u, "\6");
        SOFT_DIAG(0x45u);
        io_buf[0] = 0u;
        SOFT_DIAG(0x46u);
#ifdef READYFS_OVERLAY_RUNTIME
        if (iec_command_status(stream->device, "") < 2) {
            last_result = RF_RESULT_IO; return RF_LOOKUP_ERROR;
        }
#else
        (void)iec_command_status(stream->device, "");
#endif
        SOFT_DIAG(0x47u);
        /* This exact OPEN status is either 00 or a two-digit DOS error; the
         * precleared non-ASCII byte keeps a failed status read fail-closed. */
        if (io_buf[0] == '0'
#ifdef READYFS_OVERLAY_RUNTIME
            && io_buf[1] == '0'
#endif
            ) {
            stream->type = type;
            return 1u;
        }
#ifdef READYFS_OVERLAY_RUNTIME
        if (io_buf[0] != '6' || io_buf[1] != '2') {
            last_result = RF_RESULT_IO; return RF_LOOKUP_ERROR;
        }
#endif
    }
#ifdef READYFS_OVERLAY_RUNTIME
    stream->type = 0u;
#endif
    return 0u;
}

static unsigned char stream_find_type(ReadyFsStream *stream) {
    if (stream->path.endpoint == RF_EP_SOFTIEC) {
        return softiec_find_type(stream);
    }
#ifdef READYFS_OVERLAY_RUNTIME
    return native_file(stream, 0, RF_FILES_FIND);
#else
    return iec_find_type(stream->device, stream->native_name, &stream->type);
#endif
}

static unsigned char uci_target_ok(unsigned char target) {
    if (!uci_status_ok(target)) {
        show_uci_failure();
        return 0u;
    }
    return 1u;
}

static unsigned char uci_target_ok_or_quiet(unsigned char target) {
    if (uci_xfer.stat_len == 0u) return 1u;
    return uci_target_ok(target);
}

static unsigned char udos_stat(ReadyFsStream *stream) {
    /* C64 Ultimate firmware 3.14 returns 82,FILE NOT FOUND from FILE_STAT for
     * files that its own READ_DIR reports and FTP confirms. Directory lookup
     * is therefore the existence authority; metadata uses OPEN+FILE_INFO. */
#ifdef READYFS_OVERLAY_RUNTIME
    if (udos_find_leaf(stream, 1u)) return RF_LOOKUP_FOUND;
    return last_result == RF_RESULT_OK ? RF_LOOKUP_MISSING : RF_LOOKUP_ERROR;
#else
    return (unsigned char)(udos_find_leaf(stream, 1u) != 0);
#endif
}

static unsigned char stream_exists(ReadyFsStream *stream) {
#ifdef READYFS_OVERLAY_RUNTIME
    if (stream->path.endpoint == RF_EP_TAPE) return 0u;
#endif
    if (stream_uses_iec(stream)) {
        return stream_find_type(stream);
    }
    return udos_stat(stream);
}

#ifndef READYFS_OVERLAY_RUNTIME
static char type_letter(unsigned char type) {
    switch (type) {
        case CBM_T_PRG: return 'p';
        case CBM_T_USR: return 'u';
        case CBM_T_REL: return 'l';
        default: return 's';
    }
}
#endif

static unsigned char option_file_type(unsigned char argc) {
#ifdef READYFS_OVERLAY_RUNTIME
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_FILE_TYPE;
    tape_call.argc = argc;
    tape_call.args = args;
    if (!readyfs_overlay_tape(&tape_call)) return 0xFFu;
    return tape_call.result;
#else
    const char *value;
    value = option_value(argc, "--type");
    if (value == 0) return CBM_T_SEQ;
#ifdef READYFS_OVERLAY_RUNTIME
    tree_ui.operation = RF_TREE_CALL_COMMAND_ID;
    tree_ui.name = value;
    if (!readyfs_overlay_tree(&tree_ui)) return 0xFFu;
    if ((tree_ui.result & 0x80u) == 0u) return 0xFFu;
    return (unsigned char)(tree_ui.result & 0x7Fu);
#else
    if (same_word(value, "prg")) return CBM_T_PRG;
    if (same_word(value, "usr")) return CBM_T_USR;
    if (same_word(value, "seq")) return CBM_T_SEQ;
    return 0xFFu;
#endif
#endif
}

static void iec_open_name(char *out, const char *name,
                          unsigned char type, char mode) {
#ifdef READYFS_OVERLAY_RUNTIME
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_OPEN_NAME;
    tape_call.text = name;
    tape_call.output = out;
    tape_call.value = type;
    tape_call.value2 = (unsigned char)mode;
    (void)readyfs_overlay_tape(&tape_call);
#else
    unsigned char len;

    strcpy(out, name);
    len = strlen(out);
    out[len++] = ',';
    out[len++] = type_letter(type);
    out[len++] = ',';
    out[len++] = mode;
    out[len] = 0;
#endif
}

#ifndef READYFS_OVERLAY_RUNTIME
static unsigned char udos_open_file_type(unsigned char target) {
#ifdef READYFS_OVERLAY_RUNTIME
    if (!uci_call(target, 0x07u, 0) || uci_xfer.data_len < 11u) return CBM_T_SEQ;
    files_call.operation = RF_FILES_UDOS_TYPE;
    files_call.status = &last_result;
    files_call.reply = uci_data;
    return readyfs_overlay_files(&files_call);
#else
    unsigned char a;
    unsigned char b;
    unsigned char c;

    if (!uci_call(target, 0x07u, 0) || uci_xfer.data_len < 11u) return CBM_T_SEQ;
    a = uci_data[8u]; b = uci_data[9u]; c = uci_data[10u];
    if (a >= 'A' && a <= 'Z') a = (unsigned char)(a + 32u);
    if (b >= 'A' && b <= 'Z') b = (unsigned char)(b + 32u);
    if (c >= 'A' && c <= 'Z') c = (unsigned char)(c + 32u);
    if (a == 'p' && b == 'r' && c == 'g') return CBM_T_PRG;
    if (a == 'u' && b == 's' && c == 'r') return CBM_T_USR;
    if (a == 'r' && b == 'e' && c == 'l') return CBM_T_REL;
    return CBM_T_SEQ;
#endif
}
#endif

static unsigned char stream_open_read(ReadyFsStream *stream,
                                      unsigned char target,
                                      unsigned char lfn) {
#ifndef READYFS_OVERLAY_RUNTIME
    const char *leaf;
    unsigned int len;
#endif

    stream->target = target;
    stream->lfn = lfn;
#ifdef READYFS_OVERLAY_RUNTIME
    if (stream->path.endpoint == RF_EP_TAPE) {
        stream->type = CBM_T_SEQ;
        /* IEC operations can leave ST nonzero even after a successful close.
         * Cassette OPEN consumes that shared KERNAL status, so each device-1
         * transaction starts from a clean boundary. */
        RF_KERNAL_STATUS = 0u;
        if (cbm_open(lfn, 1u, 0u, stream->native_name) != 0u) {
            cputs(RF_ERROR "tape open fail\r\n");
            cbm_k_clrch();
            return 0u;
        }
    } else
#endif
    if (stream_uses_iec(stream)) {
        if (!RF_FOUND(stream_find_type(stream))) {
            cputs(RF_ERROR "not found\r\n");
            return 0u;
        }
#ifdef READYFS_OVERLAY_RUNTIME
        if (!RF_FOUND(native_file(stream, 0, RF_FILES_OPEN_READ))) return 0u;
#else
        if (stream->type == CBM_T_REL) {
            result_unsupported("rel unsupported\r\n");
            return 0u;
        }
        if (strlen(stream->native_name) + 4u > RF_LINE_CAP) {
            cputs(RF_ERROR "name long\r\n");
            return 0u;
        }
        iec_open_name(temp_text, stream->native_name, stream->type, 'r');
        if (cbm_open(lfn, stream->device, lfn, temp_text) != 0u) {
            cputs(RF_ERROR "source open\r\n");
            cbm_k_clrch();
            return 0u;
        }
#endif
    } else {
#ifdef READYFS_OVERLAY_RUNTIME
        return RF_FOUND(udos_file(stream, target, RF_UDOS_READ));
#else
        /* READ_DIR may omit dot-prefixed host files such as ownership
         * markers. OPEN is the existence authority for reads; entering the
         * parent first also preserves the normal raw host leaf unchanged. */
        leaf = udos_enter_parent(stream, target);
        if (leaf == 0) {
            cputs(RF_ERROR "source path\r\n"); return 0u;
        }
        uci_cmd[0] = target;
        uci_cmd[1] = 0x02u;
        uci_cmd[2] = 0x01u;
        len = 3u;
        strcpy((char *)uci_cmd + len, leaf);
        len += strlen(leaf);
        if (!uci_call_raw(uci_cmd, len)) {
            return 0u;
        }
        if (!uci_target_ok(target)) return 0u;
        stream->type = udos_open_file_type(target);
        if (stream->type == CBM_T_REL) {
            result_unsupported("rel unsupported\r\n");
            (void)uci_call(target, 0x03u, 0);
            return 0u;
        }
#endif
    }
    stream->open = 1u;
    return 1u;
}

static unsigned char stream_open_write(ReadyFsStream *stream,
                                       unsigned char target,
                                       unsigned char lfn,
                                       unsigned char source_type) {
#ifndef READYFS_OVERLAY_RUNTIME
    const char *leaf;
    unsigned int len;
#endif

    stream->target = target;
    stream->lfn = lfn;
    stream->type = source_type == 0u ? CBM_T_SEQ : source_type;
#ifdef READYFS_OVERLAY_RUNTIME
    if (stream->path.endpoint == RF_EP_TAPE) {
        RF_KERNAL_STATUS = 0u;
        if (cbm_open(lfn, 1u, 1u, stream->native_name) != 0u) {
            cputs(RF_ERROR "tape open fail\r\n");
            cbm_k_clrch();
            return 0u;
        }
    } else
#endif
    if (stream_uses_iec(stream)) {
        if (stream->path.endpoint == RF_EP_SOFTIEC) {
            if (!softiec_enter_parent(stream)) return 0u;
        }
#ifdef READYFS_OVERLAY_RUNTIME
        if (!RF_FOUND(native_file(stream, 0, RF_FILES_OPEN_WRITE))) return 0u;
#else
        if (strlen(stream->native_name) + 4u > RF_LINE_CAP) {
            cputs(RF_ERROR "name long\r\n");
            return 0u;
        }
        iec_open_name(temp_text, stream->native_name, stream->type, 'w');
        if (cbm_open(lfn, stream->device, lfn, temp_text) != 0u) {
            cputs(RF_ERROR "dest open\r\n");
            cbm_k_clrch();
            return 0u;
        }
#endif
    } else {
#ifdef READYFS_OVERLAY_RUNTIME
        return RF_FOUND(udos_file(stream, target, RF_UDOS_NEW));
#else
        leaf = udos_enter_parent(stream, target);
        if (leaf == 0) {
            cputs(RF_ERROR "dest path bad\r\n"); return 0u;
        }
        uci_cmd[0] = target;
        uci_cmd[1] = 0x02u;
        uci_cmd[2] = 0x06u; /* write + create new, no implicit replacement */
        len = 3u;
        strcpy((char *)uci_cmd + len, leaf);
        len += strlen(leaf);
        if (!uci_call_raw(uci_cmd, len)) {
            return 0u;
        }
        if (!uci_target_ok(target)) return 0u;
#endif
    }
    stream->open = 1u;
    return 1u;
}

static int stream_read(ReadyFsStream *stream, void *dst, unsigned int cap) {
    int got;

    if (stream->path.endpoint != RF_EP_ULTIMATE) {
#ifdef READYFS_OVERLAY_RUNTIME
        if (stream->path.endpoint == RF_EP_TAPE && stream->open == 2u)
            return 0;
#endif
        got = cbm_read(stream->lfn, dst, cap);
#ifdef READYFS_OVERLAY_RUNTIME
        /* KERNAL tape returns the final short chunk but another READ starts a
         * new physical search.  Latch that short read as this file's EOF. */
        if (stream->path.endpoint == RF_EP_TAPE && got >= 0 &&
            (unsigned int)got < cap) stream->open = 2u;
#endif
        return got;
    }
    uci_cmd[0] = stream->target;
    uci_cmd[1] = 0x04u;
    uci_cmd[2] = (unsigned char)(cap & 0xFFu);
    uci_cmd[3] = (unsigned char)(cap >> 8u);
    if (!uci_call_raw(uci_cmd, 4u) ||
        !uci_target_ok_or_quiet(stream->target)) return -1;
    if (uci_xfer.data_len != 0u) memcpy(dst, uci_data, uci_xfer.data_len);
    got = (int)uci_xfer.data_len;
    return got;
}

static unsigned char stream_write(ReadyFsStream *stream,
                                  const void *src, unsigned int len) {
    int wrote;

    if (stream->path.endpoint != RF_EP_ULTIMATE) {
        /* ST is shared by cassette and serial I/O.  A completed tape read
         * leaves EOF ($40), which must not become the following IEC write's
         * result.  Clear it at the actual CHKOUT/write boundary. */
        RF_KERNAL_STATUS = 0u;
        wrote = cbm_write(stream->lfn, src, len);
        return (unsigned char)(wrote == (int)len);
    }
    uci_cmd[0] = stream->target;
    uci_cmd[1] = 0x05u;
    uci_cmd[2] = 0u;
    uci_cmd[3] = 0u;
    memcpy(uci_cmd + 4u, src, len);
    return (unsigned char)(uci_call_raw(uci_cmd, len + 4u) &&
                           uci_target_ok_or_quiet(stream->target));
}

#ifdef READYFS_OVERLAY_RUNTIME
#define RF_CLOSE_CHECK(stream, ok) do { if (!stream_close(stream)) ok = 0u; } while (0)
static unsigned char stream_close(ReadyFsStream *stream) {
    if (!stream->open) return 1u;
    if (stream->path.endpoint == RF_EP_IEC)
        return RF_FOUND(native_file(stream, 0, RF_FILES_CLOSE));
#else
#define RF_CLOSE_CHECK(stream, ok) stream_close(stream)
static void stream_close(ReadyFsStream *stream) {
    if (!stream->open) return;
#endif
    if (stream->path.endpoint != RF_EP_ULTIMATE) {
        cbm_close(stream->lfn);
        cbm_k_clrch();
#ifdef READYFS_OVERLAY_RUNTIME
        if (stream->path.endpoint == RF_EP_TAPE) {
            RF_KERNAL_STATUS = 0u;
        }
#endif
    } else {
#ifdef READYFS_OVERLAY_RUNTIME
        return RF_FOUND(udos_file(stream, stream->target, RF_UDOS_CLOSE));
#else
        (void)uci_call(stream->target, 0x03u, 0);
#endif
    }
    stream->open = 0u;
#ifdef READYFS_OVERLAY_RUNTIME
    return 1u;
#endif
}

static unsigned char delete_stream(ReadyFsStream *stream) {
    const char *leaf;

    if (stream->path.endpoint == RF_EP_TAPE) return 0u;
    if (stream_uses_iec(stream)) {
#ifdef READYFS_OVERLAY_RUNTIME
        /* path_prepare leaves a SoftwareIEC partition/path reference here.
         * SCRATCH accepts a logical leaf in the current parent, not a path.
         * COPY has already closed both data channels before MOVE gets here. */
        if (stream->path.endpoint == RF_EP_SOFTIEC &&
            !softiec_enter_parent(stream)) return 0u;
#endif
#ifdef READYFS_OVERLAY_RUNTIME
        if (!RF_FOUND(native_file(stream, 0, RF_FILES_SCRATCH))) return 0u;
#else
        if (strlen(stream->native_name) + 3u > RF_LINE_CAP) return 0u;
        strcpy(temp_text, "s:");
        strcat(temp_text, stream->native_name);
        if (cbm_open(15u, stream->device, 15u, temp_text) != 0u) return 0u;
        cbm_close(15u);
        cbm_k_clrch();
#endif
        return (unsigned char)RF_MISSING(stream_find_type(stream));
    }
#ifdef READYFS_OVERLAY_RUNTIME
    /* An uncertain CLOSE must keep the stage intact. Do not delete through
     * target1 while target2 may still own that output file. */
    if (udos_open_targets) { last_result = RF_RESULT_IO; return 0u; }
#endif
    leaf = udos_find_leaf(stream, 1u);
    if (leaf == 0) return 0u;
    return (unsigned char)(uci_call(1u, 0x09u, leaf) &&
                           uci_status_ok(1u));
}

static unsigned char ask_yes(const char *prompt) {
    unsigned char ch;
#ifdef READYFS_OVERLAY_RUNTIME
    if (batch_active) {
        batch_prompt_denied = 1u;
        cputs(RF_ERROR "batch needs --yes\r\n");
        return 0u;
    }
#endif
    cputs(prompt);
    cputs(" [y/N] ");
    ch = cgetc();
    cputc(ch);
    newline();
    if (ch == 'y' || ch == 'Y') return 1u;
    last_result = RF_RESULT_INTERACTION;
    return 0u;
}

static unsigned char rename_stream(ReadyFsStream *source,
                                   ReadyFsStream *dest) {
    const char *source_leaf;
#ifndef READYFS_OVERLAY_RUNTIME
    const char *dest_leaf;
    const char *source_slash;
    const char *dest_slash;
    unsigned int len;
    unsigned int source_parent_len;
    unsigned int dest_parent_len;
#endif

    if (source->path.endpoint == RF_EP_TAPE ||
        dest->path.endpoint == RF_EP_TAPE ||
        source->path.endpoint != dest->path.endpoint ||
        source->path.unit != dest->path.unit) return 0u;
    /* SoftwareIEC 3.14 has ordinary file OPEN plus CD:, but no R: command.
     * make_temp_stream uses the final path directly only after proving that
     * it is absent, so that one safe case needs no commit rename. */
    if (source->path.endpoint == RF_EP_SOFTIEC &&
        strcmp(source->canonical, dest->canonical) == 0) return 1u;
    if (stream_uses_iec(source)) {
        /* Resolve the existing source to the exact raw PETSCII directory
         * spelling before issuing R:. New destination spelling stays as the
         * user supplied it; both physical DOS and VICE accept that form. */
        if (!RF_FOUND(stream_find_type(source))) return 0u;
#ifdef READYFS_OVERLAY_RUNTIME
        if (!RF_FOUND(native_file(source, dest, RF_FILES_RENAME))) return 0u;
#else
        if (strlen(dest->native_name) + strlen(source->native_name) + 4u >
            RF_LINE_CAP) return 0u;
        strcpy(temp_text, "r:");
        strcat(temp_text, dest->native_name);
        strcat(temp_text, "=");
        strcat(temp_text, source->native_name);
        if (cbm_open(15u, source->device, 15u, temp_text) != 0u) return 0u;
        cbm_close(15u);
        cbm_k_clrch();
#endif
        return RF_FOUND(stream_find_type(dest));
    }
#ifdef READYFS_OVERLAY_RUNTIME
    source_leaf = udos_find_leaf(source, 1u);
    if (!source_leaf) return 0u;
    udos_setup(source, 1u, RF_UDOS_RENAME);
    udos_call.other = dest;
    udos_call.source_access = source_leaf;
    return RF_FOUND(readyfs_overlay_udos(&udos_call));
#else
    source_slash = strrchr(source->native_name, '/');
    dest_slash = strrchr(dest->native_name, '/');
    if (source_slash == 0 || dest_slash == 0) return 0u;
    source_parent_len = (unsigned int)(source_slash - source->native_name);
    dest_parent_len = (unsigned int)(dest_slash - dest->native_name);
    if (source_parent_len != dest_parent_len ||
        memcmp(source->native_name, dest->native_name,
               source_parent_len) != 0) return 0u;
    source_leaf = udos_find_leaf(source, 1u);
    if (source_leaf == 0) return 0u;
    dest_leaf = dest_slash + 1u;
    uci_cmd[0] = 1u;
    uci_cmd[1] = 0x0Au;
    len = 2u;
    strcpy((char *)uci_cmd + len, source_leaf);
    len += (unsigned int)(strlen(source_leaf) + 1u);
    strcpy((char *)uci_cmd + len, dest_leaf);
    len += strlen(dest_leaf);
    return (unsigned char)(uci_call_raw(uci_cmd, len) && uci_status_ok(1u));
#endif
}

static unsigned char make_temp_stream(ReadyFsStream *dest,
                                      ReadyFsStream *temp,
                                      char *temp_text) {
    static unsigned char serial;
#ifndef READYFS_OVERLAY_RUNTIME
    char *suffix;
    char *last;
#endif
    unsigned char tries;
#ifdef READYFS_OVERLAY_RUNTIME
    unsigned char lookup;
#endif

    /* SoftwareIEC 3.14 cannot rename. For a destination still proven absent,
     * direct creation followed by the caller's verification is the only
     * usable commit path. Never use this fallback for replacement. */
    if (dest->path.endpoint == RF_EP_SOFTIEC && dest->type == 0u)
        return path_prepare(dest->canonical, temp);

    for (tries = 0u; tries < 16u; ++tries) {
        ++serial;
#ifdef READYFS_OVERLAY_RUNTIME
        utility_ui.operation = RF_PRESENT_STAGE_NAME;
        utility_ui.buffer = (char *)dest->text;
        utility_ui.workspace = temp_text;
        utility_ui.value_low = serial;
        if (!readyfs_overlay_present(&utility_ui)) return 0u;
#else
        suffix = (char *)io_buf;
        suffix[0] = 'r';
        suffix[1] = 'f';
        suffix[2] = '~';
        suffix[3] = "0123456789abcdef"[serial >> 4u];
        suffix[4] = "0123456789abcdef"[serial & 15u];
        suffix[5] = 0;
        if (dest->path.endpoint == RF_EP_IEC) {
            strcpy(format_u16(temp_text, dest->path.unit), ":/");
            strcat(temp_text, suffix);
        } else {
            strcpy(temp_text, dest->text);
            last = strrchr(temp_text, '/');
            if (last == 0 || (unsigned int)(last - temp_text) + strlen(suffix) + 2u > RF_LINE_CAP) {
                return 0u;
            }
            strcpy(last + 1u, suffix);
        }
#endif
        if (!path_prepare(temp_text, temp)) return 0u;
#ifdef READYFS_OVERLAY_RUNTIME
        temp->native_mode = dest->native_mode;
        temp->native_partition = dest->native_partition;
        lookup = stream_exists(temp);
        if (RF_LOOKUP_FAILED(lookup)) return 0u;
        if (RF_MISSING(lookup)) return 1u;
#else
        if (!stream_exists(temp)) return 1u;
#endif
    }
    cputs(RF_ERROR "no stage name\r\n");
    return 0u;
}
#ifdef READYFS_OVERLAY_RUNTIME
static unsigned char udos_distinct(ReadyFsStream *left, ReadyFsStream *right) {
    if (left->path.endpoint != RF_EP_ULTIMATE ||
        right->path.endpoint != RF_EP_ULTIMATE) return 1u;
    udos_setup(left, 1u, RF_UDOS_DISTINCT);
    udos_call.other = right;
    return RF_FOUND(readyfs_overlay_udos(&udos_call));
}
static unsigned char udos_validate(ReadyFsStream *stream, unsigned char type) {
    if (stream->path.endpoint != RF_EP_ULTIMATE) return 1u;
    udos_setup(stream, 1u, RF_UDOS_VALIDATE);
    udos_call.type = type;
    return RF_FOUND(readyfs_overlay_udos(&udos_call));
}
static unsigned char typed_temp_stream(ReadyFsStream *dest,
                                       ReadyFsStream *temp,
                                       unsigned char type) {
    return udos_validate(dest, type) && make_temp_stream(dest, temp, temp_text);
}
#else
#define typed_temp_stream(dest,temp,type) make_temp_stream(dest,temp,temp_text)
#endif


static unsigned char verify_text_file(ReadyFsStream *file, const char *text,
                                      unsigned char add_line) {
    unsigned int expected_len;
    unsigned int offset;
    unsigned int want;
    int got;
    unsigned char ok;

    if (!stream_open_read(file, 1u, 2u)) return 0u;
    expected_len = strlen(text);
    offset = 0u;
    ok = 1u;
    while (offset < expected_len) {
        want = (unsigned int)(expected_len - offset);
        if (want > sizeof(io_buf)) want = sizeof(io_buf);
        got = stream_read(file, io_buf, want);
#ifdef READYFS_SOFT_TRACE
        if (file->path.endpoint == RF_EP_SOFTIEC) {
            cputs("VB "); cputhex8((unsigned char)got); cputc('/');
            cputhex8((unsigned char)want); newline();
        }
#endif
        if (got != (int)want ||
            memcmp(io_buf, text + offset, want) != 0) {
            ok = 0u;
            break;
        }
        offset = (unsigned int)(offset + want);
    }
    if (ok && add_line) {
        got = stream_read(file, io_buf, 1u);
#ifdef READYFS_SOFT_TRACE
        if (file->path.endpoint == RF_EP_SOFTIEC) {
            cputs("VC "); cputhex8((unsigned char)got); cputc('/');
            cputhex8(io_buf[0]); newline();
        }
#endif
        if (got != 1 || io_buf[0] != '\r') ok = 0u;
    }
    if (ok) {
        got = stream_read(file, io_buf, 1u);
#ifdef READYFS_SOFT_TRACE
        if (file->path.endpoint == RF_EP_SOFTIEC) {
            cputs("VE "); cputhex8((unsigned char)got); newline();
        }
#endif
        if (got != 0) ok = 0u;
    }
    RF_CLOSE_CHECK(file, ok);
    cputs(ok ? RF_SUMMARY "verify: identical\r\n" : RF_ERROR "verify: mismatch\r\n");
    return ok;
}

static void signature_init(ReadyFsSignature *sig) {
#ifdef READYFS_OVERLAY_RUNTIME
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_SIGNATURE_INIT;
    tape_call.signature = sig;
    (void)readyfs_overlay_tape(&tape_call);
#else
    sig->bytes_lo = 0u;
    sig->bytes_hi = 0u;
    sig->crc = 0xFFFFu;
#endif
}

static void signature_add(ReadyFsSignature *sig,
                          const unsigned char *data,
                          unsigned int len) {
#ifdef READYFS_OVERLAY_RUNTIME
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_SIGNATURE_ADD;
    tape_call.signature = sig;
    tape_call.data = data;
    tape_call.length = len;
    (void)readyfs_overlay_tape(&tape_call);
#else
    unsigned int before;
    unsigned int crc;
    unsigned int i;
    unsigned char bit;

    before = sig->bytes_lo;
    sig->bytes_lo = (unsigned int)(sig->bytes_lo + len);
    if (sig->bytes_lo < before) ++sig->bytes_hi;
    crc = sig->crc;
    for (i = 0u; i < len; ++i) {
        crc ^= (unsigned int)data[i] << 8u;
        for (bit = 0u; bit < 8u; ++bit) {
            if (crc & 0x8000u) crc = (unsigned int)((crc << 1u) ^ 0x1021u);
            else crc <<= 1u;
        }
    }
    sig->crc = crc;
#endif
}

static unsigned char signature_file(ReadyFsStream *file,
                                    ReadyFsSignature *sig) {
    int got;
    unsigned char ok;

    signature_init(sig);
    if (!stream_open_read(file, 1u, 2u)) return 0u;
    ok = 1u;
    for (;;) {
        got = stream_read(file, io_buf, sizeof(io_buf));
        if (got < 0) {
            ok = 0u; break;
        }
        if (got == 0) break;
        signature_add(sig, io_buf, (unsigned int)got);
    }
    RF_CLOSE_CHECK(file, ok);
    return ok;
}

static unsigned char signatures_equal(const ReadyFsSignature *left,
                                      const ReadyFsSignature *right) {
#ifdef READYFS_OVERLAY_RUNTIME
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_SIGNATURE_EQUAL;
    tape_call.signature = (ReadyFsSignature *)left;
    tape_call.other = right;
    if (!readyfs_overlay_tape(&tape_call)) return 0u;
    return tape_call.result;
#else
    return (unsigned char)(left->bytes_lo == right->bytes_lo &&
                           left->bytes_hi == right->bytes_hi &&
                           left->crc == right->crc);
#endif
}

#ifdef READYFS_OVERLAY_RUNTIME
static int tape_spool(unsigned char operation, ReadyFsTapeSpoolState *state,
                      unsigned char *data, unsigned int length) {
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = operation;
    tape_call.spool = state;
    tape_call.data = data;
    tape_call.length = length;
    if (!readyfs_overlay_tape(&tape_call) || !tape_call.result) return -1;
    return operation == RF_TAPE_SPOOL_FETCH ? (int)tape_call.length : 1;
}
#endif

static unsigned char compare_prepared(void) {
    unsigned char equal;

    /* Read the streams independently: IEC, UCI, and host-backed endpoints
     * are allowed to return different chunk lengths for identical content. */
    equal = (unsigned char)(signature_file(&source, &left_signature) &&
                            signature_file(&dest, &right_signature) &&
                            signatures_equal(&left_signature,
                                             &right_signature));
    cputs(equal ? RF_SUMMARY "verify: identical\r\n" : RF_ERROR "verify: mismatch\r\n");
    return equal;
}

static unsigned char stream_write_all(ReadyFsStream *stream,
                                      const unsigned char *data,
                                      unsigned int len) {
    unsigned int chunk;

    while (len != 0u) {
        chunk = len > RF_IO_CHUNK ? RF_IO_CHUNK : len;
        if (!stream_write(stream, data, chunk)) return 0u;
        data += chunk;
        len = (unsigned int)(len - chunk);
    }
    return 1u;
}

static unsigned char stream_read_exact(ReadyFsStream *stream,
                                       unsigned char *data,
                                       unsigned int len) {
    unsigned int chunk;
    int got;

    while (len != 0u) {
        chunk = len > RF_IO_CHUNK ? RF_IO_CHUNK : len;
        got = stream_read(stream, data, chunk);
        if (got != (int)chunk) return 0u;
        data += chunk;
        len = (unsigned int)(len - chunk);
    }
    return 1u;
}

#ifndef READYFS_OVERLAY_RUNTIME
static unsigned char config_alias_valid(const ReadyFsAlias *item) {
    ReadyFsPath path;
    unsigned int i;
    unsigned int len;

    if (item->name[0] == 0) return 1u;
    len = strlen(item->name);
    if (len > RF_ALIAS_NAME) return 0u;
    for (i = 0u; i < len; ++i) {
        if (item->name[i] == ':' || item->name[i] == '/' ||
            item->name[i] == '@') return 0u;
    }
    if (readyfs_path_parse(item->root, &path) != RF_PATH_OK ||
        !path.absolute || path.endpoint == RF_EP_ALIAS) return 0u;
    return 1u;
}

#endif

#ifdef READYFS_OVERLAY_RUNTIME
#pragma static-locals (push, on)
#endif
static void cmd_config_save(unsigned char argc, const char *path_text) {
#ifndef READYFS_OVERLAY_RUNTIME
    static const unsigned char header[8] = {
        'R', 'F', 'C', '1', RF_ALIAS_SLOTS, RF_ALIAS_NAME,
        (unsigned char)(RF_LINE_CAP & 0xFFu), (unsigned char)(RF_LINE_CAP >> 8u)
    };
#endif
    ReadyFsSignature expected;
    ReadyFsSignature actual;
    unsigned char existed;
    unsigned char ok;
    unsigned char i;
#ifdef READYFS_OVERLAY_RUNTIME
    unsigned int record_bytes;
#endif

    if (has_dry_run(argc)) { cmd_mutation_preview(argc); return; }
    if (!path_prepare(path_text, &dest)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (dest.path.endpoint == RF_EP_TAPE) {
        result_unsupported("tape cfg off\r\n"); return;
    }
#endif
    existed = stream_exists(&dest);
#ifdef READYFS_OVERLAY_RUNTIME
    if (RF_LOOKUP_FAILED(existed)) return;
#endif
    if (existed && !option_present(argc, "--force") &&
        !ask_yes("config exists; replace")) return;
    if (!typed_temp_stream(&dest, &temp, CBM_T_SEQ)) return;
    if (!stream_open_write(&temp, 2u, 3u, CBM_T_SEQ)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    last_result = RF_RESULT_IO;
#endif
    signature_init(&expected);
#ifdef READYFS_OVERLAY_RUNTIME
    ok = 1u;
    for (i = 0u; ok && i < 26u; ++i) {
        batch_ui.operation = RF_CONFIG_EXPORT; batch_ui.size = i;
        batch_ui.buffer = (char *)&alias_slot; batch_ui.test = cwd_buf;
        ok = readyfs_overlay_script(&batch_ui);
        if (ok) {
            record_bytes = batch_ui.size;
            signature_add(&expected, (const unsigned char *)&alias_slot, record_bytes);
            ok = stream_write_all(&temp, (const unsigned char *)&alias_slot, record_bytes);
        }
    }
#else
    signature_add(&expected, header, sizeof(header));
    signature_add(&expected, (const unsigned char *)cwd_buf, sizeof(cwd_buf));
    ok = stream_write_all(&temp, header, sizeof(header));
    if (ok) ok = stream_write_all(&temp, (const unsigned char *)cwd_buf,
                                  sizeof(cwd_buf));
    for (i = 0u; ok && i < RF_ALIAS_SLOTS; ++i) {
        if (!alias_fetch(i)) ok = 0u;
        else {
            signature_add(&expected, (const unsigned char *)&alias_slot,
                          RF_ALIAS_SLOT_BYTES);
            ok = stream_write_all(&temp, (const unsigned char *)&alias_slot,
                                  RF_ALIAS_SLOT_BYTES);
        }
    }
#endif
    RF_CLOSE_CHECK(&temp, ok);
    if (!ok) {
        (void)delete_stream(&temp);
        cputs(RF_ERROR "cfg write fail\r\n");
        return;
    }
    if (existed) {
        if (!typed_temp_stream(&dest, &backup, dest.type) ||
            !rename_stream(&dest, &backup)) {
            cputs(RF_ERROR "cfg stage kept\r\n");
            return;
        }
    }
    if (!rename_stream(&temp, &dest)) {
        if (existed) (void)rename_stream(&backup, &dest);
        cputs(RF_ERROR "cfg rename fail\r\n");
        return;
    }
    if (!signature_file(&dest, &actual) ||
        !signatures_equal(&expected, &actual)) {
        if (existed && rename_stream(&dest, &temp)) {
            (void)rename_stream(&backup, &dest);
            (void)delete_stream(&temp);
        } else if (!existed) {
#ifdef READYFS_SOFT_TRACE
            /* Hardware diagnostics are preserve-only inside the exact owned
             * root. Keep a newly created mismatch for forensic readback. */
            cputs(RF_ERROR "failed file kept\r\n");
#else
            (void)delete_stream(&dest);
#endif
        }
        cputs(RF_ERROR "cfg rollback\r\n");
        return;
    }
    if (existed && !delete_stream(&backup)) {
        cputs("old cfg: "); cputs(backup.text); newline();
    }
#ifdef READYFS_OVERLAY_RUNTIME
    last_result = RF_RESULT_OK;
#endif
    cputs(RF_SUMMARY "config saved and verified\r\n");
}

#ifdef READYFS_OVERLAY_RUNTIME
unsigned char readyfs_config_io(ReadyFsBatchCall *call) {
    unsigned char ok;
    if (call->operation == RF_CONFIG_READ)
        ok = stream_read_exact(&command_stream, (unsigned char *)call->buffer, call->size);
    else if (call->operation == RF_CONFIG_EOF)
        ok = stream_read(&command_stream, io_buf, 1u) == 0;
    else if (call->operation == RF_CONFIG_CLOSE) {
        stream_close(&command_stream); ok = 1u;
    } else ok = readyfs_overlay_script(call);
    return readyfs_overlay_resume_config() && ok;
}
static void cmd_config_load(const char *path_text) {
    if (!path_prepare(path_text, &command_stream) || !stream_open_read(&command_stream, 1u, 2u)) return;
    batch_ui.operation = RF_CONFIG_LOAD;
    batch_ui.buffer = (char *)&alias_slot; batch_ui.test = cwd_buf;
    last_result = readyfs_overlay_script(&batch_ui) ? batch_ui.rc : RF_RESULT_IO;
    cputs(last_result ? RF_ERROR "bad cfg; unchanged\r\n" : RF_SUMMARY "config loaded\r\n");
}
#else
static void cmd_config_load(const char *path_text) {
    unsigned char header[8];
    ReadyFsPath parsed;
    unsigned char i;
    unsigned char ok;
    int trailing;

    if (!path_prepare(path_text, &command_stream)) return;
    if (!stream_open_read(&command_stream, 1u, 2u)) return;
    if (!reu_available || !readyfs_reu_session_store(RF_REU_CONFIG_BACKUP_OFF,
                                                      cwd_buf,
                                                      sizeof(cwd_buf))) {
        stream_close(&command_stream);
        cputs(RF_ERROR "cfg needs reu\r\n");
        return;
    }
    ok = 1u;
    for (i = 0u; i < RF_ALIAS_SLOTS; ++i) {
        if (!alias_fetch(i) ||
            !readyfs_reu_session_store(
                (unsigned int)(RF_REU_CONFIG_BACKUP_OFF + sizeof(cwd_buf) +
                               alias_reu_offset(i)),
                &alias_slot, RF_ALIAS_SLOT_BYTES)) {
            ok = 0u;
            break;
        }
    }
    if (!ok) {
        stream_close(&command_stream);
        cputs(RF_ERROR "cfg needs reu\r\n");
        return;
    }
    if (!stream_read_exact(&command_stream, header, sizeof(header)) ||
        !stream_read_exact(&command_stream, (unsigned char *)temp_text,
                           sizeof(cwd_buf))) {
        stream_close(&command_stream);
        cputs(RF_ERROR "cfg truncated\r\n");
        return;
    }
    temp_text[RF_LINE_CAP] = 0;
    if (readyfs_path_parse(temp_text, &parsed) != RF_PATH_OK ||
        !parsed.absolute || parsed.endpoint == RF_EP_ALIAS ||
        !readyfs_reu_session_store(RF_REU_CONFIG_STAGE_OFF, temp_text,
                                   sizeof(cwd_buf))) {
        stream_close(&command_stream);
        cputs(RF_ERROR "bad cfg cwd\r\n");
        return;
    }
    for (i = 0u; i < RF_ALIAS_SLOTS; ++i) {
        if (!stream_read_exact(&command_stream, (unsigned char *)&alias_slot,
                               RF_ALIAS_SLOT_BYTES)) {
            stream_close(&command_stream);
            cputs(RF_ERROR "cfg truncated\r\n");
            return;
        }
        alias_slot.name[RF_ALIAS_NAME] = 0;
        alias_slot.root[RF_LINE_CAP] = 0;
        if (!config_alias_valid(&alias_slot) ||
            !readyfs_reu_session_store(
                (unsigned int)(RF_REU_CONFIG_STAGE_OFF + sizeof(cwd_buf) +
                               alias_reu_offset(i)),
                &alias_slot, RF_ALIAS_SLOT_BYTES)) {
            stream_close(&command_stream);
            cputs(RF_ERROR "bad cfg alias\r\n");
            return;
        }
    }
    trailing = stream_read(&command_stream, io_buf, 1u);
    stream_close(&command_stream);
    if (trailing != 0 || memcmp(header, "RFC1", 4u) != 0 ||
        header[4] != RF_ALIAS_SLOTS || header[5] != RF_ALIAS_NAME ||
        header[6] != (unsigned char)(RF_LINE_CAP & 0xFFu) ||
        header[7] != (unsigned char)(RF_LINE_CAP >> 8u)) {
        cputs(RF_ERROR "bad cfg format\r\n");
        return;
    }
    ok = readyfs_reu_session_fetch(RF_REU_CONFIG_STAGE_OFF, cwd_buf,
                                   sizeof(cwd_buf));
    for (i = 0u; i < RF_ALIAS_SLOTS; ++i) {
        if (!ok || !readyfs_reu_session_fetch(
                (unsigned int)(RF_REU_CONFIG_STAGE_OFF + sizeof(cwd_buf) +
                               alias_reu_offset(i)),
                &alias_slot, RF_ALIAS_SLOT_BYTES) || !alias_store(i)) ok = 0u;
    }
    if (!ok) {
        (void)readyfs_reu_session_fetch(RF_REU_CONFIG_BACKUP_OFF, cwd_buf,
                                        sizeof(cwd_buf));
        for (i = 0u; i < RF_ALIAS_SLOTS; ++i) {
            if (readyfs_reu_session_fetch(
                    (unsigned int)(RF_REU_CONFIG_BACKUP_OFF + sizeof(cwd_buf) +
                                   alias_reu_offset(i)),
                    &alias_slot, RF_ALIAS_SLOT_BYTES)) (void)alias_store(i);
        }
        cputs(RF_ERROR "cfg rollback\r\n");
        return;
    }
    cputs(RF_SUMMARY "config loaded\r\n");
}

#endif

#ifdef READYFS_OVERLAY_RUNTIME
#pragma static-locals (pop)
#endif
static void cmd_config(unsigned char argc) {
    const char *path_text;

    if (argc < 2u) {
        cputs("config save|load [P]\r\n");
        cputs("cfg 8:/readyfs.cfg\r\n");
        return;
    }
    path_text = (argc >= 3u && args[2][0] != '-') ? args[2] :
                                                        "8:/readyfs.cfg";
    if (same_word(args[1], "save")) cmd_config_save(argc, path_text);
    else if (same_word(args[1], "load")) cmd_config_load(path_text);
    else cputs("config save|load [P]\r\n");
}

static void cmd_new(unsigned char argc) {
    unsigned char type;

    if (argc < 2u) {
        last_result = RF_RESULT_USAGE;
        cputs("new P [T]\r\n"); return;
    }
    if (has_dry_run(argc)) { cmd_mutation_preview(argc); return; }
    type = option_file_type(argc);
    if (type == 0xFFu) {
        cputs(RF_ERROR "bad file type\r\n"); return;
    }
    if (!path_prepare(args[1], &command_stream)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (command_stream.path.endpoint == RF_EP_TAPE) {
        if (type != CBM_T_SEQ) {
            result_unsupported("tape seq only\r\n"); return;
        }
        if (!stream_open_write(&command_stream, 1u, 2u, type)) return;
        stream_close(&command_stream);
        cputs(RF_SUMMARY "tape created\r\n");
        return;
    }
#endif
    if (stream_exists(&command_stream)) {
#ifdef READYFS_OVERLAY_RUNTIME
        if (last_result != RF_RESULT_IO)
#endif
        last_result = RF_RESULT_CONFLICT;
        cputs("destination exists\r\n"); return;
    }
    if (!stream_open_write(&command_stream, 1u, 2u, type)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (!stream_close(&command_stream)) return;
#else
    stream_close(&command_stream);
#endif
    if (RF_FOUND(stream_exists(&command_stream))) cputs(RF_SUMMARY "created\r\n");
    else {
        cputs(RF_ERROR "verify fail\r\n");
    }
}

static void cmd_write(unsigned char argc) {
    unsigned char type;
    unsigned char existed;
    unsigned char add_line;
    unsigned char ok;

    if (argc < 3u) {
        cputs("write P TEXT\r\n"); return;
    }
    if (has_dry_run(argc)) { cmd_mutation_preview(argc); return; }
    type = option_file_type(argc);
    if (type == 0xFFu) {
        cputs(RF_ERROR "bad file type\r\n"); return;
    }
    if (!path_prepare(args[1], &dest)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (dest.path.endpoint == RF_EP_TAPE) {
        if (type != CBM_T_SEQ) {
            result_unsupported("tape seq only\r\n"); return;
        }
        add_line = option_present(argc, "--line");
        if (!stream_open_write(&dest, 2u, 3u, type)) return;
        ok = stream_write(&dest, args[2], strlen(args[2]));
        if (ok && add_line) ok = stream_write(&dest, "\r", 1u);
        stream_close(&dest);
        cputs(ok ? RF_SUMMARY "tape wrote\r\n" : RF_ERROR "tape write fail\r\n");
        return;
    }
#endif
    existed = stream_exists(&dest);
#ifdef READYFS_OVERLAY_RUNTIME
    if (RF_LOOKUP_FAILED(existed)) return;
#endif
    if (existed && !option_present(argc, "--force") &&
        !ask_yes("destination exists; replace")) return;
    add_line = option_present(argc, "--line");
    if (!typed_temp_stream(&dest, &temp, type)) return;
#ifdef READYFS_SOFT_TRACE
    cputc('2');
#endif
    if (!stream_open_write(&temp, 2u, 3u, type)) return;
#ifdef READYFS_SOFT_TRACE
    cputc('3');
#endif
    ok = stream_write(&temp, args[2], strlen(args[2]));
    if (ok && add_line) ok = stream_write(&temp, "\r", 1u);
    RF_CLOSE_CHECK(&temp, ok);
#ifdef READYFS_SOFT_TRACE
    cputc('4');
#endif
    if (!ok) {
        (void)delete_stream(&temp);
        cputs(RF_ERROR "write fail\r\n");
        return;
    }
    if (existed) {
        if (!typed_temp_stream(&dest, &backup, dest.type) ||
            !rename_stream(&dest, &backup)) {
            cputs(RF_ERROR "stage kept\r\n");
            return;
        }
    }
    if (!rename_stream(&temp, &dest)) {
        if (existed) (void)rename_stream(&backup, &dest);
        cputs(RF_ERROR "rename fail\r\n");
        return;
    }
#ifdef READYFS_SOFT_TRACE
    cputc('5'); newline();
#endif
    if (!verify_text_file(&dest, args[2], add_line)) {
        if (existed && rename_stream(&dest, &temp)) {
            (void)rename_stream(&backup, &dest);
            (void)delete_stream(&temp);
        } else if (!existed) {
#ifdef READYFS_SOFT_TRACE
            /* Preserve the exact newly-created owned-root file so a failed
             * hardware diagnostic can be inspected through UltimateDOS. */
            cputs(RF_ERROR "failed file kept\r\n");
#else
            (void)delete_stream(&dest);
#endif
        }
        cputs("rolled back\r\n");
        return;
    }
    if (existed && !delete_stream(&backup)) {
        cputs(RF_ERROR "backup kept: "); cputs(backup.text); newline();
    }
    cputs(RF_SUMMARY "write complete\r\n");
}

static void cmd_append(unsigned char argc) {
    ReadyFsSignature expected;
    ReadyFsSignature actual;
    unsigned char existed;
    unsigned char type;
    unsigned char add_line;
    unsigned char ok;
    int got;

    if (argc < 3u) {
        cputs("append P TEXT\r\n"); return;
    }
    if (has_dry_run(argc)) { cmd_mutation_preview(argc); return; }
    type = option_file_type(argc);
    if (type == 0xFFu) {
        cputs(RF_ERROR "bad file type\r\n"); return;
    }
    if (!path_prepare(args[1], &dest)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (dest.path.endpoint == RF_EP_TAPE) {
        result_unsupported("tape append off\r\n"); return;
    }
#endif
    existed = stream_exists(&dest);
#ifdef READYFS_OVERLAY_RUNTIME
    if (RF_LOOKUP_FAILED(existed)) return;
#endif
    if (existed) type = dest.type;
    if (type == CBM_T_REL) {
        result_unsupported("rel append off\r\n");
        return;
    }
    if (!typed_temp_stream(&dest, &temp, type)) return;
    signature_init(&expected);
    ok = 1u;
    if (existed && !stream_open_read(&dest, 1u, 2u)) return;
    if (!stream_open_write(&temp, 2u, 3u, type)) {
        if (existed) stream_close(&dest);
        return;
    }
    if (existed) {
        for (;;) {
            got = stream_read(&dest, io_buf, sizeof(io_buf));
            if (got < 0) { ok = 0u; break; }
            if (got == 0) break;
            signature_add(&expected, io_buf, (unsigned int)got);
            if (!stream_write(&temp, io_buf, (unsigned int)got)) {
                ok = 0u;
                break;
            }
        }
        RF_CLOSE_CHECK(&dest, ok);
    }
    if (ok) {
        signature_add(&expected, (const unsigned char *)args[2], strlen(args[2]));
        ok = stream_write(&temp, args[2], strlen(args[2]));
    }
    add_line = option_present(argc, "--line");
    if (ok && add_line) {
        signature_add(&expected, (const unsigned char *)"\r", 1u);
        ok = stream_write(&temp, "\r", 1u);
    }
    RF_CLOSE_CHECK(&temp, ok);
    if (!ok) {
        (void)delete_stream(&temp);
        cputs(RF_ERROR "append fail\r\n");
        return;
    }
    if (existed) {
        if (!typed_temp_stream(&dest, &backup, dest.type) ||
            !rename_stream(&dest, &backup)) {
            cputs(RF_ERROR "stage kept\r\n");
            return;
        }
    }
    if (!rename_stream(&temp, &dest)) {
        if (existed) (void)rename_stream(&backup, &dest);
        cputs(RF_ERROR "rename fail\r\n");
        return;
    }
    if (!signature_file(&dest, &actual) ||
        !signatures_equal(&expected, &actual)) {
        if (existed && rename_stream(&dest, &temp)) {
            (void)rename_stream(&backup, &dest);
            (void)delete_stream(&temp);
        } else if (!existed) (void)delete_stream(&dest);
        cputs(RF_ERROR "rollback\r\n");
        return;
    }
    cputs(RF_SUMMARY "verify: identical\r\n");
    if (existed && !delete_stream(&backup)) {
        cputs(RF_ERROR "backup kept: "); cputs(backup.text); newline();
    }
    cputs(RF_SUMMARY "append complete\r\n");
}

#ifdef READYFS_OVERLAY_RUNTIME
static void __fastcall__ copy_message(unsigned char status, unsigned int high, unsigned int low) {
    utility_ui.operation = RF_PRESENT_COPY;
    utility_ui.argc = status;
    utility_ui.value_high = high;
    utility_ui.value_low = low;
    utility_ui.buffer = source.canonical;
    (void)readyfs_overlay_present(&utility_ui);
}
#endif

unsigned char readyfs_io_copy_call(ReadyFsIoCopyCall *call) {
    unsigned int total_lo;
    unsigned int total_hi;
    unsigned int before;
    int got;
    unsigned char ok;
    unsigned char existed;
    unsigned char tape_destination;
    ReadyFsStream *output;
#ifdef READYFS_OVERLAY_RUNTIME
    ReadyFsTapeSpoolState spool_state;
#endif

    copy_source_text = call->source;
    copy_destination_text = call->destination;
    copy_force = call->force;
    if (!path_prepare(copy_source_text, &source) ||
        !path_prepare(copy_destination_text, &dest)) return 0u;
    if (same_word(source.canonical, dest.canonical)) {
        cputs(RF_ERROR "same path\r\n");
        return 0u;
    }
    tape_destination = 0u;
    output = &temp;
#ifdef READYFS_OVERLAY_RUNTIME
    tape_destination = (unsigned char)(dest.path.endpoint == RF_EP_TAPE);
    /* Tape type is known before spooling; image-destination admission must
     * not use a type left in the shared descriptor by an earlier command. */
    if (source.path.endpoint == RF_EP_TAPE) source.type = CBM_T_SEQ;
    if (source.path.endpoint == RF_EP_TAPE && tape_destination) {
        result_unsupported("one tape drive\r\n");
        return 0u;
    }
#endif
    if (call->move && (source.path.endpoint == RF_EP_TAPE ||
                       tape_destination)) {
        result_unsupported("tape move off\r\n");
        return 0u;
    }
    /* Prove the source can be opened, and reject unsupported REL files,
     * before any destination existence/replacement I/O is attempted. */
#ifdef READYFS_OVERLAY_RUNTIME
    if (source.path.endpoint != RF_EP_TAPE)
#endif
    {
        if (!stream_open_read(&source, 1u, 2u)) return 0u;
#ifdef READYFS_OVERLAY_RUNTIME
        if (!stream_close(&source)) return 0u;
#else
        stream_close(&source);
#endif
    }
    existed = 0u;
#ifdef READYFS_OVERLAY_RUNTIME
    output = &dest;
    if (!tape_destination) {
#endif
        existed = stream_exists(&dest);
#ifdef READYFS_OVERLAY_RUNTIME
        if (RF_LOOKUP_FAILED(existed) || !udos_distinct(&source, &dest)) return 0u;
#endif
        if (existed && !copy_force &&
            !ask_yes("destination exists; replace")) return 0u;
        if (!typed_temp_stream(&dest, &temp, source.type)) return 0u;
        output = &temp;
#ifdef READYFS_OVERLAY_RUNTIME
    }
#endif
#ifdef READYFS_OVERLAY_RUNTIME
    copy_message(0u, 0u, 0u);
#endif
    signature_init(&left_signature);
    total_lo = 0u;
    total_hi = 0u;
    ok = 1u;
#ifdef READYFS_OVERLAY_RUNTIME
    if (source.path.endpoint == RF_EP_TAPE) {
        if (tape_spool(RF_TAPE_SPOOL_INIT, &spool_state, io_buf, 0u) < 0 ||
            !stream_open_read(&source, 1u, 2u)) return 0u;
        for (;;) {
            got = stream_read(&source, io_buf, sizeof(io_buf));
            if (got < 0) { ok = 0u; break; }
            if (got == 0) break;
            if (tape_spool(RF_TAPE_SPOOL_STORE, &spool_state, io_buf,
                           (unsigned int)got) < 0) {
                ok = 0u; break;
            }
            signature_add(&left_signature, io_buf, (unsigned int)got);
        }
        RF_CLOSE_CHECK(&source, ok);
        total_lo = spool_state.bytes_lo;
        total_hi = spool_state.bytes_bank;
        if (ok && !stream_open_write(output, 2u, 3u, source.type)) ok = 0u;
        while (ok) {
            got = tape_spool(RF_TAPE_SPOOL_FETCH, &spool_state, io_buf,
                             sizeof(io_buf));
            if (got < 0) {
                ok = 0u; break;
            }
            if (got == 0) break;
            if (!stream_write(output, io_buf, (unsigned int)got)) {
                ok = 0u; break;
            }
        }
    } else
#endif
    {
        if (!stream_open_read(&source, 1u, 2u)) return 0u;
        if (!stream_open_write(output, 2u, 3u, source.type)) {
            stream_close(&source);
            return 0u;
        }
        for (;;) {
            got = stream_read(&source, io_buf, sizeof(io_buf));
            if (got < 0) {
                ok = 0u; break;
            }
            if (got == 0) break;
            signature_add(&left_signature, io_buf, (unsigned int)got);
            if (!stream_write(output, io_buf, (unsigned int)got)) {
                ok = 0u; break;
            }
            before = total_lo;
            total_lo = (unsigned int)(total_lo + (unsigned int)got);
            if (total_lo < before) ++total_hi;
        }
    }
    RF_CLOSE_CHECK(output, ok);
    RF_CLOSE_CHECK(&source, ok);
    if (!ok) {
#ifdef READYFS_OVERLAY_RUNTIME
        if (!tape_destination) (void)delete_stream(&temp);
#else
        (void)delete_stream(&temp);
#endif
#ifdef READYFS_OVERLAY_RUNTIME
        copy_message(2u, total_hi, total_lo);
#else
        cputs(RF_ERROR "copy failed: ");
        print_u32_words(total_hi, total_lo);
        cputs(" bytes\r\n");
#endif
        return 0u;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    if (tape_destination) {
        copy_message(9u, total_hi, total_lo);
        return 1u;
    }
#endif
    if (
#ifdef READYFS_OVERLAY_RUNTIME
        !call->skip_verify &&
#endif
        (!signature_file(&temp, &right_signature) ||
         !signatures_equal(&left_signature, &right_signature))) {
        (void)delete_stream(&temp);
        cputs(RF_ERROR "stage mismatch\r\n");
        return 0u;
    }
    if (existed) {
        if (!typed_temp_stream(&dest, &backup, dest.type) ||
            !rename_stream(&dest, &backup)) {
            cputs(RF_ERROR "stage kept\r\n");
            return 0u;
        }
    }
    if (!rename_stream(&temp, &dest)) {
        if (existed) (void)rename_stream(&backup, &dest);
        cputs(RF_ERROR "copy kept ");
        cputs(temp.canonical);
        cputs(RF_ERROR "; rename fail\r\n");
        return 0u;
    }
#ifndef READYFS_OVERLAY_RUNTIME
    cputs(RF_SUMMARY "verify: identical\r\n");
#endif
    if (existed && !delete_stream(&backup)) {
        cputs("old dest ");
        cputs(backup.text);
        newline();
    }
#ifdef READYFS_OVERLAY_RUNTIME
    copy_message(call->skip_verify ? 5u : 1u, total_hi, total_lo);
#else
    cputs(RF_SUMMARY "copied ");
    print_u32_words(total_hi, total_lo);
    cputs(" bytes\r\n");
#endif
    return 1u;
}

static unsigned char compare_one(const char *left_text, const char *right_text) {
    if (!path_prepare(left_text, &source) ||
        !path_prepare(right_text, &dest)) return 0u;
    return compare_prepared();
}

static unsigned char has_dry_run(unsigned char argc) {
    return (unsigned char)(option_present(argc, "--dry-run") ||
                           option_present(argc, "--whatif"));
}

static unsigned char action_filter_accept(unsigned char argc,
                                          const char *path_text,
                                          unsigned char explain) {
    ReadyFsPath path;
    const char *include;
    const char *exclude;
    const char *stem;
    unsigned char rc;

    include = option_value(argc, "--include");
    exclude = option_value(argc, "--exclude");
    if (include == 0 && exclude == 0) return 1u;
    if (!overlay_available) {
        if (explain)
            result_unavailable("match unavailable\r\n");
        return 0u;
    }
    rc = resolve_path(path_text, temp_text);
    if (rc == RF_PATH_OK) rc = readyfs_path_parse(temp_text, &path);
    if (rc != RF_PATH_OK) {
        if (explain) { cputc(0x1Cu); cputs(readyfs_path_error(rc)); newline(); }
        return 0u;
    }
    stem = temp_text + path.path_offset;
    while (*stem == '/') ++stem;
    if ((include != 0 && !readyfs_overlay_match(include, stem)) ||
        (exclude != 0 && readyfs_overlay_match(exclude, stem))) {
        if (explain) { cputs("skip filtered "); cputs(stem); newline(); }
        return 0u;
    }
    return 1u;
}

#ifndef READYFS_OVERLAY_RUNTIME
static unsigned char relative_filter_accept(unsigned char argc,
                                            const char *stem) {
    const char *include;
    const char *exclude;

    include = option_value(argc, "--include");
    exclude = option_value(argc, "--exclude");
    if (include == 0 && exclude == 0) return 1u;
    if (!overlay_available) return 0u;
    if (include != 0 && !readyfs_overlay_match(include, stem)) return 0u;
    if (exclude != 0 && readyfs_overlay_match(exclude, stem)) return 0u;
    return 1u;
}

static ReadyFsPlan recursive_plan;
static ReadyFsPlanCall recursive_call;
static struct cbm_dirent recursive_entry;
static unsigned char recursive_argc;
static unsigned char recursive_failed;
static const char recursive_plan_failed[] = "recursive plan failed\r\n";

static unsigned char recursive_add_record(unsigned char kind,
                                          const char *stem) {
    recursive_call.operation = RF_PLAN_CALL_ADD;
    recursive_call.kind = kind;
    recursive_call.flags = relative_filter_accept(recursive_argc, stem) ?
                           RF_PLAN_SELECTED : 0u;
    recursive_call.stem = stem;
    if (!readyfs_overlay_plan_call(&recursive_call)) {
        recursive_failed = 1u;
        return 0u;
    }
    return 1u;
}

static void recursive_ultimate_block(const unsigned char *data,
                                     unsigned int data_len,
                                     const unsigned char *stat,
                                     unsigned int stat_len) {
    unsigned int parent_len;
    unsigned int name_len;
    unsigned char kind;

    (void)stat;
    (void)stat_len;
    if (recursive_failed || data_len < 2u ||
        recursive_plan.count >= RF_DIR_LIMIT) {
        if (recursive_plan.count >= RF_DIR_LIMIT) recursive_failed = 1u;
        return;
    }
    parent_len = strlen(alias_slot.root);
    name_len = (unsigned int)(data_len - 1u);
    if (name_len == 0u || name_len > RF_LINE_CAP ||
        parent_len + name_len + (parent_len == 0u ? 1u : 2u) >
            sizeof(temp_text)) {
        recursive_failed = 1u;
        return;
    }
    memcpy(temp_text, alias_slot.root, parent_len);
    if (parent_len != 0u) temp_text[parent_len++] = '/';
    memcpy(temp_text + parent_len, data + 1u, name_len);
    temp_text[parent_len + name_len] = 0;
    if (strchr(temp_text + parent_len, '/') != 0 ||
        strchr(temp_text + parent_len, '!') != 0 ||
        strcmp(temp_text + parent_len, ".") == 0 ||
        strcmp(temp_text + parent_len, "..") == 0) {
        recursive_failed = 1u;
        return;
    }
    kind = (data[0] & 0x10u) ? RF_PLAN_KIND_DIR : RF_PLAN_KIND_FILE;
    (void)recursive_add_record(kind, temp_text);
}

static unsigned char recursive_ultimate_enumerate(const char *root) {
    ReadyFsPlanRecord record;
    ReadyFsPath path;
    unsigned int cursor;
    unsigned int resume;
    unsigned char depth;
    const char *native;

    /* Root is traversal-only, never an action. */
    recursive_call.operation = RF_PLAN_CALL_ADD;
    recursive_call.kind = RF_PLAN_KIND_DIR;
    recursive_call.flags = 0u;
    recursive_call.stem = "";
    if (!readyfs_overlay_plan_call(&recursive_call)) return 0u;
    cursor = 0u;
    while (cursor < recursive_plan.used) {
        recursive_call.operation = RF_PLAN_CALL_READ;
        recursive_call.offset = cursor;
        recursive_call.record = &record;
        recursive_call.output = alias_slot.root;
        recursive_call.output_capacity = sizeof(alias_slot.root);
        if (!readyfs_overlay_plan_call(&recursive_call)) return 0u;
        resume = recursive_call.next == RF_PLAN_END ? recursive_plan.used :
                                                     recursive_call.next;
        if (record.kind == RF_PLAN_KIND_DIR) {
            depth = 0u;
            native = alias_slot.root;
            while (*native != 0) if (*native++ == '/') ++depth;
            if (depth >= 32u) { recursive_failed = 1u; return 0u; }
            if (strlen(root) + strlen(alias_slot.root) + 2u >
                sizeof(temp_text)) return 0u;
            strcpy(temp_text, root);
            if (alias_slot.root[0] != 0) {
                if (temp_text[strlen(temp_text) - 1u] != '/') strcat(temp_text, "/");
                strcat(temp_text, alias_slot.root);
            }
            if (readyfs_path_parse(temp_text, &path) != RF_PATH_OK) return 0u;
            native = temp_text + path.path_offset;
            if (!dir_ultimate_run(native, recursive_ultimate_block) ||
                recursive_failed) return 0u;
        }
        cursor = resume;
    }
    return 1u;
}

/* First real backend enumeration slice: a legacy IEC root is a bounded,
 * depth-zero tree. The same serialized plan will later receive nested entries
 * from CMD/SD2IEC, UltimateDOS, and SoftwareIEC directory adapters. */
static unsigned char recursive_preview(unsigned char argc,
                                       unsigned char action) {
    ReadyFsPath path;
    unsigned char rc;
    unsigned int entries;
    unsigned int selected;
    unsigned char kind;
    unsigned char source_unit;
    unsigned char source_endpoint;
    unsigned int display_directories;

    if (!option_present(argc, "--recursive")) return 0u;
    if (!has_dry_run(argc)) {
        cputs("dry-run\r\n");
        return 1u;
    }
    if (!reu_available || !readyfs_overlay_plan_available()) {
        result_unavailable("planner off\r\n");
        return 1u;
    }
    rc = resolve_path(args[1], temp_text);
    if (rc == RF_PATH_OK) rc = readyfs_path_parse(temp_text, &path);
    if (rc != RF_PATH_OK) {
        cputc(0x1Cu); cputs(readyfs_path_error(rc)); newline();
        return 1u;
    }
    if ((path.endpoint == RF_EP_IEC &&
         strcmp(temp_text + path.path_offset, "/") != 0) ||
        (path.endpoint != RF_EP_IEC && path.endpoint != RF_EP_ULTIMATE) ||
        path.image_depth != 0u) {
        cputs(RF_ERROR "source bad\r\n");
        return 1u;
    }
    strcpy(dest.canonical, temp_text);
    source_unit = path.unit;
    source_endpoint = path.endpoint;
    if (action != 2u) {
        rc = resolve_path(args[2], temp_text);
        if (rc != RF_PATH_OK || readyfs_path_parse(temp_text, &path) != RF_PATH_OK ||
            !path.absolute) {
            if (rc == RF_PATH_OK) cputs(RF_ERROR "dest bad\r\n");
            else { cputc(0x1Cu); cputs(readyfs_path_error(rc)); newline(); }
            return 1u;
        }
    }
    memset(&recursive_call, 0, sizeof(recursive_call));
    recursive_call.operation = RF_PLAN_CALL_INIT;
    recursive_call.plan = &recursive_plan;
    recursive_call.capacity = RF_REU_PLAN_BYTES;
    recursive_call.write = plan_reu_write;
    recursive_call.read = plan_reu_read;
    if (!readyfs_overlay_plan_call(&recursive_call)) {
        cputs(recursive_plan_failed);
        return 1u;
    }
    recursive_argc = argc;
    recursive_failed = 0u;
    if (source_endpoint == RF_EP_ULTIMATE) {
        if (!recursive_ultimate_enumerate(dest.canonical)) {
            cputs(recursive_plan_failed);
            return 1u;
        }
        entries = (unsigned int)(recursive_plan.count - 1u);
    } else if (cbm_opendir(7u, source_unit) != 0u) {
        cputs(recursive_plan_failed);
        return 1u;
    } else {
        entries = 0u;
        rc = cbm_readdir(7u, &recursive_entry);
        while (rc == 0u && entries < RF_DIR_LIMIT) {
            if (recursive_entry.type != CBM_T_HEADER) {
                kind = recursive_entry.type == CBM_T_DIR ? RF_PLAN_KIND_DIR :
                                                           RF_PLAN_KIND_FILE;
                if (!recursive_add_record(kind, recursive_entry.name)) {
                    cbm_closedir(7u); cbm_k_clrch();
                    cputs(recursive_plan_failed);
                    return 1u;
                }
                ++entries;
            }
            rc = cbm_readdir(7u, &recursive_entry);
        }
        cbm_closedir(7u);
        cbm_k_clrch();
        if (rc != 2u || entries >= RF_DIR_LIMIT) {
            cputs(recursive_plan_failed);
            return 1u;
        }
    }
    selected = (unsigned int)(recursive_plan.selected_files +
                              recursive_plan.selected_directories);
    cputs(RF_SUMMARY "recursive plan f"); print_u16(recursive_plan.files);
    display_directories = source_endpoint == RF_EP_ULTIMATE ?
                          (unsigned int)(recursive_plan.directories - 1u) :
                          recursive_plan.directories;
    cputs(" d"); print_u16(display_directories);
    cputs(" selected "); print_u16(selected); newline();
    cputs(RF_SUMMARY "plan w"); print_u16(action == 2u ? 0u : selected);
    cputs(" d"); print_u16(action == 0u ? 0u : selected);
    cputs(" m0; done w0 d0 m0\r\n");
    return 1u;
}
#endif

static void cmd_copy_move(unsigned char argc, unsigned char move_source) {
    unsigned char force;
    unsigned char copy_result;

    if (argc < 3u) {
        cputs(move_source ? "move A B [opts]\r\n" : "copy A B\r\n");
        return;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    copy_call.skip_verify = option_present(argc, "--no-verify");
#endif
#ifndef READYFS_OVERLAY_RUNTIME
    if (recursive_preview(argc, move_source ? 1u : 0u)) return;
#else
    if (option_present(argc, "--recursive") ||
        option_present(argc, "--native-pattern")) {
        (void)recursive_batch(argc, move_source ? RF_EXEC_MODE_MOVE :
                                                RF_EXEC_MODE_COPY);
        return;
    }
#endif
    if (!action_filter_accept(argc, args[1], 1u)) {
        if (has_dry_run(argc)) cputs(RF_SUMMARY "plan w0 d0 m0; done w0 d0 m0\r\n");
        return;
    }
    if (has_dry_run(argc)) {
        cmd_mutation_preview(argc);
        return;
    }
    force = option_present(argc, "--force");
#ifdef READYFS_OVERLAY_RUNTIME
    if (!path_prepare(args[1], &source) ||
        !path_prepare(args[2], &dest)) return;
    if (!action_begin(move_source ? RF_EXEC_ACTION_MOVE_FILE :
                                    RF_EXEC_ACTION_COPY_FILE,
                      source.canonical, dest.canonical)) {
        cputs(RF_ERROR "op failed\r\n");
        return;
    }
    copy_call.source = source.canonical;
    copy_call.destination = dest.canonical;
#else
    copy_call.source = args[1];
    copy_call.destination = args[2];
#endif
    copy_call.force = force;
    copy_call.move = move_source;
    copy_result = readyfs_io_copy_call(&copy_call);
    if (copy_result && move_source) {
        if (
#ifndef READYFS_OVERLAY_RUNTIME
            !path_prepare(source.canonical, &command_stream) ||
#endif
            !delete_stream(&command_stream)) {
            cputs(RF_ERROR "copy ok; delete fail\r\n");
            copy_result = 0u;
        } else cputs(RF_SUMMARY "move complete\r\n");
    }
#ifdef READYFS_OVERLAY_RUNTIME
    if (!action_complete(copy_result)) {
        return;
    }
#endif
}

static void cmd_delete(unsigned char argc) {
    unsigned char force;
    unsigned char result;

    if (argc < 2u) {
        cputs("delete P\r\n");
        return;
    }
#ifndef READYFS_OVERLAY_RUNTIME
    if (recursive_preview(argc, 2u)) return;
#else
    if (option_present(argc, "--recursive") ||
        option_present(argc, "--native-pattern")) {
        (void)recursive_batch(argc, RF_EXEC_MODE_DELETE);
        return;
    }
#endif
    if (!action_filter_accept(argc, args[1], 1u)) {
        if (has_dry_run(argc)) cputs(RF_SUMMARY "plan w0 d0 m0; done w0 d0 m0\r\n");
        return;
    }
    if (has_dry_run(argc)) {
        cmd_mutation_preview(argc);
        return;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    if (drive_partition_command(args[1], 0, argc,
                                RF_CMDPATH_SCRATCH)) return;
#endif
    if (!path_prepare(args[1], &command_stream)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (command_stream.path.endpoint == RF_EP_TAPE) {
        result_unsupported("tape delete off\r\n"); return;
    }
#endif
    if (!RF_FOUND(stream_exists(&command_stream))) {
#ifdef READYFS_OVERLAY_RUNTIME
        if (last_result != RF_RESULT_IO)
#endif
        last_result = RF_RESULT_NOT_FOUND;
        cputs(RF_ERROR "not found\r\n");
        return;
    }
    force = option_present(argc, "--force");
    if (!force && !ask_yes(args[0])) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (!action_begin(RF_EXEC_ACTION_DELETE_FILE, command_stream.canonical, 0)) {
        return;
    }
#endif
    result = delete_stream(&command_stream);
#ifdef READYFS_OVERLAY_RUNTIME
    if (!action_complete(result)) {
        return;
    }
#endif
    cputs(result ? RF_SUMMARY "deleted\r\n" : RF_ERROR "delete failed\r\n");
}

static unsigned char iec_directory_command(unsigned char device,
                                           const char *verb,
                                           const char *name) {
    if (strlen(verb) + strlen(name) > RF_LINE_CAP) {
        cputs(RF_ERROR "iec cmd long\r\n");
        return 0u;
    }
    strcpy(temp_text, verb);
    strcat(temp_text, name);
    return iec_command_ok(device, temp_text);
}

static unsigned char create_directory(ReadyFsStream *stream) {
    const char *leaf;

    if (stream->path.endpoint == RF_EP_TAPE) return 0u;
    if (stream_uses_iec(stream)) {
        if (stream->path.endpoint == RF_EP_SOFTIEC &&
            !softiec_enter_parent(stream)) return 0u;
#ifdef READYFS_OVERLAY_RUNTIME
        if (stream->path.endpoint == RF_EP_IEC)
            return RF_FOUND(native_file(stream, 0, RF_FILES_MKDIR)) &&
                   RF_FOUND(stream_find_type(stream));
#else
        if (stream->path.endpoint == RF_EP_IEC &&
            strlen(stream->native_name) > 16u) {
            cputs(RF_ERROR "iec name over 16\r\n");
            return 0u;
        }
#endif
        if (!iec_directory_command(stream->device, "md:",
                                   stream->native_name)) return 0u;
        if (stream->path.endpoint == RF_EP_SOFTIEC) return 1u;
        return RF_FOUND(stream_find_type(stream));
    }
    leaf = udos_enter_parent(stream, 1u);
    if (leaf == 0) return 0u;
    if (!uci_call(1u, 0x16u, leaf) || !uci_target_ok(1u)) return 0u;
    return RF_FOUND(stream_exists(stream));
}

static unsigned char remove_directory(ReadyFsStream *stream) {
    const char *leaf;

    if (stream->path.endpoint == RF_EP_TAPE) return 0u;
    if (stream_uses_iec(stream)) {
#ifdef READYFS_OVERLAY_RUNTIME
        if (stream->path.endpoint == RF_EP_IEC)
            return RF_FOUND(native_file(stream, 0, RF_FILES_RMDIR)) &&
                   RF_MISSING(stream_find_type(stream));
#endif
        if (!iec_directory_command(stream->device, "rd:",
                                   stream->native_name)) return 0u;
        return (unsigned char)RF_MISSING(stream_find_type(stream));
    }
    leaf = udos_find_leaf(stream, 1u);
    if (leaf == 0) return 0u;
    if (!uci_call(1u, 0x09u, leaf) || !uci_target_ok(1u)) return 0u;
    return (unsigned char)RF_MISSING(stream_exists(stream));
}

#ifdef READYFS_OVERLAY_RUNTIME
#define recursive_entry (*(struct cbm_dirent *)(void *)transfer_scratch.io)
typedef char ReadyFsRecursiveDirentFits[
    sizeof(struct cbm_dirent) <= sizeof(transfer_scratch)];

static unsigned char recursive_roots(unsigned char store) {
    if (store) {
        if (!readyfs_reu_session_store(RF_REU_RECURSIVE_ROOTS_OFF,
                                       source.canonical,
                                       RF_LINE_CAP + 1u)) return 0u;
        return readyfs_reu_session_store(
            RF_REU_RECURSIVE_ROOTS_OFF + RF_LINE_CAP + 1u,
            dest.canonical, RF_LINE_CAP + 1u);
    }
    if (!readyfs_reu_session_fetch(RF_REU_RECURSIVE_ROOTS_OFF,
                                   source.canonical,
                                   RF_LINE_CAP + 1u)) return 0u;
    return readyfs_reu_session_fetch(
        RF_REU_RECURSIVE_ROOTS_OFF + RF_LINE_CAP + 1u,
        dest.canonical, RF_LINE_CAP + 1u);
}

static void recursive_call_setup(unsigned char operation) {
    memset(&recursive_call, 0, sizeof(recursive_call));
    recursive_call.operation = operation;
    recursive_call.source_root = source.canonical;
    recursive_call.destination_root = dest.canonical;
    recursive_call.stem = temp_text;
    recursive_call.stem_capacity = sizeof(temp_text);
    recursive_call.source_text = temp.canonical;
    recursive_call.source_capacity = sizeof(temp.canonical);
    recursive_call.destination_text = backup.canonical;
    recursive_call.destination_capacity = sizeof(backup.canonical);
}

static unsigned char recursive_execute(unsigned char action,
                                       unsigned char force) {
    unsigned char result, native_mode, native_partition;

    if (action == RF_EXEC_ACTION_COPY_FILE ||
        action == RF_EXEC_ACTION_MOVE_FILE) {
        copy_call.source = temp.canonical;
        copy_call.destination = backup.canonical;
        copy_call.force = force;
        copy_call.move = (unsigned char)(action == RF_EXEC_ACTION_MOVE_FILE);
        result = readyfs_io_copy_call(&copy_call);
        if (result && action == RF_EXEC_ACTION_MOVE_FILE) {
            /* Copy I/O may reuse every stream workspace. Replay the pending
             * controller action to reconstruct its source before deleting. */
            native_mode = source.native_mode; native_partition = source.native_partition;
            if (!recursive_roots(0u)) return 0u;
            recursive_call_setup(RF_RECURSIVE_CALL_NEXT);
            if (!readyfs_overlay_recursive(&recursive_call) ||
                recursive_call.action != RF_EXEC_ACTION_MOVE_FILE ||
                !path_prepare(temp.canonical, &command_stream)) return 0u;
            command_stream.native_mode = native_mode;
            command_stream.native_partition = native_partition;
            result = delete_stream(&command_stream);
        }
        return result;
    }
    if (action == RF_EXEC_ACTION_DELETE_FILE ||
        action == RF_EXEC_ACTION_RMDIR) {
        if (!path_prepare(temp.canonical, &command_stream)) return 0u;
        return action == RF_EXEC_ACTION_DELETE_FILE ?
               delete_stream(&command_stream) :
               remove_directory(&command_stream);
    }
    if (action == RF_EXEC_ACTION_MKDIR) {
        if (!path_prepare(backup.canonical, &command_stream)) return 0u;
        /* Firmware 3.14 cannot probe directories through OPEN and rejects
         * MD:. A forced recursive merge therefore requires SoftIEC
         * containers to be precreated through their host/Ultimate path. */
        if (force && command_stream.path.endpoint == RF_EP_SOFTIEC) return 1u;
        return create_directory(&command_stream);
    }
    return 0u;
}

/* Every filesystem tree feeds the serialized ADD/start/yield/ACK controller.
 * Explicit drive-native wildcard requests retain their flat iterator. */
static unsigned char recursive_batch(unsigned char argc,
                                     unsigned char mode) {
    unsigned int entries;
    unsigned int selected;
    unsigned char rc;
    unsigned char result;
    unsigned char action;
    unsigned char force;
    unsigned char native_pattern;
    unsigned char tree_source;

    if (!readyfs_overlay_plan_available() ||
        !readyfs_overlay_journal_available() ||
        !readyfs_overlay_backend_available()) {
        cputs(RF_ERROR "batch off\r\n");
        return 0u;
    }
    native_pattern = option_present(argc, "--native-pattern");
    tree_source = 0u;
    if (resolve_path(args[1], source.canonical) != RF_PATH_OK) {
        return 0u;
    }
    if (native_pattern) {
        native_plan.operation = RF_BACKEND_CALL_NATIVE_PLAN;
        native_plan.phase = RF_NATIVEPLAN_PREPARE;
        native_plan.argc = argc;
        native_plan.args = args;
        native_plan.source = source.canonical;
        native_plan.source_path = &source.path;
        native_plan.pattern = temp_text;
        if (!readyfs_overlay_backend_call(
                (ReadyFsBackendCall *)&native_plan)) return 0u;
    } else {
        if (readyfs_path_parse(source.canonical, &source.path) != RF_PATH_OK ||
            source.path.image_depth != 0u) return 0u;
        /* Native IEC, UltimateDOS and SoftwareIEC share the tree importer.
         * Native directory preparation decides hierarchical versus flat media. */
        tree_source = (unsigned char)
            (source.path.endpoint - RF_EP_IEC) <= RF_EP_SOFTIEC - RF_EP_IEC;
        if (!tree_source) {
            cputs(RF_ERROR "source bad\r\n");
            return 0u;
        }
    }
    dest.canonical[0] = 0;
    if (mode != RF_EXEC_MODE_DELETE) {
        if (resolve_path(args[2], dest.canonical) != RF_PATH_OK ||
            readyfs_path_parse(dest.canonical, &dest.path) != RF_PATH_OK ||
            !dest.path.absolute ||
            (native_pattern && dest.path.endpoint == RF_EP_IEC &&
             dest.canonical[dest.path.path_offset + 1u] != 0)) {
            cputs(RF_ERROR "bad dest\r\n");
            return 0u;
        }
    }
    if (!recursive_roots(1u)) return 0u;
    recursive_call_setup(RF_RECURSIVE_CALL_INIT);
    recursive_call.mode = mode;
    if (!readyfs_overlay_recursive(&recursive_call)) return 0u;
    entries = selected = 0u;
    if (tree_source) {
        cmd_tree(argc, 2u);
        if (tree_failed || tree_ui.result != RF_TREE_OK) return 0u;
        recursive_call_setup(RF_RECURSIVE_CALL_IMPORT_TREE);
        recursive_call.attempted = tree_ui.queue_used;
        if (!readyfs_overlay_recursive(&recursive_call)) return 0u;
        entries = recursive_call.attempted;
        selected = recursive_call.completed;
    } else {
        if ((native_pattern ?
             cbm_opendir(7u, source.path.unit, temp_text) :
             cbm_opendir(7u, source.path.unit)) != 0u) return 0u;
        rc = cbm_readdir(7u, &recursive_entry);
        while (rc == 0u && entries < RF_DIR_LIMIT) {
            if (recursive_entry.type != CBM_T_HEADER) {
                if (recursive_entry.type == CBM_T_DIR) {
                    cbm_closedir(7u); cbm_k_clrch();
                    cputs(RF_ERROR "source bad\r\n");
                    return 0u;
                }
                native_plan.operation = RF_BACKEND_CALL_NATIVE_PLAN;
                native_plan.phase = RF_NATIVEPLAN_ADD;
                native_plan.argc = argc;
                native_plan.args = args;
                native_plan.file_type = recursive_entry.type;
                native_plan.display = native_pattern;
                native_plan.stem = recursive_entry.name;
                native_plan.recursive = &recursive_call;
                if (!readyfs_overlay_backend_call(
                        (ReadyFsBackendCall *)&native_plan)) {
                    cbm_closedir(7u); cbm_k_clrch();
                    result_unsupported("unsupported\r\n");
                    return 0u;
                }
                if (native_plan.flags & RF_PLAN_SELECTED) ++selected;
                ++entries;
            }
            rc = cbm_readdir(7u, &recursive_entry);
        }
        cbm_closedir(7u);
        cbm_k_clrch();
        if (rc != 2u || entries >= RF_DIR_LIMIT) return 0u;
    }
    native_plan.operation = RF_BACKEND_CALL_NATIVE_PLAN;
    native_plan.phase = RF_NATIVEPLAN_REPORT;
    native_plan.argc = argc;
    native_plan.args = args;
    native_plan.mode = mode;
    native_plan.entries = entries;
    native_plan.selected = selected;
    if (!readyfs_overlay_backend_call((ReadyFsBackendCall *)&native_plan)) {
        return 0u;
    }
    if (native_plan.dry_run) {
        utility_ui.operation = RF_PRESENT_PLAN;
        utility_ui.argc = mode;
        utility_ui.buffer = temp_text;
        utility_ui.value_low = entries;
        return readyfs_overlay_present(&utility_ui);
    }
    if (mode == RF_EXEC_MODE_DELETE &&
        !option_present(argc, "--force") && !ask_yes(args[0])) return 1u;
    recursive_call_setup(RF_RECURSIVE_CALL_START);
    recursive_call.mode = mode;
    recursive_call.stop_on_error = option_present(argc, "--continue") ? 0u : 1u;
    if (!readyfs_overlay_recursive(&recursive_call)) return 0u;
    force = option_present(argc, "--force");
    for (;;) {
        if (!recursive_roots(0u)) return 0u;
        recursive_call_setup(RF_RECURSIVE_CALL_NEXT);
        if (!readyfs_overlay_recursive(&recursive_call)) {
            cputs("batch stopped\r\n");
            return 0u;
        }
        action = recursive_call.action;
        if (action == RF_EXEC_ACTION_DONE) {
            utility_ui.operation = RF_PRESENT_BATCH;
            utility_ui.value_high = recursive_call.completed;
            utility_ui.value_low = recursive_call.attempted;
            utility_ui.capacity = recursive_call.failures;
            (void)readyfs_overlay_present(&utility_ui);
            return recursive_call.failures == 0u;
        }
        result = recursive_execute(action, force);
        if (!result) {
            /* Replay the still-pending action: file I/O reuses its path
             * buffers. Report the actual failed paths before acknowledging. */
            rc = last_result;
            if (recursive_roots(0u)) {
                recursive_call_setup(RF_RECURSIVE_CALL_NEXT);
                if (readyfs_overlay_recursive(&recursive_call)) {
                    utility_ui.operation = RF_PRESENT_BATCH_FAILURE;
                    utility_ui.argc = rc;
                    utility_ui.value_low = action;
                    utility_ui.buffer = temp.canonical;
                    utility_ui.workspace = backup.canonical;
                    (void)readyfs_overlay_present(&utility_ui);
                }
            }
        }
        recursive_call_setup(RF_RECURSIVE_CALL_ACK);
        recursive_call.succeeded = result;
        if (!readyfs_overlay_recursive(&recursive_call)) return 0u;
    }
}
#endif

static void cmd_mkdir_rmdir(unsigned char argc, unsigned char remove) {
    unsigned char result;
    if (argc < 2u) {
        cputs(remove ? "rmdir PATH [opts]\r\n" :
                       "mkdir PATH [opts]\r\n");
        return;
    }
    if (has_dry_run(argc)) { cmd_mutation_preview(argc); return; }
#ifdef READYFS_OVERLAY_RUNTIME
    if (drive_partition_command(args[1], 0, argc,
            remove ? RF_CMDPATH_RMDIR : RF_CMDPATH_MKDIR)) return;
#endif
    if (!path_prepare(args[1], &command_stream)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (command_stream.path.endpoint == RF_EP_TAPE) {
        result_unsupported("tape dirs off\r\n"); return;
    }
#endif
    if (!remove) {
        if (stream_exists(&command_stream)) {
            cputs("destination exists\r\n"); return;
        }
#ifdef READYFS_OVERLAY_RUNTIME
        /* Duplicate the destination as the compact RFJ1 identity. MKDIR is
         * still destination-only for backend admission. */
        if (!action_begin(RF_EXEC_ACTION_MKDIR, command_stream.canonical,
                          command_stream.canonical)) {
            return;
        }
#endif
        result = create_directory(&command_stream);
#ifdef READYFS_OVERLAY_RUNTIME
        if (!action_complete(result)) {
            return;
        }
#endif
        cputs(result ? RF_SUMMARY "directory created\r\n" : RF_ERROR "mkdir failed\r\n");
        return;
    }
    if (command_stream.path.endpoint != RF_EP_SOFTIEC &&
        !RF_FOUND(stream_exists(&command_stream))) {
        cputs(RF_ERROR "not found\r\n"); return;
    }
    if (!option_present(argc, "--force") && !ask_yes("remove empty directory")) {
        return;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    if (!action_begin(RF_EXEC_ACTION_RMDIR, command_stream.canonical, 0)) {
        return;
    }
#endif
    result = remove_directory(&command_stream);
#ifdef READYFS_OVERLAY_RUNTIME
    if (!action_complete(result)) {
        return;
    }
#endif
    cputs(result ? RF_SUMMARY "directory removed\r\n" : RF_ERROR "rmdir failed\r\n");
}

static void cmd_rename(unsigned char argc) {
    unsigned char dest_existed;

    if (argc < 3u) {
        cputs("rename A B\r\n"); return;
    }
    if (has_dry_run(argc)) { cmd_mutation_preview(argc); return; }
#ifdef READYFS_OVERLAY_RUNTIME
    if (drive_partition_command(args[1], args[2], argc,
                                RF_CMDPATH_RENAME)) return;
#endif
    if (!path_prepare(args[1], &source) || !path_prepare(args[2], &dest)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (source.path.endpoint == RF_EP_TAPE ||
        dest.path.endpoint == RF_EP_TAPE) {
        result_unsupported("tape rename off\r\n"); return;
    }
#endif
    if (same_word(source.canonical, dest.canonical)) {
        cputs(RF_ERROR "same path\r\n");
        return;
    }
    if (!RF_FOUND(stream_exists(&source))) {
        cputs(RF_ERROR "not found\r\n"); return;
    }
    dest_existed = stream_exists(&dest);
#ifdef READYFS_OVERLAY_RUNTIME
    if (RF_LOOKUP_FAILED(dest_existed)) return;
    if (!udos_distinct(&source, &dest) || !udos_validate(&dest, source.type)) return;
#endif
    if (dest_existed && !option_present(argc, "--force") &&
        !ask_yes("destination exists; replace")) return;
    if (dest_existed) {
        if (!typed_temp_stream(&dest, &backup, dest.type) ||
            !rename_stream(&dest, &backup)) {
            cputs(RF_ERROR "backup failed\r\n");
            return;
        }
    }
    if (!rename_stream(&source, &dest)) {
        if (dest_existed) (void)rename_stream(&backup, &dest);
        cputs(RF_ERROR "rename mismatch\r\n");
        return;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    if (!RF_FOUND(stream_exists(&dest)) || !RF_MISSING(stream_exists(&source))) {
#else
    if (!stream_exists(&dest) || stream_exists(&source)) {
#endif
        if (path_prepare(args[1], &command_stream)) {
            (void)rename_stream(&dest, &command_stream);
        }
        if (dest_existed) (void)rename_stream(&backup, &dest);
        cputs(RF_ERROR "rename rollback\r\n");
        return;
    }
    if (dest_existed && !delete_stream(&backup)) {
        cputs(RF_ERROR "old dest kept: "); cputs(backup.text); newline();
    }
    cputs(RF_SUMMARY "rename complete\r\n");
}

static void cmd_compare(unsigned char argc) {
    if (argc < 3u) {
        cputs("compare A B\r\n");
    }
    else (void)compare_one(args[1], args[2]);
}


static void cmd_match(unsigned char argc) {
    if (argc < 3u) { cputs("match P S\r\n"); return; }
    cputs(readyfs_overlay_match(args[1], args[2]) ? "match: yes\r\n" :
                                                       "match: no\r\n");
}

#ifdef READYFS_MONOLITHIC
static void cmd_type(unsigned char argc, unsigned char mode) {
    unsigned int total_lo;
    unsigned int total_hi;
    unsigned int before;
    unsigned int i;
    int got;
    unsigned char ch;
    (void)mode;
    if (argc < 2u) { cputs("type PATH\r\n"); return; }
    if (!path_prepare(args[1], &command_stream)) return;
    if (!stream_open_read(&command_stream, 1u, 2u)) return;
    total_lo = total_hi = 0u;
    for (;;) {
        got = stream_read(&command_stream, io_buf, sizeof(io_buf));
        if (got < 0) { cputs(RF_ERROR "read failed\r\n"); break; }
        if (got == 0) break;
        before = total_lo;
        total_lo = (unsigned int)(total_lo + (unsigned int)got);
        if (total_lo < before) ++total_hi;
        for (i = 0u; i < (unsigned int)got; ++i) {
            ch = io_buf[i];
            if (ch == '\r' || ch == '\n') newline();
            else cputc(ch >= 32u && ch <= 126u ? ch : '.');
        }
    }
    stream_close(&command_stream);
    if ((total_lo != 0u || total_hi != 0u) && wherey() != 0u) newline();
    cputs("read "); print_u32_words(total_hi, total_lo); cputs(" bytes\r\n");
}
#else
static unsigned char content_begin(unsigned char argc, unsigned char mode) {
    utility_ui.operation = RF_UTILITY_CONTENT_INIT;
    utility_ui.argc = argc;
    utility_ui.args = args;
    utility_ui.workspace = dest.canonical;
    utility_ui.value_high = mode;
    if (!readyfs_overlay_utility(&utility_ui)) {
        result_unavailable("utility off\r\n"); return 0u;
    }
    return (unsigned char)(utility_ui.value_low != 0u);
}

static void cmd_type(unsigned char argc, unsigned char mode) {
    int got;
    if (!content_begin(argc, mode)) return;
    if (!path_prepare(args[1], &command_stream)) return;
    if (!stream_open_read(&command_stream, 1u, 2u)) return;
    /* The unused destination stream owns this command's 256-byte content
     * workspace, so IEC open-name construction may freely use temp_text. */
    for (;;) {
        got = stream_read(&command_stream, io_buf, sizeof(io_buf));
        if (got < 0) { cputs(RF_ERROR "read failed\r\n"); break; }
        if (got == 0) break;
        utility_ui.operation = RF_UTILITY_CONTENT_ADD;
        utility_ui.buffer = (char *)io_buf;
        utility_ui.capacity = (unsigned int)got;
        utility_ui.workspace = dest.canonical;
        if (!readyfs_overlay_utility(&utility_ui) ||
            utility_ui.value_low == 0u) break;
    }
    stream_close(&command_stream);
    utility_ui.operation = RF_UTILITY_CONTENT_REPORT;
    utility_ui.workspace = dest.canonical;
    if (!readyfs_overlay_utility(&utility_ui))
        result_unavailable("utility off\r\n");
}
#endif

#ifdef READYFS_OVERLAY_RUNTIME
static void __fastcall__ stat_message(unsigned char mode, const char *name, unsigned int value) {
    utility_ui.operation = RF_PRESENT_STAT;
    utility_ui.argc = mode;
    utility_ui.buffer = (char *)name;
    utility_ui.value_low = value;
    (void)readyfs_overlay_present(&utility_ui);
}
#endif

static void cmd_stat(unsigned char argc) {
    struct cbm_dirent entry;

    if (argc < 2u) { cputs("stat PATH\r\n"); return; }
    if (!path_prepare(args[1], &command_stream)) return;
#ifdef READYFS_OVERLAY_RUNTIME
    if (command_stream.path.endpoint == RF_EP_TAPE) {
        stat_message(2u, command_stream.native_name, 0u);
        return;
    }
#endif
    if (stream_uses_iec(&command_stream)) {
#ifdef READYFS_OVERLAY_RUNTIME
        if (command_stream.path.endpoint == RF_EP_IEC)
            media(RF_MEDIA_SHOW, command_stream.device, 0);
#endif
        if (!RF_FOUND(stream_find_type(&command_stream))) {
            cputs(RF_ERROR "not found\r\n");
            return;
        }
#ifdef READYFS_OVERLAY_RUNTIME
        stat_message(0u, command_stream.native_name, command_stream.type);
#else
        cputs("display: "); cputs(command_stream.native_name); newline();
        cputs("type: $"); cputhex8(command_stream.type); newline();
#endif
        /* Re-open the parent scan only for regular flat IEC, where its block
         * count is directly available. SoftIEC host sizes require a separate
         * metadata API and are not mislabeled as C64 blocks. */
        if (command_stream.path.endpoint == RF_EP_IEC &&
            cbm_opendir(6u, command_stream.device) == 0u) {
            while (cbm_readdir(6u, &entry) == 0u) {
                if (same_word(entry.name, command_stream.native_name)) {
#ifdef READYFS_OVERLAY_RUNTIME
                    stat_message(1u, entry.name, entry.size);
#else
                    cputs("raw: "); cputs(entry.name); newline();
                    cputs("size est: "); print_u16(entry.size);
                    cputs(" c64 blocks\r\n");
#endif
                    break;
                }
            }
            cbm_closedir(6u); cbm_k_clrch();
        } else if (command_stream.path.endpoint == RF_EP_SOFTIEC) {
            cputs("raw: ?\r\nsize: ?\r\n");
        }
        return;
    }
    udos_find_display = command_stream.canonical;
    (void)udos_find_leaf(&command_stream, 1u);
    udos_find_display = 0;
    if (!stream_open_read(&command_stream, 1u, 2u)) return;
    if (!uci_call(1u, 0x07u, 0)) { stream_close(&command_stream); return; }
    cputs("type: $"); cputhex8(command_stream.type); newline();
    if (uci_xfer.data_len >= 4u) {
        cputs("size exact: ");
        print_u32_words((unsigned int)uci_data[2] |
                        ((unsigned int)uci_data[3] << 8u),
                        (unsigned int)uci_data[0] |
                        ((unsigned int)uci_data[1] << 8u));
        cputs(" bytes\r\n");
    }
    if (uci_xfer.stat_len != 0u && !uci_status_ok(1u)) show_uci_failure();
    else cputs("status: ok\r\n");
    stream_close(&command_stream);
}

#ifndef READYFS_OVERLAY_RUNTIME
static unsigned char print_softiec_mapping(unsigned char partition) {
    unsigned int len;

    /* Resolve the partition's root directory.  A "$" suffix asks for a
     * directory-listing pseudo-file and yields FILE NOT FOUND even when the
     * partition itself is valid, so it cannot distinguish mapped/unmapped. */
    strcpy(format_u16(temp_text, partition), ":");
    uci_cmd[0] = 5u;
    uci_cmd[1] = 0x22u;
    uci_cmd[2] = 0u; /* read/default PRG channel; name itself requests dir */
    len = 3u;
    strcpy((char *)uci_cmd + len, temp_text);
    len += strlen(temp_text);
    /* SoftwareIEC GET_FATNAME uses the same complete ReadyIRC-derived UCI
     * state machine. The transport owns async PUSH/DATA_ACC, queue drains,
     * bounded recovery, and the final quiet-idle wait. */
    if (!uci_call_raw(uci_cmd, len)) return 0u;
    if (!uci_status_ok(5u)) {
        if (uci_xfer.stat_len != 0u && uci_stat[0] == 0x08u) {
            cputs("unmapped\r\n");
            return 2u;
        }
        show_uci_failure();
        return 0u;
    }
    cputs("raw mapping: ");
    print_data_text();
    newline();
    return 1u;
}

static void cmd_volume(unsigned char argc) {
    ReadyFsPath path;
    struct cbm_dirent entry;
    const char *text;
    unsigned char rc;
    unsigned char saw_header;

    text = argc >= 2u ? args[1] : cwd_buf;
    rc = resolve_path(text, temp_text);
    if (rc == RF_PATH_OK) rc = readyfs_path_parse(temp_text, &path);
    if (rc != RF_PATH_OK || !path.absolute) {
        if (rc == RF_PATH_OK) cputs("absolute");
        else { cputc(0x1Cu); cputs(readyfs_path_error(rc)); }
        newline();
        return;
    }
    cputs("path: "); cputs(temp_text); newline();
    if (iec_partition_driver_pending(&path)) return;
    if (path.endpoint == RF_EP_IEC) {
#ifdef READYFS_OVERLAY_RUNTIME
        media(RF_MEDIA_SHOW, path.unit, 0);
#endif
        cputs("backend: iec device "); print_u16(path.unit); newline();
        if (cbm_opendir(6u, path.unit) != 0u) {
            cputs(RF_ERROR "dir open failed\r\n");
            return;
        }
        saw_header = 0u;
        do {
            rc = cbm_readdir(6u, &entry);
            if (rc == 0u && entry.type == CBM_T_HEADER && !saw_header) {
                cputs("volume: "); cputs(entry.name); newline();
                saw_header = 1u;
            }
        } while (rc == 0u);
        cbm_closedir(6u);
        cbm_k_clrch();
        if (rc == 2u) {
            cputs("free: "); print_u16(entry.size);
            cputs(" c64 blocks\r\n");
        } else cputs(RF_ERROR "free unavailable\r\n");
        return;
    }
    if (path.endpoint == RF_EP_ULTIMATE) {
        cputs("ultimate dos\r\n");
        if (!readyfs_uci_detect()) {
            result_unavailable("uci unavailable\r\n"); return;
        }
        if (!udos_change_absolute(1u, temp_text + path.path_offset)) {
            cputs(RF_ERROR "fail\r\n");
            return;
        }
        if (uci_call(1u, 0x12u, 0) && uci_target_ok(1u)) {
            cputs("raw path: "); print_data_text(); newline();
        }
        cputs(RF_ERROR "free unavailable\r\n");
        return;
    }
    if (path.endpoint == RF_EP_SOFTIEC) {
        if (!readyfs_uci_detect()) {
            cputs("backend: softiec partition "); print_u16(path.unit); newline();
            result_unavailable("uci unavailable\r\n");
            return;
        }
        cputs("backend: softiec partition "); print_u16(path.unit);
        cputs(" on bus "); print_u16(readyfs_uci_softiec_bus()); newline();
        (void)print_softiec_mapping(path.unit);
        cputs(RF_ERROR "free unavailable\r\n");
        return;
    }
    cputs("tape backend\r\n");
    cputs("no tape free\r\n");
}

#else
static void cmd_volume(unsigned char argc) {
    ReadyFsPath path;
    ReadyFsVolumeCall call;
    unsigned char rc;
    rc=resolve_path(argc>=2u ? args[1] : cwd_buf,temp_text);
    if(rc==RF_PATH_OK)rc=readyfs_path_parse(temp_text,&path);
    if(rc!=RF_PATH_OK || !path.absolute) {
        last_result=RF_RESULT_USAGE;
        cputs(RF_ERROR "absolute path required\r\n");return;
    }
    call.path=&path;call.text=temp_text;call.directory=0;
    call.status=&last_result;
    if(path.endpoint==RF_EP_IEC) {
        if(!path_prepare(temp_text,&source) ||
           native_file(&source,0,RF_FILES_DIRECTORY)!=RF_LOOKUP_FOUND)return;
        call.text=source.canonical;call.directory=temp_text;
        media(RF_MEDIA_SHOW,path.unit,0);
    }
    (void)readyfs_overlay_volume(&call);
}
#endif

#ifdef READYFS_OVERLAY_RUNTIME
static unsigned char tape_designator(const char *text, unsigned char endpoint,
                                     unsigned char *unit) {
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_DESIGNATOR;
    tape_call.text = text;
    tape_call.value = endpoint;
    tape_call.output = (char *)unit;
    if (!readyfs_overlay_tape(&tape_call)) return 0u;
    return tape_call.result;
}
#define parse_drive_designator(text, unit) \
    tape_designator((text), RF_EP_IEC, (unit))
#define softiec_designator(text, unit) \
    tape_designator((text), RF_EP_SOFTIEC, (unit))
#else
static unsigned char parse_drive_designator(const char *text,
                                            unsigned char *unit) {
    ReadyFsPath path;
    unsigned char rc;

    rc = readyfs_path_parse(text, &path);
    if (rc != RF_PATH_OK || path.endpoint != RF_EP_IEC ||
        path.partition != 0u ||
        text[path.path_offset] != 0) return 0u;
    *unit = path.unit;
    return 1u;
}
#endif

static const char *option_value(unsigned char argc, const char *option) {
#ifdef READYFS_OVERLAY_RUNTIME
    memset(&tape_call, 0, sizeof(tape_call));
    tape_call.operation = RF_TAPE_OPTION_VALUE;
    tape_call.argc = argc;
    tape_call.args = args;
    tape_call.text = option;
    if (!readyfs_overlay_tape(&tape_call)) return 0;
    return tape_call.found;
#else
    unsigned char i;
    for (i = 1u; i + 1u < argc; ++i) {
        if (same_word(args[i], option)) return args[i + 1u];
    }
    return 0;
#endif
}

#ifndef READYFS_OVERLAY_RUNTIME
static unsigned char softiec_designator(const char *text,
                                        unsigned char *partition) {
    ReadyFsPath path;
    if (readyfs_path_parse(text, &path) != RF_PATH_OK ||
        path.endpoint != RF_EP_SOFTIEC || text[path.path_offset] != 0) return 0u;
    *partition = path.unit;
    return 1u;
}
#endif

static unsigned char softiec_raw_path(const char *source, char *raw) {
    ReadyFsPath path;
    const char *host;
    char *scan;

    if (resolve_path(source, temp_text) != RF_PATH_OK ||
        readyfs_path_parse(temp_text, &path) != RF_PATH_OK ||
        path.endpoint != RF_EP_ULTIMATE || !path.absolute ||
        path.image_depth != 0u) return 0u;
    host = temp_text + path.path_offset;
    /* ADD_PARTITION resolves against SoftwareIEC's live virtual root.  The
     * physical 3.14 unit exposes USB1 there; /USB0 is only its stale saved
     * default-path spelling and target $05 correctly rejects that rewrite. */
    strcpy(raw, host);
    /* Typed '_' is PETSCII $A4.  ADD_PARTITION consumes a host pathname and,
     * like component CD, requires the live FAT-name byte $5F. */
    scan = raw;
    while (*scan != 0) {
        if ((unsigned char)*scan == 0xA4u) *scan = 0x5Fu;
        ++scan;
    }
    return 1u;
}

static void cmd_softiec_mount(unsigned char argc, unsigned char partition) {
    const char *name;
    unsigned int len;

    name = option_value(argc, "--name");
    if (name == 0 || name[0] == 0 || strchr(name, ':') != 0) {
        cputs("--name IDENT required\r\n");
        return;
    }
    if (!softiec_raw_path(args[1], source.canonical)) {
        cputs(RF_ERROR "need u: folder\r\n");
        return;
    }
    if (!readyfs_uci_detect()) {
        result_unavailable("uci unavailable\r\n"); return;
    }
    if (!option_present(argc, "--force") &&
        !ask_yes("map softiec partition")) return;
    uci_cmd[0] = 5u;
    uci_cmd[1] = 0x20u;
    uci_cmd[2] = partition;
    len = 3u;
    strcpy((char *)uci_cmd + len, name);
    len += strlen(name);
    uci_cmd[len++] = ':';
    strcpy((char *)uci_cmd + len, source.canonical);
    len += strlen(source.canonical);
    /* SoftwareIEC mapping uses the same complete UCI transaction contract;
     * firmware 3.14 status is normalized as binary or legacy ASCII success. */
    if (uci_call_raw(uci_cmd, len) && uci_target_ok(5u)) {
        cputs(RF_SUMMARY "softiec s"); print_u16(partition);
        cputs(": mapped to raw "); cputs(source.canonical); newline();
    }
}

static void cmd_softiec_unmap(unsigned char argc, unsigned char partition) {
    if (!readyfs_uci_detect()) {
        result_unavailable("uci unavailable\r\n"); return;
    }
    if (!option_present(argc, "--force") &&
        !ask_yes("unmap softiec partition")) return;
    uci_cmd[0] = 5u;
    uci_cmd[1] = 0x21u;
    uci_cmd[2] = partition;
    if (uci_call_raw(uci_cmd, 3u) && uci_target_ok(5u)) {
        cputs(RF_SUMMARY "softiec unmapped\r\n");
    }
}

static void cmd_mount(unsigned char argc) {
    const char *leaf;
    unsigned int len;
    unsigned char unit;

    if (argc < 2u) { cputs("mount IMAGE DRIVE:\r\n"); return; }
    if (has_dry_run(argc)) { cmd_mutation_preview(argc); return; }
#ifdef READYFS_OVERLAY_RUNTIME
    if (drive_partition_command(args[1], 0, argc,
             args[0][0] == 'f' ? RF_CMDPATH_FORMAT : RF_CMDPATH_MOUNT)) return;
#endif
    if (argc < 3u) { cputs("mount IMAGE DRIVE:\r\n"); return; }
    if (softiec_designator(args[2], &unit)) {
        cmd_softiec_mount(argc, unit);
        return;
    }
    if (!parse_drive_designator(args[2], &unit)) {
        cputs(RF_ERROR "need drive target\r\n");
        return;
    }
    if (!path_prepare(args[1], &command_stream) ||
        command_stream.path.endpoint != RF_EP_ULTIMATE) {
        cputs(RF_ERROR "mount needs u: image\r\n");
        return;
    }
    if (!readyfs_uci_detect()) {
        result_unavailable("uci unavailable\r\n"); return;
    }
    if (!option_present(argc, "--force") &&
        !ask_yes("replace mounted media")) return;
    leaf = udos_find_leaf(&command_stream, 1u);
    if (leaf == 0) {
        cputs(RF_ERROR "image not found\r\n"); return;
    }
#ifdef READYFS_OVERLAY_RUNTIME
    media(RF_MEDIA_FORGET, unit, 0);
#endif
    uci_cmd[0] = 1u;
    uci_cmd[1] = 0x23u;
    uci_cmd[2] = unit;
    len = 3u;
    strcpy((char *)uci_cmd + len, leaf);
    len += strlen(leaf);
    /* Same state-machine contract as all ReadyFS UCI calls: the transport
     * owns asynchronous PUSH, queue drains, DATA_ACC, and quiet-idle finish. */
    if (uci_call_raw(uci_cmd, len) && uci_target_ok(1u)) {
#ifdef READYFS_OVERLAY_RUNTIME
        media(RF_MEDIA_REMEMBER, unit, command_stream.canonical);
#else
        cputs(RF_SUMMARY "mounted on "); print_u16(unit); cputs(":\r\n");
#endif
    }
}

static void cmd_drive_media(unsigned char argc, unsigned char swap) {
    unsigned char unit;
    unsigned char command;

    if (argc < 2u) {
        cputs(swap ? "swap DRIVE:\r\n" : "dismount DRIVE:\r\n");
        return;
    }
    if (has_dry_run(argc)) { cmd_mutation_preview(argc); return; }
#ifdef READYFS_OVERLAY_RUNTIME
    if (!swap && drive_partition_command(args[1], 0, argc,
                                         RF_CMDPATH_UNMOUNT)) return;
#endif
    if (!swap && softiec_designator(args[1], &unit)) {
        cmd_softiec_unmap(argc, unit);
        return;
    }
    if (!parse_drive_designator(args[1], &unit)) {
        cputs("drive 8:-30\r\n");
        return;
    }
    if (!readyfs_uci_detect()) {
        result_unavailable("uci unavailable\r\n"); return;
    }
    if (!option_present(argc, "--force") &&
        !ask_yes(swap ? "advance disk swap list" : "dismount media")) return;
#ifdef READYFS_OVERLAY_RUNTIME
    media(RF_MEDIA_FORGET, unit, 0);
#endif
    command = swap ? 0x25u : 0x24u;
    uci_cmd[0] = 1u;
    uci_cmd[1] = command;
    uci_cmd[2] = unit;
    if (uci_call_raw(uci_cmd, 3u) && uci_target_ok(1u)) {
        cputs(swap ? RF_SUMMARY "disk swap requested\r\n" : RF_SUMMARY "media dismounted\r\n");
    }
}

static void cmd_mutation_preview(unsigned char argc) {
    utility_ui.operation = RF_UTILITY_PREVIEW;
    utility_ui.value_low = dispatch_command;
    utility_ui.argc = argc;
    utility_ui.args = args;
    if (!readyfs_overlay_utility(&utility_ui))
        result_unavailable("utility off\r\n");
}

static void cmd_capabilities(unsigned char argc) {
    unsigned char rc;
    if (argc > 1u) {
        rc = resolve_path(args[1], temp_text);
        if (rc != RF_PATH_OK) {
            cputc(0x1Cu); cputs(readyfs_path_error(rc)); newline(); return;
        }
        utility_ui.buffer = temp_text;
    } else utility_ui.buffer = cwd_buf;
    utility_ui.operation = RF_UTILITY_CAPABILITIES;
    utility_ui.argc = argc;
    utility_ui.args = args;
    if (!readyfs_overlay_utility(&utility_ui))
        result_unavailable("utility off\r\n");
}

#ifdef READYFS_OVERLAY_RUNTIME
unsigned char __fastcall__ readyfs_script_exists(const char *path) {
    unsigned char found;
    if (!path_prepare(path, &command_stream)) return 2u;
    found = stream_exists(&command_stream);
    return RF_LOOKUP_FAILED(found) ? 2u : (unsigned char)(found != 0u);
}
#endif

#ifdef READYFS_OVERLAY_RUNTIME
#pragma static-locals (push, on)
static void cmd_run(unsigned char argc) {
    unsigned int size;
    unsigned int commands;
    unsigned char done;
    unsigned char keep_running;
    int got;

    if (argc < 2u || argc > 11u) { last_result = RF_RESULT_USAGE; cputs("run FILE [ARGS]\r\n"); return; }
    if (batch_active) { cputs(RF_ERROR "nested run off\r\n"); return; }
    batch_ui.operation = RF_ENV_ARGUMENTS;
    batch_ui.argc = argc; batch_ui.args = args;
    if (!readyfs_overlay_script(&batch_ui)) { result_unavailable("batch off\r\n"); return; }
    if (!path_prepare(args[1], &command_stream) ||
        !stream_open_read(&command_stream, 1u, 2u)) return;
    size = 0u;
    done = 0u;
    while (!done) {
        got = stream_read(&command_stream, io_buf, sizeof(io_buf));
        if (got < 0) { cputs(RF_ERROR "script read fail\r\n"); done = 2u; }
        else if (got == 0) done = 1u;
        else if (size > (unsigned int)(RF_REU_BATCH_DATA_BYTES -
                                      (unsigned int)got) ||
                 !readyfs_reu_batch_store(
                     (unsigned int)(RF_REU_BATCH_DATA_OFF + size),
                     io_buf, (unsigned int)got)) {
            cputs("script too large\r\n");
            done = 2u;
        } else size = (unsigned int)(size + (unsigned int)got);
    }
    stream_close(&command_stream);
    if (done != 1u) return;

    batch_ui.operation = RF_BATCH_INIT;
    batch_ui.size = size;
    if (!readyfs_overlay_batch(&batch_ui)) {
        result_unavailable("batch off\r\n"); return;
    }
    commands = 0u;
    for (;;) {
        batch_ui.operation = RF_BATCH_NEXT;
        batch_ui.buffer = line_buf;
        batch_ui.capacity = sizeof(line_buf);
        batch_ui.args = args;
        if (!readyfs_overlay_batch(&batch_ui)) {
            result_unavailable("batch off\r\n"); break;
        }
        if (batch_ui.action == RF_BATCH_DONE) break;
        argc = batch_ui.argc;
        ++commands;
        cputs("batch> "); cputs(args[0]); newline();
        batch_prompt_denied = 0u;
        batch_active = 1u;
        keep_running = dispatch(argc);
        batch_active = 0u;
        batch_ui.operation = RF_BATCH_ACK;
        batch_ui.rc = batch_prompt_denied ? RF_RESULT_INTERACTION :
                      (keep_running ? last_result : RF_RESULT_OK);
        batch_ui.finish = (unsigned char)!keep_running;
        if (!readyfs_overlay_batch(&batch_ui)) {
            result_unavailable("batch off\r\n"); break;
        }
    }
    batch_active = 0u;
    batch_ui.operation = RF_BATCH_REPORT;
    if (!readyfs_overlay_batch(&batch_ui))
        result_unavailable("batch report off\r\n");
    else {
        cputs(RF_SUMMARY "run done lines "); print_u16(batch_ui.size);
        cputs(" commands "); print_u16(commands);
        cputs(" rc "); print_u16(batch_ui.rc); newline();
        last_result = batch_ui.rc;
    }
}
#endif

#ifdef READYFS_OVERLAY_RUNTIME
#pragma static-locals (pop)
static void cmd_status(void) {
    tree_ui.operation = RF_TREE_CALL_STATUS;
    tree_ui.parent = cwd_buf;
    tree_ui.result = last_result;
    if (!readyfs_overlay_tree(&tree_ui)) cputs(RF_ERROR "status off\r\n");
}
#endif

static unsigned char dispatch(unsigned char argc) {
    unsigned char command;
    if (argc == 0u) return 1u;
#ifdef READYFS_OVERLAY_RUNTIME
    tree_ui.operation = RF_TREE_CALL_COMMAND_ID;
    tree_ui.name = args[0];
    tree_ui.command_args = args;
    tree_ui.command_argc = argc;
    tree_ui.result = RF_COMMAND_UNKNOWN;
    if (!readyfs_overlay_tree(&tree_ui)) {
        result_unavailable("tree off\r\n"); return 1u;
    }
    command = tree_ui.result;
#else
    command = readyfs_command_id(args[0]);
#endif
    dispatch_command = command;
    /* STATUS reports the preceding command's typed result.  Every other
     * recognized command starts from OK and may replace it with a more
     * specific result while it runs. */
    if (command != RF_COMMAND_STATUS && command != RF_COMMAND_UNKNOWN) {
        last_result = RF_RESULT_OK;
    }
    if (command == RF_COMMAND_EXIT) return 0u;
    if (command == RF_COMMAND_HELP) {
#ifdef READYFS_OVERLAY_RUNTIME
        if (argc > 1u) {
            tree_ui.name = args[1]; tree_ui.command_args = 0;
            (void)readyfs_overlay_tree(&tree_ui);
            utility_ui.operation = RF_PRESENT_HELP;
            utility_ui.value_low = tree_ui.result;
            utility_ui.buffer = args[1];
            (void)readyfs_overlay_present(&utility_ui);
        } else
#endif
        if (!readyfs_overlay_help())
            result_unavailable("off\r\n");
    }
    else if (command == RF_COMMAND_PROBE) cmd_probe(argc);
#ifdef READYFS_OVERLAY_RUNTIME
    else if (command == RF_COMMAND_IEC) {
        iec_call.args = args; iec_call.argc = argc;
        iec_call.command = (unsigned char *)source.canonical;
        iec_call.reply = (unsigned char *)temp_text;
        iec_call.status = &last_result;
        (void)readyfs_overlay_iec(&iec_call);
    }
    else if (command == RF_COMMAND_PROFILE) {
        drive_ui.operation = RF_DRIVEUI_QUERY;
        drive_ui.argc = argc;
        drive_ui.args = args;
        if (!readyfs_overlay_drive(&drive_ui))
            result_unavailable("profile off\r\n");
    }
    else if (command == RF_COMMAND_NATIVE) {
        native_ui.argc = argc;
        native_ui.args = args;
        native_ui.output = source.canonical;
        native_ui.followup = dest.canonical;
        if (!readyfs_overlay_native(&native_ui))
            result_unavailable("native off\r\n");
    }
#endif
    else if (command == RF_COMMAND_DRIVES) cmd_drives();
    else if (command == RF_COMMAND_PWD) { cputs(cwd_buf); newline(); }
    else if (command == RF_COMMAND_HISTORY) {
        utility_ui.operation = RF_UTILITY_HISTORY;
        utility_ui.argc = argc;
        utility_ui.args = args;
        utility_ui.buffer = temp_text;
        utility_ui.capacity = sizeof(temp_text);
        if (!readyfs_overlay_utility(&utility_ui))
            result_unavailable("utility off\r\n");
    }
    else if (command == RF_COMMAND_CLEAR) {
        clrscr();
    }
    else if (command == RF_COMMAND_CD) cmd_cd(argc);
    else if (command == RF_COMMAND_ALIAS) cmd_alias(argc);
    else if (command == RF_COMMAND_UNALIAS) cmd_unalias(argc);
    else if (command == RF_COMMAND_CONFIG) cmd_config(argc);
    else if (command == RF_COMMAND_DIR) cmd_dir(argc);
#ifdef READYFS_OVERLAY_RUNTIME
    else if (command == RF_COMMAND_TREE) cmd_tree(argc, 0u);
    else if (command == RF_COMMAND_FIND) cmd_tree(argc, 1u);
#else
    else if (command == RF_COMMAND_TREE)
        result_unavailable("tree needs overlay\r\n");
    else if (command == RF_COMMAND_FIND)
        result_unavailable("find needs overlay\r\n");
#endif
    else if (command == RF_COMMAND_STAT) cmd_stat(argc);
    else if (command == RF_COMMAND_VOLUME) cmd_volume(argc);
    else if (command == RF_COMMAND_MATCH) cmd_match(argc);
    else if (command == RF_COMMAND_TYPE) cmd_type(argc, RF_CONTENT_TYPE);
    else if (command >= RF_COMMAND_HEAD && command <= RF_COMMAND_TEST) {
#ifdef READYFS_MONOLITHIC
        result_unavailable("content needs overlay\r\n");
#else
        cmd_type(argc, (unsigned char)(RF_CONTENT_HEAD +
                                      command - RF_COMMAND_HEAD));
#endif
    }
    else if (command >= RF_COMMAND_COPY && command <= RF_COMMAND_MOVE) {
        cmd_copy_move(argc, (unsigned char)(command - RF_COMMAND_COPY));
    } else if (command == RF_COMMAND_RENAME) {
        cmd_rename(argc);
    } else if (command == RF_COMMAND_DELETE) {
        cmd_delete(argc);
    } else if (command == RF_COMMAND_COMPARE) {
        cmd_compare(argc);
    } else if (command == RF_COMMAND_NEW) {
        cmd_new(argc);
    } else if (command == RF_COMMAND_WRITE) {
        cmd_write(argc);
    } else if (command == RF_COMMAND_APPEND) {
        cmd_append(argc);
    } else if (command >= RF_COMMAND_MKDIR && command <= RF_COMMAND_RMDIR) {
        cmd_mkdir_rmdir(argc, (unsigned char)(command - RF_COMMAND_MKDIR));
    } else if (command == RF_COMMAND_MOUNT) {
        cmd_mount(argc);
    } else if (command >= RF_COMMAND_DISMOUNT && command <= RF_COMMAND_SWAP) {
        cmd_drive_media(argc,
                        (unsigned char)(command - RF_COMMAND_DISMOUNT));
    } else if (command == RF_COMMAND_CAPABILITIES) {
        cmd_capabilities(argc);
    } else if (command == RF_COMMAND_STATUS) {
#ifdef READYFS_OVERLAY_RUNTIME
        cmd_status();
#else
        result_unavailable("status needs overlay\r\n");
#endif
    } else if (command == RF_COMMAND_RUN) {
#ifdef READYFS_OVERLAY_RUNTIME
        cmd_run(argc);
#else
        result_unavailable("run needs overlay\r\n");
#endif
    } else {
        last_result = RF_RESULT_UNKNOWN;
        cputs(RF_ERROR "unknown; type help\r\n");
        return 1u;
    }
    return 1u;
}

int main(void) {
    unsigned char argc;

    bordercolor(COLOR_BLUE);
    bgcolor(COLOR_BLUE);
    textcolor(COLOR_WHITE);
    clrscr();
    /* REST run_prg and prior diagnostic programs can leave KERNAL logical
     * files registered even though ReadyFS starts as a new standalone app. */
    cbm_k_clall();
    cputs("readyfs lab 0.1\r\n");
    reu_available = readyfs_reu_init();
    overlay_available = readyfs_overlay_init(reu_available);
    readyfs_console_recording = 1u;
    if (reu_available) aliases_clear_reu();
    cputs("reu: ");
    if (reu_available) {
        print_u16(readyfs_reu_bank_count());
        cputs(" banks\r\n");
    } else cputs(RF_ERROR "need 1 mib\r\n");
    cputs("overlay: ");
    if (overlay_available) {
#ifdef READYFS_OVERLAY_RUNTIME
        cputs("cmdpath: ready\r\n");
#else
        cputs("ready\r\n");
#endif
    }
    else cputs(RF_ERROR "unavailable\r\n");
    cputs("planner: ");
    cputs(readyfs_overlay_plan_available() ? "ready\r\n" : "unavailable\r\n");
#ifdef READYFS_OVERLAY_RUNTIME
    cputs("journal: ");
    cputs(readyfs_overlay_journal_available() &&
          readyfs_overlay_backend_available() ? "ready backend: ready\r\n" :
                                                "unavailable\r\n");
    cputs("batch: ");
    cputs(readyfs_overlay_batch_available() ? "ready\r\n" :
                                               "unavailable\r\n");
#endif
    for (;;) {
        read_line();
        readyfs_reu_history_add(line_buf);
#ifdef READYFS_OVERLAY_RUNTIME
        batch_ui.operation = RF_BATCH_INTERACTIVE;
        /* Editor returns this same resident buffer and capacity. */
        batch_ui.args = args; batch_ui.rc = last_result;
        if (!readyfs_overlay_batch(&batch_ui)) { result_unavailable("batch off\r\n"); continue; }
        if (batch_ui.action != RF_BATCH_COMMAND) { last_result = batch_ui.rc; continue; }
        argc = batch_ui.argc;
#else
        argc = split_args(line_buf);
#endif
        if (!dispatch(argc)) break;
    }
    return 0;
}
