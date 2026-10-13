/* Isolate the production partition parser on real hardware, without overlays.
 * Same mailbox convention as sd2iec_partitions_probe; read-only. */
#include "../src/apps/readyfs/readyfs_iec.c"
#define MAIL ((unsigned char *)0xC100u)
void readyfs_media_reset(void) {}
unsigned char readyfs_reu_session_store(unsigned int off, const void *data, unsigned int size) {
    (void)off; (void)data; (void)size; return 1u;
}
unsigned char readyfs_reu_batch_store(unsigned int off, const void *data, unsigned int size) {
    (void)off; (void)data; (void)size; return 1u;
}
int main(void) {
    ReadyFsIecCall call;
    memset(MAIL, 0, 1024u); memcpy(MAIL, "rfs", 3u); MAIL[3] = 3u;
    memset(&call, 0, sizeof(call));
    call.device = 10u; call.operation = RF_IEC_PARTITIONS;
    call.flags = RF_IEC_SD_ONLY;
    call.reply = MAIL + 256u; call.status = MAIL + 6u;
    clrscr(); cputs("native production parser\r\n");
    MAIL[4] = 1u; MAIL[5] = readyfs_iec_execute(&call); MAIL[4] = 4u;
    cputs("done\r\n"); MAIL[0xF0] = 0xA5u;
    for (;;) {}
    return 0;
}
