#include "readyfs_reu.h"
#include "readyfs_console.h"

#include <string.h>

#define REU_COMMAND  (*(volatile unsigned char*)0xDF01)
#define REU_C64_LO   (*(volatile unsigned char*)0xDF02)
#define REU_C64_HI   (*(volatile unsigned char*)0xDF03)
#define REU_REU_LO   (*(volatile unsigned char*)0xDF04)
#define REU_REU_HI   (*(volatile unsigned char*)0xDF05)
#define REU_REU_BANK (*(volatile unsigned char*)0xDF06)
#define REU_LEN_LO   (*(volatile unsigned char*)0xDF07)
#define REU_LEN_HI   (*(volatile unsigned char*)0xDF08)

#define REU_CMD_STASH 0x90u
#define REU_CMD_FETCH 0x91u
#define RF_REU_PROBE_OFF 0xFFF0u
#define RF_REU_SESSION_BASE 0x2000u
#define RF_REU_SESSION_SIZE 0xDFF0u

static unsigned char probe_byte;
/* Keep persistent REU selectors/cursors in initialized DATA, below the high
 * resident tail that KERNAL disk I/O may use as scratch. readyfs_reu_init()
 * replaces every sentinel before normal use. */
static unsigned char bank_count_encoded = 0xFFu;
unsigned char readyfs_reu_history_bank_value = 0xFFu;
unsigned char readyfs_reu_overlay_bank_value = 0xFFu;
unsigned char readyfs_reu_batch_bank_value = 0xFFu;
#define history_bank readyfs_reu_history_bank_value
#define overlay_bank readyfs_reu_overlay_bank_value
static unsigned char history_head = 0xFFu;
static unsigned char history_used = 0xFFu;

static void reu_transfer(unsigned char command, void *ram,
                         unsigned char bank, unsigned int offset,
                         unsigned int length) {
    unsigned int addr;

    addr = (unsigned int)ram;
    REU_C64_LO = (unsigned char)(addr & 0xFFu);
    REU_C64_HI = (unsigned char)(addr >> 8u);
    REU_REU_LO = (unsigned char)(offset & 0xFFu);
    REU_REU_HI = (unsigned char)(offset >> 8u);
    REU_REU_BANK = bank;
    REU_LEN_LO = (unsigned char)(length & 0xFFu);
    REU_LEN_HI = (unsigned char)(length >> 8u);
    REU_COMMAND = command;
}

static unsigned char fetch_probe(unsigned char bank) {
    probe_byte = 0u;
    reu_transfer(REU_CMD_FETCH, &probe_byte, bank, RF_REU_PROBE_OFF, 1u);
    return probe_byte;
}

static void stash_probe(unsigned char bank, unsigned char value) {
    probe_byte = value;
    reu_transfer(REU_CMD_STASH, &probe_byte, bank, RF_REU_PROBE_OFF, 1u);
}

static unsigned char detect_banks(void) {
    unsigned char original0;
    unsigned char original;
    unsigned char got;
    unsigned int bank;

    original0 = fetch_probe(0u);
    stash_probe(0u, 0x5Au);
    for (bank = 1u; bank < 256u; ++bank) {
        original = fetch_probe((unsigned char)bank);
        stash_probe((unsigned char)bank, 0xC3u);
        got = fetch_probe(0u);
        stash_probe((unsigned char)bank, original);
        if (got == 0xC3u) {
            stash_probe(0u, original0);
            return (unsigned char)bank;
        }
    }
    stash_probe(0u, original0);
    return 0u; /* Encoded 256 banks. */
}

unsigned char readyfs_reu_init(void) {
    unsigned int count;

    bank_count_encoded = detect_banks();
    count = bank_count_encoded == 0u ? 256u : (unsigned int)bank_count_encoded;
    if (count < 16u) return 0u;
    history_bank = (unsigned char)(count - 1u);
    overlay_bank = (unsigned char)(count - 2u);
    readyfs_reu_batch_bank_value = (unsigned char)(count - 3u);
    readyfs_reu_console_bank_value = (unsigned char)(count - 4u);
    history_head = 0u;
    history_used = 0u;
    return 1u;
}

unsigned int readyfs_reu_bank_count(void) {
    return bank_count_encoded == 0u ? 256u : (unsigned int)bank_count_encoded;
}

void readyfs_reu_history_add(const char *line) {
    unsigned int offset;

    if (history_bank == 0u || line == 0 || line[0] == 0) return;
    offset = (unsigned int)history_head * RF_REU_HISTORY_BYTES;
    /* ReadyFS always supplies its full 256-byte, NUL-terminated line buffer;
     * DMA it directly instead of reserving a duplicate resident slot. */
    reu_transfer(REU_CMD_STASH, (void *)line, history_bank, offset,
                 RF_REU_HISTORY_BYTES);
    history_head = (unsigned char)((history_head + 1u) % RF_REU_HISTORY_SLOTS);
    if (history_used < RF_REU_HISTORY_SLOTS) ++history_used;
}

unsigned char readyfs_reu_history_get(unsigned char age, char *out) {
    unsigned char slot_index;
    unsigned int offset;

    if (out == 0 || age >= history_used || history_bank == 0u) return 0u;
    slot_index = (unsigned char)((history_head + RF_REU_HISTORY_SLOTS - 1u - age) %
                                 RF_REU_HISTORY_SLOTS);
    offset = (unsigned int)slot_index * RF_REU_HISTORY_BYTES;
    reu_transfer(REU_CMD_FETCH, out, history_bank, offset, RF_REU_HISTORY_BYTES);
    out[RF_REU_HISTORY_BYTES - 1u] = 0;
    return 1u;
}

unsigned char readyfs_reu_history_count(void) {
    return history_used;
}

