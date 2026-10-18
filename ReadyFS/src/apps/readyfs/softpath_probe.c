#include <cbm.h>
#include <conio.h>
#include <stdio.h>
#include <string.h>

#define DEVICE 11u

static char status_text[40];

static int status_read(const char *command) {
    int count;
    if (cbm_open(15u, DEVICE, 15u, command) != 0u) return -1;
    count = cbm_read(15u, status_text, sizeof(status_text) - 1u);
    cbm_close(15u);
    cbm_k_clrch();
    if (count < 0) return count;
    status_text[count] = 0;
    return count;
}

static void drain_status(void) {
    (void)status_read("");
}

static unsigned char directory_header(char *name) {
    struct cbm_dirent entry;
    unsigned char rc;

    name[0] = 0;
    if (cbm_opendir(2u, DEVICE) != 0u) return 0u;
    rc = cbm_readdir(2u, &entry);
    if (rc == 0u) {
        strncpy(name, entry.name, 16u);
        name[16] = 0;
    }
    cbm_closedir(2u);
    cbm_k_clrch();
    return (unsigned char)(rc == 0u);
}

static void attempt(const char *label, const char *command) {
    int status_len;
    char header[17];

    drain_status();
    status_len = status_read(command);
    cputs(label); cputc(' ');
    if (status_len >= 2) {
        cputc(status_text[0]); cputc(status_text[1]);
    } else cputs("IO");
    cputs(" H ");
    if (directory_header(header)) cputs(header);
    else cputs("FAIL");
    cputs("\r\n");
}

static void open_attempt(const char *label, const char *name) {
    unsigned char rc;
    int status_len;

    drain_status();
    rc = cbm_open(6u, DEVICE, 6u, name);
    status_len = status_read("");
    cbm_close(6u);
    cbm_k_clrch();
    cputs(label); cputc(' '); cprintf("%u ", rc);
    if (status_len >= 2) {
        cputc(status_text[0]); cputc(status_text[1]);
    } else cputs("IO");
    cputs("\r\n");
}

int main(void) {
    char test_command[16];
    char reset_command[5];

    bordercolor(COLOR_BLUE);
    bgcolor(COLOR_BLUE);
    textcolor(COLOR_WHITE);
    clrscr();
    cputs("SOFTPATH READ-ONLY\r\n");

    /* Lowercase C literals map to uppercase ASCII/PETSCII command bytes in
     * the cc65 C64 target. Uppercase source literals carry the high-bit
     * screen-code form and are correctly rejected by SoftwareIEC as syntax. */
    attempt("ROOT", "cd:/");
    attempt("USB1", "cd:usb1");
    /* cc65 maps even escaped source '_' through the C64 character map to
     * $A4.  The SoftwareIEC matcher exposes host '_' as PETSCII $5F, so put
     * that byte into the command at run time (typed input already uses
     * PETSCII and does not need this compiled-literal workaround). */
    strcpy(test_command, "cd:readyfs.test");
    test_command[10] = 0x5fu;
    attempt("TEST", test_command);
    attempt("OWN", "cd:readyfs-20260815-190355-79014");
    open_attempt("DIR OPEN", "rf065128");
    open_attempt("MARK OPEN", ".readyfs-owner-readyfs-20260815-190355-79014");
    attempt("CASE", "cd:rf065128");
    open_attempt("MISS OPEN", "sfa.seq");
    strcpy(reset_command, "cd:.");
    reset_command[3] = 0x5fu;
    attempt("RESET", reset_command);
    cputs("DONE\r\n");
    return 0;
}
