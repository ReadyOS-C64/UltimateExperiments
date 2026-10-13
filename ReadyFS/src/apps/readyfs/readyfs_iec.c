/* Native leaf service: no overlay loads, UCI, host, network or file data I/O. */
#include "readyfs_iec.h"
#include "readyfs_reu.h"
#include "readyfs_result.h"
#include "readyfs_console.h"
#include "readyfs_present.h"
#include <cbm.h>
#include <conio.h>
#include <string.h>

unsigned int readyfs_iec_abi(void) {
#ifdef __CC65__
    readyfs_media_reset();
#endif
    return RF_IEC_ABI;
}

/* Standalone configuration only: CLOSE15 releases ALL SD2IEC user buffers.
 * Never reuse this transaction while filesystem data channels are open.
 * Explicit-length writes preserve binary G-P partition 0, U0> and U-$CA. */
static int transaction(unsigned char device, const unsigned char *command,
                       unsigned char length, unsigned char *reply,
                       unsigned char read_reply) {
    int count;
    count = -1;
    reply[0] = 0u;
    if (!cbm_open(15u, device, 15u, "")) {
        if (!length || cbm_write(15u, command, length) == length) {
            if (read_reply) {
                count = cbm_read(15u, reply, 79u);
                if (count >= 0) reply[count] = 0u;
            } else count = 0;
        }
    }
    cbm_close(15u); cbm_k_clrch();
    return count;
}

static unsigned char fold(unsigned char c) {
    c &= 0x7Fu;
    if (c >= 97u && c <= 122u) c -= 32u;
    return c;
}

static unsigned char is_sd(const unsigned char *text) {
    const unsigned char *start;
    const char *word;
    unsigned char n, i;
    for (n = 0u; n < 2u; ++n) {
        word = n ? "uiec" : "sd2iec";
        for (start = text; *start; ++start) {
            for (i = 0u; word[i] && start[i] &&
                 fold(start[i]) == fold(word[i]); ++i) {}
            if (!word[i]) return 1u;
        }
    }
    return 0u;
}

static void invalidate(unsigned char device) {
    unsigned char zero[4];
    memset(zero, 0, sizeof(zero));
    (void)readyfs_reu_session_store(RF_REU_DRIVE_PROFILE_OFF +
          (unsigned int)(device - 8u) * 4u, zero, 4u);
    (void)readyfs_reu_batch_store(RF_REU_MEDIA_OFF +
          (unsigned int)(device - 8u) * 256u, zero, 1u);
}

static unsigned char fail(ReadyFsIecCall *c, unsigned char result,
                           const char *message) {
    *c->status = result;
    cputs(RF_ERROR); cputs(message); cputs("\r\n");
    return 0u;
}

static unsigned char partitions(ReadyFsIecCall *c) {
    unsigned char lines, bytes, ok;
    unsigned char *b;
    b = c->reply; lines = 0u; ok = 0u;
    if (cbm_open(2u, c->device, 0u, "$=p")) goto done;
    if (cbm_read(2u, b, 2u) != 2) goto done; /* BASIC load address */
    for (;;) {
        if (cbm_read(2u, b, 2u) != 2) break;
        if (!(b[0] | b[1])) { ok = 1u; break; } /* no BLOCKS FREE footer */
        if (cbm_read(2u, b, 2u) != 2) break;
        cputc('$'); cputhex8(b[1]); cputhex8(b[0]); cputc(' ');
        for (bytes = 0u; bytes < 96u; ++bytes) {
            if (cbm_read(2u, b, 1u) != 1) goto done;
            if (!b[0]) break;
            /* Directory reverse-video controls are not console markers. */
            if (b[0] >= 32u && b[0] != 146u) cputc(b[0]);
        }
        if (bytes == 96u) break;
        cputs("\r\n");
        if (++lines == 16u) {
            cputs(RF_SUMMARY "-- more --\r\n");
            if (cgetc() == CH_STOP) { ok = 1u; break; }
            lines = 0u;
        }
    }
done:
    cbm_close(2u); cbm_k_clrch();
    return ok ? 1u : fail(c, RF_RESULT_IO, "partition listing failed");
}

