#include "src/apps/readyfs/readyfs_uci.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

#define ST_DATA  0x80u
#define ST_STAT  0x40u
#define ST_BUSY  0x10u
#define ST_LAST  0x20u
#define ST_MORE  0x30u
#define ST_ABORT 0x04u
#define ST_ERROR 0x08u

static unsigned int selected_base;
static unsigned char phase;
static unsigned char scenario;
static unsigned char block_index;
static unsigned char pushed_samples;
static unsigned char data_index;
static unsigned char stat_index;
static unsigned char command_bytes[16];
static unsigned char command_count;
static unsigned char push_count;
static unsigned char abort_count;
static unsigned char accept_count;
static unsigned char accept_more_count;
static unsigned char handled_data[8];
static unsigned char handled_length;
static unsigned char handled_blocks;

static const unsigned char reply_data[] = {'D','O','S',' ','V'};
static const unsigned char reply_stat[] = {'0','0'};
static const unsigned char more_data_0[] = {'A','B','C'};
static const unsigned char more_data_1[] = {'D','E'};
static const unsigned char more_stat[] = {'0'};

static unsigned int active_data_length(void) {
    if (scenario == 1u) {
        return block_index == 0u ? sizeof(more_data_0) : sizeof(more_data_1);
    }
    return sizeof(reply_data);
}

static unsigned int active_stat_length(void) {
    return scenario == 1u ? sizeof(more_stat) : sizeof(reply_stat);
}

void readyfs_uci_asm_set_base(unsigned int base) { selected_base = base; }
unsigned char readyfs_uci_asm_id(void) {
    return selected_base == 0xDF1Cu ? 0x49u : 0u;
}
unsigned char readyfs_uci_asm_softiec_bus(void) { return 11u; }
unsigned char readyfs_uci_asm_write_cmd(unsigned char value) {
    assert(command_count < sizeof(command_bytes));
    command_bytes[command_count++] = value;
    return value;
}
void readyfs_uci_asm_push_cmd(void) {
    ++push_count;
    pushed_samples = 0u;
    data_index = 0u;
    stat_index = 0u;
    block_index = 0u;
    phase = 1u;
}
unsigned char readyfs_uci_asm_status(void) {
    if (phase == 0u || phase == 5u) return 0u;
    if (phase == 1u) {
        if (pushed_samples++ == 0u) return 0u; /* PUSH not observed yet. */
        phase = push_count == 1u ? 2u : (scenario == 3u ? 7u : 4u);
    }
    if (phase == 2u) return ST_BUSY;
    if (phase == 3u) {
        phase = push_count == 1u ? 4u : 5u;
        return ST_ABORT;
    }
    if (phase == 4u) {
        unsigned char st = (scenario == 1u && block_index == 0u) ?
                           ST_MORE : ST_LAST;
        if (data_index < active_data_length()) st |= ST_DATA;
        if (stat_index < active_stat_length()) st |= ST_STAT;
        return st;
    }
    if (phase == 6u) {
        phase = 4u;
        block_index = 1u;
        data_index = 0u;
        stat_index = 0u;
        return ST_BUSY;
    }
    if (phase == 7u) return ST_ERROR;
    return 0u;
}
unsigned char readyfs_uci_asm_read_data(void) {
    if (scenario == 1u) {
        assert(data_index < active_data_length());
        return block_index == 0u ? more_data_0[data_index++] :
                                  more_data_1[data_index++];
    }
    assert(data_index < active_data_length());
    return reply_data[data_index++];
}
unsigned char readyfs_uci_asm_read_stat(void) {
    if (scenario == 1u) {
        assert(stat_index < active_stat_length());
        return more_stat[stat_index++];
    }
    assert(stat_index < active_stat_length());
    return reply_stat[stat_index++];
}
void readyfs_uci_asm_accept_data(void) {
    ++accept_count;
    phase = 5u;
}
unsigned char readyfs_uci_asm_accept_more_transition(unsigned char old_state) {
    assert(old_state == ST_MORE);
    assert(scenario == 1u && block_index == 0u);
    ++accept_more_count;
    phase = 6u;
    return 1u;
}
void readyfs_uci_asm_abort(void) {
    ++abort_count;
    phase = 3u;
}
void readyfs_uci_asm_clear_error(void) {
    assert(!"recovery oracle does not inject ERROR");
}

