/* Native IEC leaf I/O. No native CLOSE15, overlay loads, UCI or network. */
#include "readyfs_files.h"
#include "readyfs_result.h"
#include "readyfs_reu.h"
#include "readyfs_driver.h"
#include "readyfs_console.h"
#include <cbm.h>
#include <cbm_filetype.h>
#include <conio.h>
#include <string.h>
/* The same pure classifier is compiled into both leaf slots; no call into
 * slot6 can occur while slot19 is resident. */
#define READYFS_CLASSIFIER_ONLY
#define readyfs_driver_classify readyfs_files_classify
#include "readyfs_driver.c"
#undef readyfs_driver_classify
#undef READYFS_CLASSIFIER_ONLY
extern unsigned char readyfs_same_word(const char *, const char *);
unsigned int readyfs_files_abi(void) { return RF_FILES_ABI; }

static unsigned char error(ReadyFsFilesCall *c) {
    *c->status = RF_RESULT_IO;
    cputs(RF_ERROR "iec operation failed\r\n");
    return RF_LOOKUP_ERROR;
}

/* TALK the always-present DOS channel directly. OPEN/CLOSE15 would destroy
 * live SD2IEC data buffers, including a copy's source on the same device. */
static unsigned char receive(ReadyFsFilesCall *c) {
    unsigned char n, st, value, stored;
    n = stored = 0u;
#ifdef __CC65__
    *(volatile unsigned char *)0x90u = 0u;
#endif
    cbm_k_talk(c->stream->device); cbm_k_tksa(0x6Fu);
    st = cbm_k_readst();
    if (!st) {
        do {
            value = cbm_k_acptr(); st = cbm_k_readst();
            if (stored < 79u) c->reply[stored++] = value;
            ++n;
        } while (!st && n != 255u);
    }
    cbm_k_untlk(); cbm_k_clrch();
    c->reply[stored] = 0u;
    return st == 0x40u ? stored : 255u;
}

static unsigned char status(ReadyFsFilesCall *c) {
    unsigned char count;
    count = receive(c);
    if (count == 255u || count < 2u ||
        c->reply[0] < '0' || c->reply[0] > '9' ||
        c->reply[1] < '0' || c->reply[1] > '9') return error(c);
    c->dos = (c->reply[0] - '0') * 10u + c->reply[1] - '0';
    return RF_LOOKUP_FOUND;
}

static unsigned char send(ReadyFsFilesCall *c, const unsigned char *bytes, unsigned char count) {
    unsigned char i, st;
#ifdef __CC65__
    *(volatile unsigned char *)0x90u = 0u;
#endif
    cbm_k_listen(c->stream->device); cbm_k_second(0x6Fu);
    for (i = 0u; i < count; ++i) cbm_k_ciout(bytes[i]);
    cbm_k_unlsn(); st = cbm_k_readst(); cbm_k_clrch();
    return !st;
}

static unsigned char command(ReadyFsFilesCall *c) {
    if (c->stream->path.endpoint == RF_EP_SOFTIEC) {
        /* Preserve SoftwareIEC's established standalone SCRATCH transaction.
         * Its caller verifies source disappearance with logical-type probes. */
        if (cbm_open(15u, c->stream->device, 15u, (char *)c->request)) return error(c);
        cbm_close(15u); cbm_k_clrch(); return RF_LOOKUP_FOUND;
    }
    if (!send(c, (const unsigned char *)c->request, strlen(c->request))) return error(c);
    if (status(c) == RF_LOOKUP_ERROR) return RF_LOOKUP_ERROR;
    if (c->dos != (c->operation == RF_FILES_SCRATCH ? 1u : 0u)) return error(c);
    return RF_LOOKUP_FOUND;
}

static unsigned char open_file(ReadyFsFilesCall *c) {
    ReadyFsStream *s;
    unsigned char len, rc;
    s = c->stream;
    if (s->type < CBM_T_SEQ || s->type > CBM_T_USR) {
        *c->status = RF_RESULT_UNSUPPORTED;
        cputs(RF_ERROR "file type unsupported\r\n");
        return RF_LOOKUP_ERROR;
    }
    len = strlen(c->request);
    if (len > 115u) return error(c);
    c->request[len++] = ',';
    c->request[len++] = s->type == CBM_T_SEQ ? 's' : s->type == CBM_T_PRG ? 'p' : 'u';
    c->request[len++] = ',';
    c->request[len++] = c->operation == RF_FILES_OPEN_WRITE ? 'w' : 'r';
    c->request[len] = 0u;
#ifdef __CC65__
    *(volatile unsigned char *)0x90u = 0u;
#endif
    rc = cbm_open(s->lfn, s->device, s->lfn, (char *)c->request);
    cbm_k_clrch();
    if (rc) { cbm_close(s->lfn); cbm_k_clrch(); return error(c); }
    if (s->path.endpoint == RF_EP_IEC) {
        rc = status(c);
        if (rc == RF_LOOKUP_ERROR || c->dos != 0u) {
            cbm_close(s->lfn); cbm_k_clrch();
            return rc == RF_LOOKUP_ERROR ? rc : error(c);
        }
    }
    return RF_LOOKUP_FOUND;
}

