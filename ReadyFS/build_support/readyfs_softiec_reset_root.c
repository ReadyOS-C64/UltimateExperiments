/* Test-only native IEC cwd restoration. Does not write files or settings. */
#include <cbm.h>
#include <string.h>

int main(void) {
    char command[6];
    unsigned char status[64];
    strcpy(command, "cd0:."); command[4] = 0x5Fu;
    if (!cbm_open(15u, 11u, 15u, command)) {
        (void)cbm_read(15u, status, sizeof(status));
    }
    cbm_close(15u); cbm_k_clrch();
    *(unsigned char *)0xC1F0u = 0xA5u;
    for (;;) {}
    return 0;
}
