#include "readyfs_console.h"
#include "readyfs_content.h"

#include <conio.h>
#include <string.h>

#define RF_CONTENT_MAGIC 0x43u

#ifdef __CC65__
typedef unsigned int ReadyFsContentWord;
#else
typedef unsigned short ReadyFsContentWord;
#endif

typedef struct {
    unsigned char magic;
    unsigned char mode;
    unsigned char limit;
    unsigned char lines;
    unsigned char line_open;
    unsigned char done;
    unsigned char truncated;
    unsigned char start;
    unsigned char used;
    ReadyFsContentWord total_low;
    ReadyFsContentWord total_high;
} ReadyFsContentState;

#define RF_CONTENT_RING_BYTES \
    (256u - (unsigned int)sizeof(ReadyFsContentState))

static void print_u32(ReadyFsContentWord high, ReadyFsContentWord low) {
    unsigned char digits[10];
    unsigned char bit;
    unsigned char i;
    unsigned char carry;
    unsigned char next;
    unsigned char started;
    memset(digits, 0, sizeof(digits));
    for (bit = 0u; bit < 32u; ++bit) {
        carry = (unsigned char)((high & 0x8000u) != 0u);
        high = (unsigned int)((high << 1u) | (low >> 15u));
        low <<= 1u;
        for (i = 10u; i != 0u; --i) {
            next = (unsigned char)(digits[i - 1u] * 2u + carry);
            digits[i - 1u] = (unsigned char)(next % 10u);
            carry = (unsigned char)(next / 10u);
        }
    }
    started = 0u;
    for (i = 0u; i < 10u; ++i) {
        if (digits[i] != 0u || i == 9u) started = 1u;
        if (started) cputc((char)('0' + digits[i]));
    }
}

static void print_hex8(unsigned char value) {
    unsigned char nibble;
    nibble = (unsigned char)(value >> 4u);
    cputc((char)(nibble < 10u ? '0' + nibble : 'a' + nibble - 10u));
    nibble = (unsigned char)(value & 15u);
    cputc((char)(nibble < 10u ? '0' + nibble : 'a' + nibble - 10u));
}

static void crc32_byte(ReadyFsContentState *state, unsigned char value) {
    unsigned char *crc;
    unsigned char bit;
    unsigned char carry;
    crc = (unsigned char *)(void *)&state->total_low;
    crc[0] ^= value;
    for (bit = 0u; bit < 8u; ++bit) {
        carry = (unsigned char)(crc[0] & 1u);
        crc[0] >>= 1u;
        if (crc[1] & 1u) crc[0] |= 0x80u;
        crc[1] >>= 1u;
        if (crc[2] & 1u) crc[1] |= 0x80u;
        crc[2] >>= 1u;
        if (crc[3] & 1u) crc[2] |= 0x80u;
        crc[3] >>= 1u;
        if (carry) {
            crc[0] ^= 0x20u;
            crc[1] ^= 0x83u;
            crc[2] ^= 0xB8u;
            crc[3] ^= 0xEDu;
        }
    }
}

unsigned char readyfs_content_parse_count(const char *text,
                                          unsigned char *value) {
    unsigned int parsed;
    parsed = 0u;
    if (text == 0 || *text == 0) return 0u;
    while (*text != 0) {
        if (*text < '0' || *text > '9') return 0u;
        parsed = (unsigned int)(parsed * 10u + (unsigned int)(*text++ - '0'));
        if (parsed > 255u) return 0u;
    }
    if (parsed == 0u) return 0u;
    *value = (unsigned char)parsed;
    return 1u;
}

static void view_byte(unsigned char value) {
    if (value == '\r' || value == '\n') {
        cputc('\r'); cputc('\n');
    } else cputc(value >= 32u && value <= 126u ? value : '.');
}

static unsigned char initialize(ReadyFsUtilityCall *call) {
    ReadyFsContentState *state;
    unsigned char mode;
    unsigned char limit;
    mode = (unsigned char)call->value_high;
    limit = 10u;
    call->value_low = 0u;
    if (call->workspace == 0 || call->args == 0 || call->argc < 2u ||
        mode > RF_CONTENT_CRC32 ||
        ((mode == RF_CONTENT_TYPE || mode == RF_CONTENT_CRC32) &&
         call->argc != 2u) ||
        ((mode == RF_CONTENT_HEAD || mode == RF_CONTENT_TAIL) &&
         (call->argc > 3u ||
          (call->argc == 3u &&
           !readyfs_content_parse_count(call->args[2], &limit))))) {
        cputs(mode == RF_CONTENT_HEAD ? "head path [lines]\r\n" :
              (mode == RF_CONTENT_TAIL ? "tail path [lines]\r\n" :
               (mode == RF_CONTENT_CRC32 ? "crc32 path\r\n" :
                                           "type path\r\n")));
        return 1u;
    }
    state = (ReadyFsContentState *)(void *)call->workspace;
    memset(state, 0, sizeof(*state));
    state->magic = RF_CONTENT_MAGIC;
    state->mode = mode;
    state->limit = limit;
    if (mode == RF_CONTENT_CRC32) {
        state->total_low = 0xFFFFu;
        state->total_high = 0xFFFFu;
    }
    call->value_low = 1u;
    return 1u;
}