static unsigned char close_file(ReadyFsFilesCall *c) {
    unsigned char st;
#ifdef __CC65__
    *(volatile unsigned char *)0x90u = 0u;
#endif
    cbm_close(c->stream->lfn); st = cbm_k_readst(); cbm_k_clrch();
    c->stream->open = 0u;
    if (st) return error(c);
    if (status(c) == RF_LOOKUP_ERROR) return RF_LOOKUP_ERROR;
    return c->dos == 0u ? RF_LOOKUP_FOUND : error(c);
}

unsigned char readyfs_files(ReadyFsFilesCall *c) {
    struct cbm_dirent entry;
    char *leaf;
    unsigned char rc, result;
    if (c->operation == RF_FILES_OPEN_READ || c->operation == RF_FILES_OPEN_WRITE) return open_file(c);
    if (c->operation == RF_FILES_CLOSE) return close_file(c);
    if (c->operation == RF_FILES_SCRATCH || c->operation == RF_FILES_RENAME) return command(c);
    if (c->operation == RF_FILES_STATUS) return status(c);
    if (c->operation != RF_FILES_FIND) return error(c);
    leaf = strrchr(c->stream->native_name, '/');
    leaf = leaf ? leaf + 1u : c->stream->native_name;
    result = RF_LOOKUP_ERROR;
    if (cbm_opendir(6u, c->stream->device, c->directory ? c->directory : (const char *)"$")) {
        cbm_closedir(6u); cbm_k_clrch(); return error(c);
    }
    for (;;) {
        rc = cbm_readdir(6u, &entry);
        if (rc != 0u) {
            if (rc == 2u) result = RF_LOOKUP_MISSING;
            break;
        }
        if (entry.type != CBM_T_HEADER &&
            readyfs_same_word(entry.name, leaf)) {
            c->stream->type = entry.type;
            strcpy(leaf, entry.name);
            result = RF_LOOKUP_FOUND;
            break;
        }
    }
    cbm_closedir(6u); cbm_k_clrch();
    if (result == RF_LOOKUP_ERROR) return error(c);
    if (status(c) == RF_LOOKUP_ERROR) return RF_LOOKUP_ERROR;
    if (c->dos != 0u) return error(c);
    if (result == RF_LOOKUP_MISSING) c->stream->type = 0u;
    return result;
}

/* Preparation runs before data channels open. Cache identity only; G-P is
 * queried for every descriptor so partition0 means the current partition. */
unsigned char readyfs_files_prepare(ReadyFsStreamCall *call) {
    ReadyFsFilesCall c;
    ReadyFsDriverCall identity;
    unsigned char record[4], query[5];
    unsigned int offset;
    c.stream = call->stream; c.reply = call->reply; c.status = call->status;
    offset = RF_REU_DRIVE_PROFILE_OFF + (unsigned int)(c.stream->device - 8u) * 4u;
    if (!readyfs_reu_session_fetch(offset, record, 4u) ||
        record[0] != 0x52u || record[1] != c.stream->device) {
        if (!send(&c, (const unsigned char *)"ui", 2u) ||
            status(&c) != RF_LOOKUP_FOUND || c.dos != 73u) goto io;
        record[0] = 0x52u; record[1] = c.stream->device;
        identity.status = (const char *)c.reply;
        if (!readyfs_files_classify(&identity)) goto io;
        record[2] = identity.kind; record[3] = identity.flags;
        if (!readyfs_reu_session_store(offset, record, 4u)) goto io;
    }
    if (record[2] != RF_DRIVER_SD2IEC) {
        if (c.stream->path.partition || strchr(c.stream->native_name, '/')) goto unsupported;
        return 1u;
    }
    query[0] = 'g'; query[1] = '-'; query[2] = 'p';
    query[3] = c.stream->path.partition; query[4] = 13u;
    if (query[3] == 255u) goto unsupported;
    if (!send(&c, query, query[3] ? 5u : 3u) || receive(&c) != 31u || c.reply[30] != 13u) goto io;
    if (!c.reply[0]) {
        *c.status = RF_RESULT_NOT_FOUND; cputs(RF_ERROR "partition absent\r\n"); return 0u;
    }
    if (!c.reply[2] || c.reply[2] == 255u || (query[3] && c.reply[2] != query[3])) goto io;
    if (c.reply[0] < 1u || c.reply[0] > 4u) goto unsupported;
    c.stream->native_mode = c.reply[0] == 1u ? RF_NATIVE_HIER : RF_NATIVE_FLAT;
    c.stream->native_partition = c.reply[2];
    return 1u;
unsupported:
    *c.status = RF_RESULT_UNSUPPORTED; cputs(RF_ERROR "native path unsupported\r\n"); return 0u;
io:
    (void)error(&c); return 0u;
}
