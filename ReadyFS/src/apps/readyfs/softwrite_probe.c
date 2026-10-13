#include <cbm.h>
#include <conio.h>
#include <string.h>

#define DEVICE 11u
#ifndef SOFTWRITE_DIR
#define SOFTWRITE_DIR "rf065128"
#endif
#ifndef SOFTWRITE_LEAF
#define SOFTWRITE_LEAF "kp065128"
#endif

static char status_text[40];

static int status_read(const char *command) {
    int count;
    if (cbm_open(15u, DEVICE, 15u, command) != 0u) return -1;
    count = cbm_read(15u, status_text, sizeof(status_text) - 1u);
    cbm_close(15u);
    cbm_k_clrch();
    if (count >= 0) status_text[count] = 0;
    return count;
}

static unsigned char command_ok(const char *command) {
    int count;
    (void)status_read("");
    count = status_read(command);
    return (unsigned char)(count >= 2 && status_text[0] == '0' &&
                                         status_text[1] == '0');
}

static unsigned char enter_owned(void) {
    char test_command[16];
    if (!command_ok("cd:/") || !command_ok("cd:usb1")) return 0u;
    strcpy(test_command, "cd:readyfs.test");
    test_command[10] = 0x5Fu;
    return (unsigned char)(command_ok(test_command) &&
        command_ok("cd:readyfs-20260815-190355-79014") &&
        command_ok("cd:" SOFTWRITE_DIR));
}

static void print_status(void) {
    if (status_text[0] != 0 && status_text[1] != 0) {
        cputc(status_text[0]); cputc(status_text[1]);
    } else cputs("IO");
}

int main(void) {
    static const char name[] = SOFTWRITE_LEAF ",s,w";
    char readback[8];
    int count;
    unsigned char opened;

    bordercolor(COLOR_BLUE);
    bgcolor(COLOR_BLUE);
    textcolor(COLOR_WHITE);
    clrscr();
    cputs("SOFTWRITE OWNED PROBE\r\n");
    if (!enter_owned()) { cputs("PATH FAIL\r\nDONE\r\n"); return 1; }
    cputs("PATH 00\r\n");
    (void)cbm_open(6u, DEVICE, 6u, "readyfs-absent,s,r");
    status_text[0] = status_text[1] = 0;
    (void)status_read("");
    cbm_close(6u); cbm_k_clrch();
    cputs("PREFLIGHT "); print_status(); cputs("\r\n");
    if (!enter_owned()) { cputs("REENTER FAIL\r\nDONE\r\n"); return 1; }
    cputs("REENTER 00\r\n");
    opened = (unsigned char)(cbm_open(3u, DEVICE, 3u, name) == 0u);
    status_text[0] = status_text[1] = 0;
    (void)status_read("");
    cputs("OPEN "); print_status(); cputs("\r\n");
    if (opened && status_text[0] == '0' && status_text[1] == '0') {
        count = cbm_write(3u, "probe\r", 6u);
        cputs("WRITE "); cprintf("%d\r\n", count);
    }
    cbm_close(3u); cbm_k_clrch();
    opened = (unsigned char)(cbm_open(2u, DEVICE, 2u,
                                     SOFTWRITE_LEAF ",s,r") == 0u);
    status_text[0] = status_text[1] = 0;
    (void)status_read("");
    cputs("REOPEN "); print_status(); cputs("\r\n");
    count = opened ? cbm_read(2u, readback, sizeof(readback)) : -1;
    cbm_close(2u); cbm_k_clrch();
    cputs("READ "); cprintf("%d\r\n", count);
    cputs("DONE\r\n");
    return 0;
}
