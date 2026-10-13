/* Native, read-only IEC diagnostic. No UCI/network or filesystem writes.
 * Results remain at $C100; $C1F0=$A5 means complete. */
#include <cbm.h>
#include <conio.h>
#include <string.h>

#define MAIL ((unsigned char *)0xC100u)

static int query(unsigned char device, const char *command, unsigned char *buffer, unsigned char size) {
    unsigned char opened;
    int count;
    opened = cbm_open(15u, device, 15u, command);
    if (device == 10u) MAIL[0x10] = opened;
    if (opened) { cbm_close(15u); cbm_k_clrch(); return -1; }
    count = cbm_read(15u, buffer, size);
    cbm_close(15u); cbm_k_clrch();
    return count;
}

static unsigned char fold(unsigned char value) {
    value &= 0x7Fu;
    if (value >= 0x61u && value <= 0x7Au) value -= 0x20u;
    return value;
}

static unsigned char contains(const char *text, const char *word) {
    unsigned char i;
    while (*text) {
        for (i = 0u; word[i] && text[i] && fold(text[i]) == fold(word[i]); ++i) {}
        if (!word[i]) return 1u;
        ++text;
    }
    return 0u;
}

int main(void) {
    unsigned char i;
    unsigned char units[4] = {8u, 9u, 10u, 11u};
    char partition_one[5];
    int count;
    unsigned char *record;
    memset(MAIL, 0, 768u);
    MAIL[0] = 0x52u; MAIL[1] = 0x46u; MAIL[2] = 0x53u; MAIL[3] = 1u;
    clrscr(); cputs("sd2iec native read-only probe\r\n");
    for (i = 0u; i < 4u; ++i) {
        *(unsigned char *)0x90u = 0u;
        cbm_k_listen(units[i]); cbm_k_second(0x6Fu);
        MAIL[8u+i] = cbm_k_readst();
        cbm_k_unlsn(); cbm_k_clrch();
        cputc('0' + units[i] / 10u); cputc('0' + units[i] % 10u);
        cputs(" listen status $"); cputhex8(MAIL[8u+i]); cputs("\r\n");
    }
    count = query(10u, "ui", MAIL + 0x20u, 63u);
    MAIL[0x11] = count < 0 ? 255u : (unsigned char)count;
    cputs("ui open $"); cputhex8(MAIL[0x10]); cputs("\r\n");
    if (count >= 0) {
        MAIL[0x20u + count] = 0u;
        cputs((char *)MAIL + 0x20u); cputs("\r\n");
        if (contains((char *)MAIL + 0x20u, "sd2iec") ||
            contains((char *)MAIL + 0x20u, "uiec")) {
            MAIL[0x12] = (unsigned char)query(10u, "g-p", MAIL + 0x80u, 31u);
            strcpy(partition_one, "g-p"); partition_one[3] = 1u;
            partition_one[4] = 0;
            MAIL[0x13] = (unsigned char)query(10u, partition_one, MAIL + 0xA0u, 31u);
            cputs("g-p current/type $"); cputhex8(MAIL[0x82]);
            cputc('/'); cputhex8(MAIL[0x80]); cputs("\r\n");
            cputs("partition 1 type $"); cputhex8(MAIL[0xA0]); cputs("\r\n");
        }
    }
    cputs("read-only identities 8-15\r\n");
    for (i = 8u; i <= 15u; ++i) {
        record = MAIL + 256u + (unsigned int)(i - 8u) * 48u;
        record[0] = i;
        if (i == 10u) {
            record[1] = MAIL[0x11];
            memcpy(record + 2u, MAIL + 0x20u, 45u);
        } else {
            count = query(i, i == 8u ? "" : "ui", record + 2u, 45u);
            record[1] = count < 0 ? 255u : (unsigned char)count;
            if (count >= 0) record[2u+count] = 0u;
        }
        cputc('0' + i / 10u); cputc('0' + i % 10u); cputc(' ');
        if (record[1] != 255u) cputs((char *)record + 2u);
        else cputs("no command channel");
        cputs("\r\n");
    }
    cputs("done; no media changes\r\n");
    MAIL[0xF0] = 0xA5u;
    for (;;) {}
    return 0;
}
