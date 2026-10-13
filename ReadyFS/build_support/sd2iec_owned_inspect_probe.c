/* Read-only inspection of a retained partial owned bootstrap. */
#define main bootstrap_main
#include "sd2iec_owned_bootstrap_probe.c"
#undef main
int main(void) {
    unsigned int n;
    int count;
    memset(MAIL, 0, 1024u); memcpy(MAIL, "rfs", 3u); MAIL[3] = 7u;
    stream.device = 10u; stream.lfn = 7u; stream.path.endpoint = RF_EP_IEC;
    name(0); stream.native_name = stream.canonical;
    prep.stream = &stream; prep.status = MAIL + 6u; prep.reply = MAIL + 256u;
    file.stream = &stream; file.status = prep.status; file.reply = prep.reply;
    file.request = (char *)MAIL + 384u;
    MAIL[4] = 1u;
    if (readyfs_files_prepare(&prep)) {
        MAIL[4] = 2u;
        MAIL[5] = owner();
    }
    MAIL[7] = stream.native_mode;
    name("owner"); file.operation = RF_FILES_FIND;
    (void)readyfs_files_plan(&file);
    *(volatile unsigned char *)0x90u = 0u;
    MAIL[80] = cbm_open(2u, 10u, 0u, file.request);
    if (!MAIL[80]) {
        *(volatile unsigned char *)0x90u = 0u;
        for (n = 0u; n < 480u; ++n) {
            count = cbm_read(2u, MAIL + 512u + n, 1u);
            MAIL[83] = count; MAIL[84] = cbm_k_readst();
            if (count != 1) break;
            if (cbm_k_readst()) { ++n; break; }
        }
        MAIL[81] = n; MAIL[82] = n >> 8;
    }
    cbm_close(2u); cbm_k_clrch();
    MAIL[0xF0] = 0xA5u;
    for (;;) {}
    return 0;
}
