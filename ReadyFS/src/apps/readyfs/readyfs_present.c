#include "readyfs_present.h"
#include <conio.h>
#include "readyfs_path.h"
#include <string.h>
#include "readyfs_console.h"
#include "readyfs_uci.h"
unsigned int readyfs_present_abi(void) {
    return RF_PRESENT_ABI;
}
#ifdef READYFS_MONOLITHIC
extern void print_u16(unsigned int value);
#define number print_u16
#else
static void number(unsigned int value) {
    char text[6]; unsigned char i = 0u;
    do { text[i++] = '0' + value % 10u; value /= 10u; } while (value);
    while (i) cputc(text[--i]);
}
#endif
unsigned char readyfs_present(ReadyFsUtilityCall *call) {
    unsigned char i, type; unsigned int n;
    const char *name;
    ReadyFsPath path;
#ifndef READYFS_MONOLITHIC
    const ReadyFsUciTransfer *xfer;
    char *last;
#endif
    const ReadyFsDirectoryEntry *entry;
#ifndef READYFS_MONOLITHIC
    if (call->operation == RF_PRESENT_BATCH_FAILURE) {
        cputs(RF_ERROR "batch action "); number(call->value_low);
        cputs(" failed rc "); number(call->argc); cputs("\r\n");
        cputs(call->buffer); cputs("\r\n");
        cputs(call->workspace); cputs("\r\n"); return 1u;
    }
    if (call->operation == RF_PRESENT_STAT) {
        cputs(call->argc == 1u ? "raw: " : "display: ");
        cputs(call->buffer); cputs("\r\n");
        if (call->argc == 1u) {
            cputs("size est: "); number(call->value_low); cputs(" c64 blocks\r\n");
        } else if (call->argc == 2u) cputs("type: seq\r\nsize: sequential unknown\r\n");
        else { cputs("type: $"); cputhex8((unsigned char)call->value_low); cputs("\r\n"); }
        return 1u;
    }
    if (call->operation == RF_PRESENT_BATCH) {
        cputs(RF_SUMMARY "batch done "); number(call->value_high); cputc('/'); number(call->value_low);
        if (call->capacity) cputs(RF_ERROR);
        cputs(" fail "); number(call->capacity); cputs("\r\n"); return 1u;
    }
    if (call->operation == RF_PRESENT_COPY) return readyfs_transfer_present(call);
#ifndef __CC65__
    if (call->operation == RF_PRESENT_MEDIA) return readyfs_media(call);
#endif
    if (call->operation == RF_PRESENT_DATA_TEXT) {
        for (n = 0u; n < call->value_low; ++n) {
            i = (unsigned char)call->buffer[n];
            cputc(i >= 32u && i < 127u ? i : '.');
        }
        return 1u;
    }
    if (call->operation == RF_PRESENT_STAGE_NAME) {
        /* The canonical parent includes endpoint, partition and image view.
         * A stage must never fall back to the IEC device root. */
        strcpy(call->workspace, call->buffer);
        last = strrchr(call->workspace, '/');
        if (!last || (unsigned int)(last - call->workspace) + 7u > RF_PATH_MAX) return 0u;
        ++last;
        /* SD2IEC forces an X00 wrapper for invalid FAT characters even in
         * raw XE0 mode. Keep stages FAT-safe; the existence probe still guards
         * this temporary namespace against collisions. */
        strcpy(last, "rft");
        last[3] = "0123456789abcdef"[(unsigned char)call->value_low >> 4u];
        last[4] = "0123456789abcdef"[call->value_low & 15u];
        last[5] = 0;
        return 1u;
    }
    if (call->operation == RF_PRESENT_UCI_ERROR) {
        xfer = (const ReadyFsUciTransfer *)call->buffer;
        cputs(RF_ERROR);
        if (xfer->flags) {
            cputs("transport $"); cputhex8(xfer->flags);
            cputs(" st $"); cputhex8(xfer->last_status);
            cputs(" d/s "); number(xfer->data_seen); cputc('/'); number(xfer->stat_seen);
        } else {
            cputs("target: ");
            for (n = 0u; n < xfer->stat_len; ++n) {
                i = xfer->stat[n];
                if (i >= 32u && i < 127u) cputc(i);
                else { cputc('$'); cputhex8(i); cputc(' '); }
            }
        }
        cputs("\r\n"); return 1u;
    }
#endif
    if (call->operation == RF_PRESENT_CD) {
        n = call->value_low;
        if (n == RF_PATH_OK) n = readyfs_path_parse(call->buffer, &path);
        if (n != RF_PATH_OK || !path.absolute) {
            cputs(RF_ERROR);
            if (n == RF_PATH_OK) cputs("absolute");
            else cputs(readyfs_path_error((unsigned char)n));
            cputs("\r\n");
        } else strcpy(call->workspace, call->buffer);
        return 1u;
    }
    if (call->operation == RF_PRESENT_FREE) {
        number(call->value_low); cputs(" blocks free.\r\n"); return 1u;
    }
    if (call->operation == RF_PRESENT_DIR) {
        entry = (const ReadyFsDirectoryEntry *)call->buffer;
        name = entry->name; type = entry->type; n = entry->size;
    } else {
        name = call->buffer; type = (unsigned char)call->value_high;
        n = call->value_low;
    }
    if (call->operation == RF_PRESENT_HOST) cputs("?    ");
    else {
        number(n); cputc(' ');
        if (n < 1000u) cputc(' ');
        if (n < 100u) cputc(' ');
        if (n < 10u) cputc(' ');
    }
    if (type == 5u) revers(1u);
    cputc('"');
    for (i = 0u; i < (call->operation == RF_PRESENT_DIR ? 16u : call->capacity) && name[i]; ++i) cputc(name[i]);
    cputc('"');
    while (i++ < 16u) cputc(' ');
    if (type == 5u) revers(0u);
    cputc(' ');
    cputs(type == 5u ? "" : type == 2u ? "dir" :
          type == 0x11u ? "prg" : type == 0x10u ? "seq" :
          type == 0x12u ? "usr" : type == 0x13u ? "rel" :
          type == 0u ? "del" : "---");
    cputs("\r\n"); return 1u;
}
