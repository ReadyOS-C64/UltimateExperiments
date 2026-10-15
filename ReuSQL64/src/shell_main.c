#include <cbm.h>
#include <string.h>

#include "rsql.h"
#include "rsql_shell.h"

#define FOUNDATION_SENTINEL (*(volatile rsql_u8*)0xCFF0)
#define REU_SIZE_SELECTOR (*(volatile rsql_u8*)0xCFF1)
#define OVERLAY_PRELOADED_MASK (*(volatile rsql_u8*)0xCFF2)
#define FAILURE_STAGE (*(volatile rsql_u8*)0xCFF3)
#define FAILURE_DETAIL (*(volatile rsql_u8*)0xCFF5)
#define BORDER_COLOR (*(volatile rsql_u8*)0xD020)

static char g_line[RSQL_SHELL_LINE_MAX + 1u];

static void output(const char* bytes, rsql_u16 length, void* user) {
    rsql_u8 value;
    (void)user;
    while (length--) {
        value = (rsql_u8)*bytes++;
        /* cc65 source uppercase is shifted PETSCII. CHROUT displays it, but
         * screen-RAM automation cannot decode that spelling. Emit the
         * equivalent unshifted PETSCII letter so humans and VICE agree. */
        if (value >= 0xC1u && value <= 0xDAu) value -= 0x80u;
        cbm_k_bsout(value == '\n' ? 13u : value);
    }
}

static rsql_u8 read_line(void) {
    rsql_u16 length = 0u;
    rsql_u8 value;
    for (;;) {
        value = cbm_k_getin();
        if (!value) continue;
        if (value == 13u) {
            cbm_k_bsout(13u);
            g_line[length] = 0;
            return 1u;
        }
        if (value == 3u) return 0u;
        if (value == 20u) {
            if (length) {
                --length;
                cbm_k_bsout(20u);
            }
        } else if (value >= 32u && length < RSQL_SHELL_LINE_MAX) {
            g_line[length++] = (char)value;
            cbm_k_bsout(value);
        }
    }
}

static void fail(rsql_u8 stage, rsql_u8 detail) {
    FAILURE_STAGE = stage;
    FAILURE_DETAIL = detail;
    FOUNDATION_SENTINEL = detail ? detail : 0xFFu;
    BORDER_COLOR = 2u;
    for (;;) {}
}

int main(void) {
    RsqlInitRequest init;
    RsqlShell shell;
    rsql_u8 rc;
    BORDER_COLOR = 0u;
    FOUNDATION_SENTINEL = 0u;
    memset(&init, 0, sizeof(init));
    init.abi_major = RSQL_ABI_MAJOR;
    init.abi_minor = RSQL_ABI_MINOR;
    init.reu.probe_hardware = 1u;
    init.format_if_missing = 1u;
    init.preloaded_overlay_mask = OVERLAY_PRELOADED_MASK;
    rc = rsql_init(&init);
    if (rc != RSQL_OK) fail(0x10u, rc);
    if (rsql_reu_size_kib() != (rsql_u16)(512u << REU_SIZE_SELECTOR)) {
        fail(0x11u, RSQL_ERR_REU_TOO_SMALL);
    }
    rsql_shell_init(&shell, output, 0);
    output("REUSQL64 SHELL 0.1\nTYPE .HELP\n", 31u, 0);
    while (!shell.quit_requested) {
        output("RSQL> ", 6u, 0);
        if (!read_line()) break;
        (void)rsql_shell_run_line(&shell, g_line);
    }
    rc = rsql_checkpoint();
    if (rc != RSQL_OK) fail(0x20u, rc);
    rc = rsql_shutdown();
    if (rc != RSQL_OK) fail(0x21u, rc);
    FOUNDATION_SENTINEL = 0xA5u;
    BORDER_COLOR = 5u;
    return 0;
}
