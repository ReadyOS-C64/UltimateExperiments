/* Read DOS status without OPEN/CLOSE15 while a directory data channel is live.
 * Pure read-only proof of the channel lifetime required by native file copy. */
#include <cbm.h>
#include <conio.h>
#include <string.h>
#define MAIL ((unsigned char *)0xC100u)
#define DATA ((unsigned char *)0xC200u)
int main(void) {
    unsigned char n, st;
    int got;
    memset(MAIL, 0, 1024u); memcpy(MAIL, "rfs", 3u); MAIL[3] = 4u;
    clrscr(); cputs("native live channel status\r\n");
    MAIL[4] = 1u; MAIL[5] = cbm_open(2u, 10u, 0u, "$=p");
    if (!MAIL[5]) {
        MAIL[4] = 2u;
        got = cbm_read(2u, DATA, 6u); MAIL[6] = got;
        MAIL[4] = 3u;
        *(volatile unsigned char *)0x90u = 0u;
        cbm_k_talk(10u); cbm_k_tksa(0x6Fu);
        for (n = 0u; n < 79u; ++n) {
            MAIL[32u+n] = cbm_k_acptr(); st = cbm_k_readst();
            if (st) { ++n; break; }
        }
        MAIL[7] = st; MAIL[8] = n;
        cbm_k_untlk(); cbm_k_clrch();
        MAIL[4] = 4u;
        got = cbm_read(2u, DATA + 6u, 250u);
        MAIL[9] = got; MAIL[10] = got >> 8;
        MAIL[11] = cbm_k_readst();
    }
    MAIL[4] = 5u; cbm_close(2u); cbm_k_clrch(); MAIL[4] = 6u;
    cputs("read before/after $"); cputhex8(MAIL[6]); cputc('/'); cputhex8(MAIL[9]);
    MAIL[0xF0] = 0xA5u;
    for (;;) {}
    return 0;
}
