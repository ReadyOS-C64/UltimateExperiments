#include <cbm.h>
#include <conio.h>
#include <string.h>

/* Focused disposable-TAP transport oracle. ReadyFS itself remains the target;
 * this probe first proves the cc65/KERNAL device-1 channel contract that its
 * sequential adapter will use. */

static const char payload[] = "tape data\r";
static char readback[32];

static void line(const char *text) {
    cputs(text);
    cputs("\r\n");
}

int main(void) {
    int count;

    clrscr();
    line("readyfs tape probe");
    line("write arm");
    (void)cgetc();
    line("write open");
    if (cbm_open(2u, 1u, 1u, "rfseq") != 0u) {
        line("write open fail");
        return 1;
    }
    count = cbm_write(2u, payload, sizeof(payload) - 1u);
    cbm_close(2u);
    cbm_k_clrch();
    if (count != (int)(sizeof(payload) - 1u)) {
        line("write fail");
        return 2;
    }
    line("write ok 10");

    line("read arm");
    (void)cgetc();
    line("read open");
    if (cbm_open(2u, 1u, 0u, "rfseq") != 0u) {
        line("read open fail");
        return 3;
    }
    memset(readback, 0, sizeof(readback));
    /* ReadyFS streams in 32-byte chunks.  This oversized request must return
     * the ten payload bytes as a short final chunk at tape-file EOF. */
    count = cbm_read(2u, readback, sizeof(readback));
    cbm_close(2u);
    cbm_k_clrch();
    if (count != (int)(sizeof(payload) - 1u) ||
        memcmp(readback, payload, sizeof(payload) - 1u) != 0) {
        line("read verify fail");
        return 4;
    }
    line("read ok 10");
    line("tape probe pass");
    for (;;) { }
    return 0;
}