unsigned char readyfs_iec_execute(ReadyFsIecCall *c) {
    int count;
    unsigned char code;
    unsigned char i;
    if (c->flags & RF_IEC_SD_ONLY) {
        count = transaction(c->device, (const unsigned char *)"ui", 2u,
                            c->reply, 1u);
        if (count < 0) return fail(c, RF_RESULT_UNAVAILABLE, "device absent");
        if (!is_sd(c->reply)) return fail(c, RF_RESULT_UNSUPPORTED, "need sd2iec/uiec");
    }
    if (c->operation == RF_IEC_ADDRESS) {
        /* Do not introduce an address conflict with another bus listener. */
#ifdef __CC65__
        *(volatile unsigned char *)0x90u = 0u;
#endif
        cbm_k_listen(c->new_device); cbm_k_second(0x6Fu);
        i = cbm_k_readst(); cbm_k_unlsn(); cbm_k_clrch();
        if (!i) return fail(c, RF_RESULT_CONFLICT, "new address occupied");
        if (i != 0x80u) return fail(c, RF_RESULT_IO, "address check failed");
    }
    if (c->operation == RF_IEC_PARTITIONS) return partitions(c);
    if (c->flags & RF_IEC_INVALIDATE) {
        if (c->flags & RF_IEC_RAW) {
            for (i = 8u; i <= 30u; ++i) invalidate(i);
        } else {
            invalidate(c->device);
            if (c->new_device) invalidate(c->new_device);
        }
    }
    count = transaction(c->device, c->command, c->length, c->reply,
                         c->operation != RF_IEC_ADDRESS &&
                         c->operation != RF_IEC_RESTART);
    if (count < 0) return fail(c, RF_RESULT_IO, "iec command failed");
    if (c->operation == RF_IEC_ADDRESS) {
        count = transaction(c->new_device, (const unsigned char *)"ui", 2u,
                            c->reply, 1u);
        if (count < 0 || !is_sd(c->reply))
            return fail(c, RF_RESULT_PARTIAL, "address sent; verify failed");
        if (c->flags & RF_IEC_SAVE) {
            count = transaction(c->new_device, (const unsigned char *)"xw", 2u,
                                c->reply, 1u);
            if (count < 2 || c->reply[0] != '0' || c->reply[1] != '3')
                return fail(c, RF_RESULT_PARTIAL, "address changed; save failed");
        }
        cputs(RF_SUMMARY "address verified\r\n");
        return 1u;
    }
    if (c->operation == RF_IEC_RESTART) {
        cputs(RF_SUMMARY "restart sent; saved address applies\r\n");
        return 1u;
    }
    if (c->operation == RF_IEC_PARTITION) {
        if (count != 31 || c->reply[30] != 13u)
            return fail(c, RF_RESULT_IO, "invalid partition reply");
        if (!c->reply[0]) return fail(c, RF_RESULT_NOT_FOUND, "partition absent");
        cputs("partition $"); cputhex8(c->reply[2]);
        cputs(" type $"); cputhex8(c->reply[0]); cputs("\r\n");
        for (i = 3u; i < 19u; ++i) cputc(c->reply[i] == 0xA0u ? ' ' : c->reply[i]);
        cputs("\r\n512-byte blocks $");
        cputhex8(c->reply[27]); cputhex8(c->reply[28]); cputhex8(c->reply[29]);
        cputs("\r\n");
        if (c->reply[0] == 1u) cputs("type 1: fat or dnp\r\n");
        return 1u;
    }
    if (count < 2 || c->reply[0] < '0' || c->reply[0] > '9' ||
        c->reply[1] < '0' || c->reply[1] > '9')
        return fail(c, RF_RESULT_IO, "invalid dos status");
    code = (c->reply[0] - '0') * 10u + c->reply[1] - '0';
    if (c->expected == 255u ? (code > 3u && code != 9u && code != 73u) : code != c->expected)
        return fail(c, RF_RESULT_IO, (char *)c->reply);
    cputs(RF_SUMMARY); cputs((char *)c->reply); cputs("\r\n");
    return 1u;
}