static unsigned char add(ReadyFsUtilityCall *call) {
    ReadyFsContentState *state;
    unsigned char *ring;
    unsigned int before;
    unsigned int i;
    unsigned char value;
    unsigned int position;
    state = (ReadyFsContentState *)(void *)call->workspace;
    if (state == 0 || state->magic != RF_CONTENT_MAGIC ||
        call->buffer == 0) return 0u;
    if (state->mode != RF_CONTENT_CRC32) {
        before = state->total_low;
        state->total_low = (unsigned int)(state->total_low + call->capacity);
        if (state->total_low < before) ++state->total_high;
    }
    ring = (unsigned char *)(void *)(state + 1);
    for (i = 0u; i < call->capacity; ++i) {
        value = (unsigned char)call->buffer[i];
        if (state->mode == RF_CONTENT_CRC32) {
            crc32_byte(state, value);
        } else if (state->mode == RF_CONTENT_TAIL) {
            position = (unsigned int)(state->start + state->used);
            if (position >= RF_CONTENT_RING_BYTES) position -= RF_CONTENT_RING_BYTES;
            ring[position] = value;
            if (state->used < RF_CONTENT_RING_BYTES) ++state->used;
            else {
                if (++state->start >= RF_CONTENT_RING_BYTES) state->start = 0u;
                state->truncated = 1u;
            }
        } else if (!state->done) {
            view_byte(value);
            if (value == '\r' || value == '\n') {
                ++state->lines;
                state->line_open = 0u;
                if (state->mode == RF_CONTENT_HEAD &&
                    state->lines >= state->limit) state->done = 1u;
            } else state->line_open = 1u;
        }
    }
    call->value_low = state->done ? 0u : 1u;
    return 1u;
}

static unsigned char ring_byte(const ReadyFsContentState *state,
                               const unsigned char *ring,
                               unsigned char offset) {
    unsigned int position;
    position = (unsigned int)(state->start + offset);
    if (position >= RF_CONTENT_RING_BYTES) position -= RF_CONTENT_RING_BYTES;
    return ring[position];
}

static unsigned char report(ReadyFsUtilityCall *call) {
    ReadyFsContentState *state;
    unsigned char *ring;
    unsigned char skip;
    unsigned char i;
    unsigned char lines;
    unsigned char value;
    state = (ReadyFsContentState *)(void *)call->workspace;
    if (state == 0 || state->magic != RF_CONTENT_MAGIC) return 0u;
    if (state->mode == RF_CONTENT_TAIL) {
        ring = (unsigned char *)(void *)(state + 1);
        skip = 0u;
        lines = 0u;
        i = state->used;
        while (i != 0u) {
            --i;
            value = ring_byte(state, ring, i);
            if ((value == '\r' || value == '\n') && i + 1u != state->used &&
                ++lines >= state->limit) { skip = (unsigned char)(i + 1u); break; }
        }
        for (i = skip; i < state->used; ++i) view_byte(ring_byte(state, ring, i));
        if (state->truncated) cputs(RF_ERROR "\r\ntail truncated");
    }
    if ((state->mode != RF_CONTENT_TAIL && state->line_open) ||
        state->mode == RF_CONTENT_TAIL) cputs("\r\n");
    if (state->mode == RF_CONTENT_CRC32) {
        ring = (unsigned char *)(void *)&state->total_low;
        cputs("crc32 $");
        print_hex8((unsigned char)(ring[3] ^ 0xFFu));
        print_hex8((unsigned char)(ring[2] ^ 0xFFu));
        print_hex8((unsigned char)(ring[1] ^ 0xFFu));
        print_hex8((unsigned char)(ring[0] ^ 0xFFu));
        cputs("\r\n");
        return 1u;
    }
    if (state->mode == RF_CONTENT_HEAD) cputs("head; read ");
    else if (state->mode == RF_CONTENT_TAIL) cputs("tail; read ");
    else cputs("read ");
    print_u32(state->total_high, state->total_low); cputs(" bytes\r\n");
    return 1u;
}

unsigned int readyfs_content_abi(void) { return RF_CONTENT_ABI; }

unsigned char readyfs_content_dispatch(ReadyFsUtilityCall *call) {
    if (call == 0) return 0u;
#ifdef __CC65__
    if (call->operation == RF_UTILITY_FORMAT_MEDIA) {
        return readyfs_content_format((void *)call);
    }
    if (call->operation == RF_UTILITY_CONTENT_INIT &&
        call->value_high == RF_CONTENT_TEST) {
        return readyfs_utility_test((void *)call);
    }
#endif
    if (call->operation == RF_UTILITY_CONTENT_INIT) return initialize(call);
    if (call->operation == RF_UTILITY_CONTENT_ADD) return add(call);
    if (call->operation == RF_UTILITY_CONTENT_REPORT) return report(call);
    return 0u;
}
