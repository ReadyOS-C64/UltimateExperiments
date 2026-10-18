/* Production native preparation and qualified root lookup, read-only.
 * Cache uses four local bytes for this standalone experiment. */
#include "../src/apps/readyfs/readyfs_files.c"
#include "../src/apps/readyfs/readyfs_files_plan.c"
#define MAIL ((unsigned char *)0xC100u)
static ReadyFsStream stream;
static unsigned char cache[4];
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
int main(void) {
    ReadyFsStreamCall prep;
    ReadyFsFilesCall file;
    memset(MAIL, 0, 1024u); memcpy(MAIL, "rfs", 3u); MAIL[3] = 5u;
    clrscr(); cputs("native production file preparation\r\n");
    stream.device = 10u; stream.path.endpoint = RF_EP_IEC;
    strcpy(stream.canonical, "rfprobe-absent"); stream.native_name = stream.canonical;
    prep.stream = &stream; prep.status = MAIL + 6u; prep.reply = MAIL + 256u;
    MAIL[4] = 1u; MAIL[5] = readyfs_files_prepare(&prep);
    MAIL[7] = stream.native_mode; MAIL[8] = stream.native_partition;
    memcpy(MAIL + 512u, prep.reply, 31u);
    if (MAIL[5]) {
        stream.path.partition = stream.native_partition;
        MAIL[4] = 2u; MAIL[9] = readyfs_files_prepare(&prep);
        memset(&file, 0, sizeof(file)); file.stream = &stream;
        file.status = MAIL + 6u; file.reply = MAIL + 256u;
        file.request = (char *)MAIL + 384u; file.operation = RF_FILES_FIND;
        MAIL[4] = 3u; MAIL[10] = readyfs_files_plan(&file);
        if (MAIL[10] == RF_LOOKUP_FOUND) {
            MAIL[4] = 4u; MAIL[11] = readyfs_files(&file);
            MAIL[12] = file.dos;
        }
    }
    MAIL[4] = 5u; cputs("done\r\n"); MAIL[0xF0] = 0xA5u;
    for (;;) {}
    return 0;
}