static void collect_blocks(const unsigned char *data, unsigned int data_len,
                           const unsigned char *stat, unsigned int stat_len) {
    assert(stat_len == 1u && stat[0] == '0');
    assert(handled_length + data_len <= sizeof(handled_data));
    memcpy(handled_data + handled_length, data, data_len);
    handled_length = (unsigned char)(handled_length + data_len);
    ++handled_blocks;
}

int main(void) {
    ReadyFsUciTransfer xfer;
    unsigned char data[8];
    unsigned char stat[4];
    const unsigned char identify[] = {1u, 1u};

    memset(&xfer, 0, sizeof(xfer));
    xfer.data = data;
    xfer.data_cap = sizeof(data);
    xfer.stat = stat;
    xfer.stat_cap = sizeof(stat);

    assert(readyfs_uci_recovery_probe());
    assert(push_count == 1u);
    assert(abort_count == 1u);
    assert(accept_count == 1u);
    assert(command_count == 2u);
    assert(command_bytes[0] == 1u && command_bytes[1] == 1u);

    assert(readyfs_uci_command(identify, sizeof(identify), &xfer));
    assert(push_count == 2u);
    assert(abort_count == 1u);
    assert(accept_count == 2u);
    assert(command_count == 4u);
    assert(xfer.flags == 0u);
    assert(xfer.data_len == sizeof(reply_data));
    assert(xfer.stat_len == sizeof(reply_stat));
    assert(memcmp(data, reply_data, sizeof(reply_data)) == 0);
    assert(memcmp(stat, reply_stat, sizeof(reply_stat)) == 0);

    scenario = 1u;
    handled_length = 0u;
    handled_blocks = 0u;
    memset(&xfer, 0, sizeof(xfer));
    xfer.data = data;
    xfer.data_cap = sizeof(data);
    xfer.stat = stat;
    xfer.stat_cap = sizeof(stat);
    xfer.on_block = collect_blocks;
    assert(readyfs_uci_command(identify, sizeof(identify), &xfer));
    assert(accept_more_count == 1u);
    assert(xfer.block_count == 2u && handled_blocks == 2u);
    assert(xfer.data_seen == 5u && xfer.stat_seen == 2u);
    assert(handled_length == 5u && memcmp(handled_data, "ABCDE", 5u) == 0);
    assert(xfer.flags == 0u);

    scenario = 2u;
    memset(&xfer, 0, sizeof(xfer));
    xfer.data = data;
    xfer.data_cap = 2u;
    xfer.stat = stat;
    xfer.stat_cap = 1u;
    assert(readyfs_uci_command(identify, sizeof(identify), &xfer));
    assert(xfer.data_len == 2u && xfer.stat_len == 1u);
    assert(xfer.data_seen == sizeof(reply_data));
    assert(xfer.stat_seen == sizeof(reply_stat));
    assert((xfer.flags & (RF_UCI_TRUNC_DATA | RF_UCI_TRUNC_STAT)) ==
           (RF_UCI_TRUNC_DATA | RF_UCI_TRUNC_STAT));

    scenario = 3u;
    memset(&xfer, 0, sizeof(xfer));
    assert(!readyfs_uci_command(identify, sizeof(identify), &xfer));
    assert((xfer.flags & RF_UCI_ERROR) != 0u);
    assert(abort_count == 2u);

    assert(!readyfs_uci_command(identify, 897u, &xfer));
    assert(push_count == 5u);

    puts("readyfs UCI recovery/multiblock/truncation/error tests passed");
    return 0;
}
