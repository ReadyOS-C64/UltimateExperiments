/* Pure request formatter in slot20. No I/O and no nested overlay calls. */
#include "readyfs_files.h"
#include "readyfs_result.h"
#include "readyfs_console.h"
#include <string.h>
#include <conio.h>
#include <cbm_filetype.h>

unsigned int readyfs_files_plan_abi(void) { return RF_FILES_PLAN_ABI; }

static unsigned char reject(ReadyFsFilesCall *c) {
    *c->status = RF_RESULT_UNSUPPORTED;
    cputs(RF_ERROR "native path unsupported\r\n");
    return RF_LOOKUP_ERROR;
}

static unsigned char add(char *out, const char *text, unsigned int n) {
    unsigned int used;
    used = strlen(out);
    if (used + n > 119u) return 0u;
    memcpy(out + used, text, n); out[used + n] = 0;
    return 1u;
}

static unsigned char partition(char *out, unsigned char p) {
    char digits[3];
    unsigned char n;
    n = 0u;
    if (p >= 100u) digits[n++] = '0' + p / 100u;
    if (p >= 10u) digits[n++] = '0' + (p / 10u) % 10u;
    digits[n++] = '0' + p % 10u;
    return add(out, digits, n);
}

static unsigned char valid(const ReadyFsStream *s) {
    const char *p;
    unsigned char length;
    length = 0u;
    if (!s->native_mode && (*s->native_name == '$' || *s->native_name == '#')) return 0u;
    for (p = s->native_name; *p; ++p) {
        if (!length && *p == '.' && (!p[1] || p[1] == '/' ||
            (p[1] == '.' && (!p[2] || p[2] == '/')))) return 0u;
        if (*p == '/') {
            if (s->native_mode != RF_NATIVE_HIER || !length) return 0u;
            length = 0u;
        } else {
            if ((unsigned char)*p < 32u || strchr(":,=*?!@", *p) ||
                ++length > (s->path.endpoint == RF_EP_SOFTIEC ? 115u : 16u)) return 0u;
        }
    }
    return length != 0u;
}

static unsigned char reference(char *out, const ReadyFsStream *s,
                                unsigned char directory) {
    const char *leaf;
    unsigned int parent;
    if (!valid(s)) return 0u;
    if (directory && !add(out, "$", 1u)) return 0u;
    if (!s->native_mode)
        return directory || add(out, s->native_name, strlen(s->native_name));
    if (!s->native_partition || s->native_partition == 255u ||
        !partition(out, s->native_partition)) return 0u;
    if (s->native_mode == RF_NATIVE_HIER) {
        if (!add(out, "//", 2u)) return 0u;
        leaf = strrchr(s->native_name, '/');
        parent = leaf ? (unsigned int)(leaf + 1u - s->native_name) : 0u;
        if (!add(out, s->native_name, parent)) return 0u;
        leaf = s->native_name + parent;
    } else if (s->native_mode == RF_NATIVE_FLAT) leaf = s->native_name;
    else return 0u;
    /* A colon enables path parsing; an explicit star matches all entries.
     * Empty patterns match no nonempty filename in the SD2IEC firmware. */
    if (directory) return add(out, ":*", 2u);
    return add(out, ":", 1u) && add(out, leaf, strlen(leaf));
}

static unsigned char same_parent(const ReadyFsStream *a, const ReadyFsStream *b) {
    const char *x, *y;
    unsigned int n, i;
    unsigned char left, right;
    x = strrchr(a->native_name, '/'); y = strrchr(b->native_name, '/');
    if (!x || !y) return x == y;
    n = (unsigned int)(x - a->native_name);
    if (n != (unsigned int)(y - b->native_name)) return 0u;
    for (i = 0u; i < n; ++i) {
        left = (unsigned char)a->native_name[i] & 0x7Fu;
        right = (unsigned char)b->native_name[i] & 0x7Fu;
        if (left >= 97u && left <= 122u) left -= 32u;
        if (right >= 97u && right <= 122u) right -= 32u;
        if (left != right) return 0u;
    }
    return 1u;
}

