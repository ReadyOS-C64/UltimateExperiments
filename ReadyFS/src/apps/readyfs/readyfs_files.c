/* Native IEC leaf I/O. No native CLOSE15, overlay loads, UCI or network. */
#include "readyfs_files.h"
#include "readyfs_result.h"
#include "readyfs_console.h"
#include <cbm.h>
#include <cbm_filetype.h>
#include <conio.h>
#include <string.h>
extern unsigned char readyfs_same_word(const char *, const char *);
unsigned int readyfs_files_abi(void) { return RF_FILES_ABI; }

static unsigned char error(ReadyFsFilesCall *c) {
    *c->status = RF_RESULT_IO;
    cputs(RF_ERROR "iec operation failed\r\n");
    return RF_LOOKUP_ERROR;
}

/* TALK the always-present DOS channel directly. OPEN/CLOSE15 would destroy
 * live SD2IEC data buffers, including a copy's source on the same device. */
static unsigned char status(ReadyFsFilesCall *c) {
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
    if (st != 0x40u || stored < 2u ||
        c->reply[0] < '0' || c->reply[0] > '9' ||
        c->reply[1] < '0' || c->reply[1] > '9') return error(c);
    c->dos = (c->reply[0] - '0') * 10u + c->reply[1] - '0';
    return RF_LOOKUP_FOUND;
}

static unsigned char command(ReadyFsFilesCall *c) {
    unsigned char n, st;
    const char *name;
    name = c->stream->native_name;
    if (strlen(name) + (c->operation == RF_FILES_RENAME ?
        strlen(c->other->native_name) : 0u) + 4u > 119u) return error(c);
    strcpy((char *)c->reply, c->operation == RF_FILES_RENAME ? "r:" : "s:");
    if (c->operation == RF_FILES_RENAME) {
        strcat((char *)c->reply, c->other->native_name);
        strcat((char *)c->reply, "=");
    }
    strcat((char *)c->reply, name);
    if (c->stream->path.endpoint == RF_EP_SOFTIEC) {
        /* Preserve SoftwareIEC's established standalone SCRATCH transaction.
         * Its caller verifies source disappearance with logical-type probes. */
        if (cbm_open(15u, c->stream->device, 15u, (char *)c->reply)) return error(c);
        cbm_close(15u); cbm_k_clrch(); return RF_LOOKUP_FOUND;
    }
#ifdef __CC65__
    *(volatile unsigned char *)0x90u = 0u;
#endif
    cbm_k_listen(c->stream->device); cbm_k_second(0x6Fu);
    for (n = 0u; c->reply[n]; ++n) cbm_k_ciout(c->reply[n]);
    cbm_k_unlsn(); st = cbm_k_readst(); cbm_k_clrch();
    if (st) return error(c);
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
    if (strlen(s->native_name) + 4u > 119u) return error(c);
    strcpy((char *)c->reply, s->native_name); len = strlen((char *)c->reply);
    c->reply[len++] = ',';
    c->reply[len++] = s->type == CBM_T_SEQ ? 's' : s->type == CBM_T_PRG ? 'p' : 'u';
    c->reply[len++] = ',';
    c->reply[len++] = c->operation == RF_FILES_OPEN_WRITE ? 'w' : 'r';
    c->reply[len] = 0u;
#ifdef __CC65__
    *(volatile unsigned char *)0x90u = 0u;
#endif
    rc = cbm_open(s->lfn, s->device, s->lfn, (char *)c->reply);
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
    unsigned char rc, result;
    if (c->operation == RF_FILES_OPEN_READ || c->operation == RF_FILES_OPEN_WRITE) return open_file(c);
    if (c->operation == RF_FILES_CLOSE) return close_file(c);
    if (c->operation == RF_FILES_SCRATCH || c->operation == RF_FILES_RENAME) return command(c);
    if (c->operation == RF_FILES_STATUS) return status(c);
    if (c->operation != RF_FILES_FIND) return error(c);
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
            readyfs_same_word(entry.name, c->stream->native_name)) {
            c->stream->type = entry.type;
            strcpy(c->stream->native_name, entry.name);
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
