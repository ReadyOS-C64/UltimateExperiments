/* User-authorized address repair, only after positive SD2IEC identification.
 * Run with Ultimate drive A disabled and CPU at 1 MHz. No filesystem writes.
 * Mailbox stage: 1=identified8, 2=identified10, 3=XW accepted,
 * 4=identified10 after native hard restart. */
#include <cbm.h>
#include <conio.h>
#include <string.h>
#define MAIL ((unsigned char *)0xC100u)

static int query(unsigned char device, const char *command, unsigned char *buffer) {
    int count;
    if (cbm_open(15u, device, 15u, command)) {
        cbm_close(15u); cbm_k_clrch(); return -1;
    }
    count = cbm_read(15u, buffer, 63u);
    cbm_close(15u); cbm_k_clrch();
    if (count >= 0) buffer[count] = 0u;
    return count;
}
static unsigned char fold(unsigned char value) {
    value &= 0x7Fu;
    if (value >= 0x61u && value <= 0x7Au) value -= 0x20u;
    return value;
}
static unsigned char sd2iec(const unsigned char *text) {
    const unsigned char *start;
    const char *word;
    unsigned char n, i;
    for (n=0u; n<2u; ++n) {
        word = n ? "uiec" : "sd2iec";
        for (start=text; *start; ++start) {
            for (i=0u; word[i] && start[i] && fold(start[i])==fold(word[i]); ++i) {}
            if (!word[i]) return 1u;
        }
    }
    return 0u;
}
int main(void) {
    char address[5], restart[3];
    unsigned char attempts;
    int count;
    memset(MAIL,0,256u);
    MAIL[0]=0x52u;MAIL[1]=0x46u;MAIL[2]=0x41u;MAIL[3]=1u;
    clrscr();cputs("sd2iec address repair\r\n");
    count=query(8u,"ui",MAIL+0x20u);
    if (count<0 || !sd2iec(MAIL+0x20u)) goto done;
    MAIL[4]=1u;cputs((char *)MAIL+0x20u);cputs("\r\n");
    strcpy(address,"u0>.");address[3]=10;
    (void)cbm_open(15u,8u,15u,address);
    cbm_close(15u);cbm_k_clrch();
    count=query(10u,"ui",MAIL+0x60u);
    if (count<0 || !sd2iec(MAIL+0x60u)) goto done;
    MAIL[4]=2u;cputs("verified at 10\r\n");
    count=query(10u,"xw",MAIL+0xA0u);
    if (count<2 || MAIL[0xA0]!='0' ||
        (MAIL[0xA1]!='0' && MAIL[0xA1]!='3')) goto done;
    MAIL[4]=3u;cputs("configuration saved\r\n");
    restart[0]='u';restart[1]=(char)202u;restart[2]=0;
    (void)cbm_open(15u,10u,15u,restart);
    cbm_close(15u);cbm_k_clrch();
    for (attempts=0u;attempts<32u;++attempts) {
        count=query(10u,"ui",MAIL+0x60u);
        if (count>=0 && sd2iec(MAIL+0x60u)) {
            MAIL[4]=4u;cputs("still 10 after hard restart\r\n");break;
        }
    }
done:
    cputs("stage ");cputhex8(MAIL[4]);cputs("\r\ndone\r\n");
    MAIL[0xF0]=0xA5u;
    for (;;) {}
    return 0;
}