/* SD2IEC RD rejects every slash. Enter the qualified parent first, then
 * RD only the partition-qualified leaf. Both commands stay in resident data.
 * This standalone operation changes the device cwd; never use with live files. */
static unsigned char rmdir_plan(ReadyFsFilesCall *c) {
    char leaf[17];
    char *colon, *next;
    unsigned char used;
    if (!reference(c->request, c->stream, 0u)) return 0u;
    colon = strrchr(c->request, ':');
    strcpy(leaf, colon + 1u); *colon = 0;
    used = strlen(c->request);
    if ((unsigned int)used + strlen(leaf) + 10u > 119u) return 0u;
    memmove(c->request + 2u, c->request, used + 1u);
    memcpy(c->request, "cd", 2u);
    next = c->request + used + 3u; c->directory = next; *next = 0;
    return add(next, "rd", 2u) && partition(next, c->stream->native_partition) &&
           add(next, ":", 1u) && add(next, leaf, strlen(leaf));
}

static unsigned char udos_type(const unsigned char *data) {
    unsigned char ext[3], i;
    for (i = 0u; i < 3u; ++i) {
        ext[i] = data[8u + i] & 0x7Fu;
        if (ext[i] >= 97u && ext[i] <= 122u) ext[i] -= 32u;
    }
    if (ext[0] == 80u && ext[1] == 82u && ext[2] == 71u) return CBM_T_PRG;
    if (ext[0] == 85u && ext[1] == 83u && ext[2] == 82u) return CBM_T_USR;
    if (ext[0] == 82u && ext[1] == 69u && ext[2] == 76u) return CBM_T_REL;
    return CBM_T_SEQ;
}

unsigned char readyfs_files_plan(ReadyFsFilesCall *c) {
    unsigned char ok;
    if (c->operation == RF_FILES_UDOS_TYPE) return udos_type(c->reply);
    if (c->operation == RF_FILES_STATUS || c->operation == RF_FILES_CLOSE)
        return RF_LOOKUP_FOUND;
    c->request[0] = 0;
    c->directory = 0;
    if (c->operation == RF_FILES_MKDIR || c->operation == RF_FILES_RMDIR) {
        if (c->stream->native_mode != RF_NATIVE_HIER) return reject(c);
        if (c->operation == RF_FILES_RMDIR) ok = rmdir_plan(c);
        else ok = add(c->request, "md", 2u) && reference(c->request, c->stream, 0u);
    } else if (c->operation == RF_FILES_FIND) {
        ok = reference(c->request, c->stream, 1u);
        c->directory = c->request;
    } else if (c->operation == RF_FILES_SCRATCH) {
        ok = add(c->request, "s", 1u);
        if (!c->stream->native_mode) ok = ok && add(c->request, ":", 1u);
        ok = ok && reference(c->request, c->stream, 0u);
    } else if (c->operation == RF_FILES_RENAME) {
        if (c->stream->device != c->other->device ||
            c->stream->native_mode != c->other->native_mode ||
            c->stream->native_partition != c->other->native_partition ||
            !same_parent(c->stream, c->other))
            return reject(c);
        ok = add(c->request, "r", 1u);
        if (!c->stream->native_mode) ok = ok && add(c->request, ":", 1u);
        ok = ok && reference(c->request, c->other, 0u) &&
             add(c->request, "=", 1u) && reference(c->request, c->stream, 0u);
    } else if (c->operation == RF_FILES_OPEN_READ || c->operation == RF_FILES_OPEN_WRITE) {
        ok = reference(c->request, c->stream, 0u);
        if (strlen(c->request) > 115u) ok = 0u; /* ,T,M suffix */
    } else return reject(c);
    return ok ? RF_LOOKUP_FOUND : reject(c);
}
