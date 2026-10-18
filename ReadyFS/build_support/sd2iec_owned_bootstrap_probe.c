/* Native owned-test bootstrap. Refuses an existing root, never replaces files.
 * The runner supplies a unique, <=16-byte component and per-run marker.
 * Leaves partition at FAT root; unknown previous SD cwd is not restorable. */
#include "../src/apps/readyfs/readyfs_files.c"
#include "../src/apps/readyfs/readyfs_files_plan.c"
#include <stdio.h>
#include "sd2iec_owned_run.h"
#define MAIL ((unsigned char *)0xC100u)
static ReadyFsStream stream;
static ReadyFsStreamCall prep;
static ReadyFsFilesCall file;
static unsigned char cache[4], payload[64];
static const char marker[] = RF_TEST_MARKER;
unsigned char readyfs_reu_session_fetch(unsigned int off, void *data, unsigned int size) {
    (void)off; memcpy(data, cache, size); return 1u;
}
unsigned char readyfs_reu_session_store(unsigned int off, const void *data, unsigned int size) {
    (void)off; memcpy(cache, data, size); return 1u;
}
unsigned char readyfs_same_word(const char *a, const char *b) {
    while (*a && *b) if (folded(*a++) != folded(*b++)) return 0u;
    return !*a && !*b;
}
static unsigned char invoke(unsigned char op) {
    file.operation = op;
    if (readyfs_files_plan(&file) != RF_LOOKUP_FOUND) return RF_LOOKUP_ERROR;
    return readyfs_files(&file);
}
static unsigned char dos(void) {
    if (!send(&file, (const unsigned char *)file.request, strlen(file.request)) ||
        status(&file) != RF_LOOKUP_FOUND) return 255u;
    MAIL[16u + MAIL[4]] = file.dos;
    return file.dos;
}
static void name(const char *leaf) {
    strcpy(stream.canonical, RF_TEST_ROOT);
    if (leaf) { strcat(stream.canonical, "/"); strcat(stream.canonical, leaf); }
    stream.type = CBM_T_SEQ;
}
static unsigned char open_new(const char *leaf, unsigned char type) {
    name(leaf);
    if (invoke(RF_FILES_FIND) != RF_LOOKUP_MISSING) return 0u;
    stream.type = type;
    MAIL[80] = invoke(RF_FILES_OPEN_WRITE);
    strcpy((char *)MAIL + 768u, file.request);
    MAIL[81] = stream.device; MAIL[82] = stream.lfn; MAIL[83] = stream.type;
    MAIL[84] = stream.native_mode; MAIL[85] = stream.native_partition;
    return MAIL[80] == RF_LOOKUP_FOUND;
}
static unsigned char owner(void) {
    unsigned int count, used;
    unsigned char ok;
    name("owner");
    MAIL[64] = invoke(RF_FILES_FIND); MAIL[65] = stream.type; MAIL[66] = stream.native_mode;
    if (MAIL[64] != RF_LOOKUP_FOUND || stream.type != CBM_T_SEQ) return 0u;
    MAIL[67] = invoke(RF_FILES_OPEN_READ); MAIL[68] = stream.native_mode;
    if (MAIL[67] != RF_LOOKUP_FOUND) return 0u;
    used = 0u; ok = 1u;
    for (;;) {
        count = cbm_read(stream.lfn, payload, sizeof(payload));
        if (count > sizeof(payload) || used + count > sizeof(marker)-1u ||
            memcmp(payload, marker + used, count)) { ok = 0u; break; }
        MAIL[69] = count; MAIL[70] = cbm_k_readst();
        memcpy(MAIL + 640u + used, payload, count);
        used += count;
        if (cbm_k_readst() == 0x40u) break;
        if (!count || cbm_k_readst()) { ok = 0u; break; }
    }
    MAIL[71] = invoke(RF_FILES_CLOSE); MAIL[72] = stream.native_mode;
    if (MAIL[71] != RF_LOOKUP_FOUND) return 0u;
    return ok && used == sizeof(marker)-1u;
}
static unsigned char mkdir_owned(const char *leaf) {
    if (!owner()) return 0u;
    name(leaf);
    if (invoke(RF_FILES_FIND) != RF_LOOKUP_MISSING) return 0u;
    sprintf(file.request, "md%u//" RF_TEST_ROOT "/:%s", stream.native_partition, leaf);
    return dos() == 0u;
}
static unsigned char seed(void) {
    unsigned int i;
    unsigned char n;
    if (!owner() || !open_new("in/seed", CBM_T_SEQ)) return 0u;
    for (i = 0u; i < 1025u;) {
        for (n = 0u; n < sizeof(payload) && i < 1025u; ++n, ++i)
            payload[n] = (unsigned char)(i * 37u + 11u);
        *(volatile unsigned char *)0x90u = 0u;
        if (cbm_write(stream.lfn, payload, n) != n) {
            (void)invoke(RF_FILES_CLOSE); return 0u;
        }
    }
    return invoke(RF_FILES_CLOSE) == RF_LOOKUP_FOUND;
}
static unsigned char verify_seed(void) {
    unsigned int i, count;
    unsigned char n, ok;
    name("in/seed");
    if (invoke(RF_FILES_FIND) != RF_LOOKUP_FOUND || stream.type != CBM_T_SEQ ||
        invoke(RF_FILES_OPEN_READ) != RF_LOOKUP_FOUND) return 0u;
    i = 0u; ok = 1u;
    for (;;) {
        count = cbm_read(stream.lfn, payload, sizeof(payload));
        if (count > sizeof(payload) || i + count > 1025u) { ok = 0u; break; }
        for (n = 0u; n < count; ++n, ++i)
            if (payload[n] != (unsigned char)(i * 37u + 11u)) ok = 0u;
        if (cbm_k_readst() == 0x40u) break;
        if (!count || cbm_k_readst()) { ok = 0u; break; }
    }
    if (invoke(RF_FILES_CLOSE) != RF_LOOKUP_FOUND) return 0u;
    MAIL[13] = (unsigned char)i; MAIL[14] = (unsigned char)(i >> 8);
    return ok && i == 1025u;
}
int main(void) {
    unsigned char rc;
    memset(MAIL, 0, 1024u); memcpy(MAIL, "rfs", 3u); MAIL[3] = 6u;
    clrscr(); cputs("native owned-test bootstrap\r\n");
    stream.device = 10u; stream.lfn = 7u; stream.path.endpoint = RF_EP_IEC;
    name(0); stream.native_name = stream.canonical;
    prep.stream = &stream; prep.status = MAIL + 6u; prep.reply = MAIL + 256u;
    file.stream = &stream; file.status = prep.status; file.reply = prep.reply;
    file.request = (char *)MAIL + 384u;
    MAIL[4] = 1u;
    if (!readyfs_files_prepare(&prep) ||
        (stream.native_mode != RF_NATIVE_HIER && stream.native_mode != RF_NATIVE_FLAT) ||
        !stream.native_partition || stream.native_partition == 255u) goto done;
    stream.path.partition = stream.native_partition; MAIL[8] = stream.native_partition;
    memcpy(MAIL + 512u, prep.reply, 31u);
    /* No data channel exists. Root DNP before BACK; flat images need only BACK.
     * FAT-root BACK may report33/62. A failed image close changes to FAT too,
     * but all other statuses still fail closed here. */
    MAIL[4] = 2u;
    if (stream.native_mode == RF_NATIVE_HIER) {
        sprintf(file.request, "cd%u//", stream.native_partition);
        if (dos()) goto done;
    }
    MAIL[4] = 3u;
    sprintf(file.request, "cd%u:%c", stream.native_partition, 0x5F);
    rc = dos(); if (rc != 0u && rc != 33u && rc != 62u) goto done;
    MAIL[4] = 4u;
    sprintf(file.request, "cd%u//", stream.native_partition);
    if (dos() || !readyfs_files_prepare(&prep) || stream.native_mode != RF_NATIVE_HIER) goto done;
    memcpy(MAIL + 544u, prep.reply, 31u);
    MAIL[4] = 5u; name(0);
    if (invoke(RF_FILES_FIND) != RF_LOOKUP_MISSING) goto done;
    MAIL[4] = 6u;
    sprintf(file.request, "md%u//:" RF_TEST_ROOT, stream.native_partition);
    if (dos()) goto done;
    MAIL[4] = 7u;
    if (!open_new("owner", CBM_T_SEQ)) goto done;
    *(volatile unsigned char *)0x90u = 0u;
    rc = cbm_write(stream.lfn, marker, sizeof(marker)-1u) == sizeof(marker)-1u;
    MAIL[86] = rc; MAIL[87] = cbm_k_readst(); MAIL[88] = stream.native_mode;
    if (invoke(RF_FILES_CLOSE) != RF_LOOKUP_FOUND || !rc) goto done;
    MAIL[4] = 8u; if (!owner()) goto done;
    MAIL[4] = 9u; if (!mkdir_owned("in")) goto done;
    MAIL[4] = 10u; if (!mkdir_owned("out")) goto done;
    MAIL[4] = 11u; if (!mkdir_owned("tree")) goto done;
    /* Nested MD uses qualified parent; never sends a slash inside the leaf. */
    MAIL[4] = 12u; if (!owner()) goto done;
    name("tree/inner"); if (invoke(RF_FILES_FIND) != RF_LOOKUP_MISSING) goto done;
    sprintf(file.request, "md%u//" RF_TEST_ROOT "/tree/:inner", stream.native_partition);
    if (dos()) goto done;
    MAIL[4] = 13u; if (!seed()) goto done;
    MAIL[4] = 14u; if (!verify_seed()) goto done;
    MAIL[4] = 15u; if (!owner()) goto done;
    MAIL[5] = 1u;
done:
    MAIL[7] = stream.native_mode; cputs(MAIL[5] ? "passed\r\n" : "stopped\r\n");
    MAIL[0xF0] = 0xA5u;
    for (;;) {}
    return 0;
}
