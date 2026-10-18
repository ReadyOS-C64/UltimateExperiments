/* Read-only $=P transport diagnostic. No paging or filesystem mutations.
 * $C100 header, $C200 raw bytes; $C1F0=$A5 completion. */
#include <cbm.h>
#include <conio.h>
#include <string.h>
#define MAIL ((unsigned char *)0xC100u)
#define DATA ((unsigned char *)0xC200u)
int main(void) {
    unsigned int n;
    int count;
    memset(MAIL, 0, 1024u);
    memcpy(MAIL, "rfs", 3u); MAIL[3] = 2u;
    clrscr(); cputs("native partition bytes\r\n");
    MAIL[4] = 1u;
    MAIL[5] = cbm_open(2u, 10u, 0u, "$=p");
    MAIL[4] = 2u;
    if (!MAIL[5]) {
        for (n = 0u; n < 768u; ++n) {
            MAIL[8] = (unsigned char)n; MAIL[9] = n >> 8;
            count = cbm_read(2u, DATA + n, 1u);
            MAIL[6] = count; MAIL[7] = cbm_k_readst();
            if (count != 1) break;
            if (MAIL[7] & 0x40u) { ++n; break; }
        }
        MAIL[8] = (unsigned char)n; MAIL[9] = n >> 8;
    }
    MAIL[4] = 3u;
    cbm_close(2u); cbm_k_clrch();
    MAIL[4] = 4u;
    cputs("count $"); cputhex8(MAIL[9]); cputhex8(MAIL[8]);
    MAIL[0xF0] = 0xA5u;
    for (;;) {}
    return 0;
}
