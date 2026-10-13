/* Native, session-only last-mount hints. No network, relay, or disk registry.
 * A remembered path is never a statement about the drive's current media. */
#include "readyfs_present.h"
#include "readyfs_reu.h"
#include "readyfs_uci.h"
#include "readyfs_console.h"
extern unsigned char readyfs_iec_present(unsigned char device);
#include <conio.h>
#include <string.h>
static char path[256];
static unsigned int offset(unsigned char unit) {
    return RF_REU_MEDIA_OFF + ((unsigned int)(unit - 8u) << 8u);
}
static void number(unsigned char unit) {
    if (unit >= 10u) cputc('0' + unit / 10u);
    cputc('0' + unit % 10u);
}
void readyfs_media_reset(void) {
    unsigned char unit;
    path[0] = 0;
    for (unit = 8u; unit <= 30u; ++unit)
        (void)readyfs_reu_batch_store(offset(unit), path, 1u);
}
static unsigned char show(unsigned char unit) {
    number(unit); cputs(": ");
    if (readyfs_reu_batch_fetch(offset(unit), path, sizeof(path)) && path[0]) {
        path[255] = 0;
        cputs("last mounted by readyfs\r\n");
        cputs(path); cputs("\r\nmay have changed elsewhere\r\n");
        return (unsigned char)(3u + strlen(path) / 40u);
    }
    cputs("image path unknown\r\n"); return 1u;
}
unsigned char readyfs_media(ReadyFsUtilityCall *call) {
    unsigned char unit, found;
    unsigned int length;
    unit = (unsigned char)call->value_low;
    if (call->value_high == RF_MEDIA_DRIVES) {
        cputs("iec scan 8-30\r\n");
        found = 0u;
        for (unit = 8u; unit <= 30u; ++unit) {
            if (readyfs_iec_present(unit)) { show(unit); found = 1u; }
        }
        if (!found) cputs("no iec listeners\r\n");
        if (readyfs_uci_detect()) {
            cputs("u: ultimate dos\r\ns: softiec bus ");
            number(readyfs_uci_softiec_bus()); cputs("\r\n");
        } else cputs("uci unavailable\r\n");
        cputs("t: sequential tape\r\n");
        return 1u;
    }
    if (unit < 8u || unit > 30u) return 0u;
    if (call->value_high == RF_MEDIA_SHOW) { call->capacity = show(unit); return 1u; }
    path[0] = 0;
    /* Clear first, including failed replacement attempts, so an old mount
     * never masquerades as the outcome of an ambiguous hardware operation. */
    if (!readyfs_reu_batch_store(offset(unit), path, 1u)) return 0u;
    if (call->value_high == RF_MEDIA_FORGET) return 1u;
    if (call->value_high != RF_MEDIA_REMEMBER || !call->buffer) return 0u;
    length = strlen(call->buffer);
    if (!length || length > 255u) return 0u;
    if (!readyfs_reu_batch_store(offset(unit), call->buffer, length + 1u)) return 0u;
    cputs(RF_SUMMARY "mounted on "); number(unit); cputs(":\r\n");
    show(unit);
    return 1u;
}
