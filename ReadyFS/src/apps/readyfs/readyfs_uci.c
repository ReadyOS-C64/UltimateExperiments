#include "readyfs_uci.h"

#define UCI_STAT_DATA   0x80u
#define UCI_STAT_STAT   0x40u
#define UCI_STATE_MASK  0x30u
#define UCI_STATE_IDLE  0x00u
#define UCI_STATE_LAST  0x20u
#define UCI_STATE_MORE  0x30u
#define UCI_STAT_BUSY   0x01u
#define UCI_STAT_ACCEPT 0x02u
#define UCI_STAT_ABORT  0x04u
#define UCI_STAT_ERROR  0x08u

#define UCI_WAIT_SYNC     60000u
#define UCI_WAIT_RESPONSE 60000u
/* Four finite passes preserve the proven 16 MHz wall-time at 64 MHz. */
#define UCI_WAIT_PASSES   4u

static unsigned int uci_base_addr;

static unsigned char id_matches(unsigned char id) {
    return (unsigned char)((id & RF_UCI_ID_MASK) == RF_UCI_ID_MATCH);
}

static unsigned char probe_base(unsigned int base) {
    readyfs_uci_asm_set_base(base);
    if (id_matches(readyfs_uci_asm_id())) {
        uci_base_addr = base;
        return 1u;
    }
    return 0u;
}

/* IDLE is reusable only when every asynchronous control bit is also clear. */
static unsigned char status_is_quiet_idle(unsigned char st) {
    return (unsigned char)(((st & UCI_STATE_MASK) == UCI_STATE_IDLE) &&
                           ((st & (UCI_STAT_BUSY | UCI_STAT_ACCEPT |
                                   UCI_STAT_ABORT | UCI_STAT_ERROR)) == 0u));
}

static unsigned char wait_idle(void) {
    unsigned char pass;
    unsigned int tries;
    unsigned char st;

    for (pass = 0u; pass < UCI_WAIT_PASSES; ++pass) {
        for (tries = 0u; tries < UCI_WAIT_RESPONSE; ++tries) {
            st = readyfs_uci_asm_status();
            if ((st & UCI_STAT_ERROR) != 0u) return 0u;
            if (status_is_quiet_idle(st)) return 1u;
        }
    }
    return 0u;
}

static unsigned char wait_response_state(void) {
    unsigned char pass;
    unsigned int tries;
    unsigned char st;
    unsigned char state;

    for (pass = 0u; pass < UCI_WAIT_PASSES; ++pass) {
        for (tries = 0u; tries < UCI_WAIT_RESPONSE; ++tries) {
            st = readyfs_uci_asm_status();
            if ((st & UCI_STAT_ERROR) != 0u) return 0u;
            state = (unsigned char)(st & UCI_STATE_MASK);
            if (state == UCI_STATE_LAST || state == UCI_STATE_MORE) return 1u;
        }
    }
    return 0u;
}

static unsigned char wait_accept_advance(unsigned char old_state) {
    unsigned char pass;
    unsigned int tries;
    unsigned char st;

    /* DATA_ACC is asynchronous. An unchanged data state is still the block
     * just acknowledged, never evidence that the next block is ready. */
    for (pass = 0u; pass < UCI_WAIT_PASSES; ++pass) {
        for (tries = 0u; tries < UCI_WAIT_RESPONSE; ++tries) {
            st = readyfs_uci_asm_status();
            if ((st & UCI_STAT_ERROR) != 0u) return 0u;
            if ((st & UCI_STATE_MASK) != old_state) return 1u;
        }
    }
    return 0u;
}

static unsigned char sync_interface(void) {
    unsigned char pass;
    unsigned int tries;
    unsigned char st;
    unsigned char state;

    for (pass = 0u; pass < UCI_WAIT_PASSES; ++pass) {
        for (tries = 0u; tries < UCI_WAIT_SYNC; ++tries) {
            st = readyfs_uci_asm_status();
            state = (unsigned char)(st & UCI_STATE_MASK);
            if ((st & UCI_STAT_ERROR) != 0u) {
                readyfs_uci_asm_clear_error();
                continue;
            }
            if ((st & UCI_STAT_ABORT) != 0u) {
                /* ABORT_P already represents a pending asynchronous request. */
                continue;
            }
            if ((st & UCI_STAT_DATA) != 0u) {
                (void)readyfs_uci_asm_read_data();
                continue;
            }
            if ((st & UCI_STAT_STAT) != 0u) {
                (void)readyfs_uci_asm_read_stat();
                continue;
            }
            if (state == UCI_STATE_LAST || state == UCI_STATE_MORE) {
                if (state == UCI_STATE_MORE) {
                    /* At 64 MHz a C call boundary can miss the brief required
                     * MORE -> BUSY transition. The bounded assembly helper
                     * observes that transition adjacent to DATA_ACC. */
                    if (!readyfs_uci_asm_accept_more_transition(state)) {
                        return 0u;
                    }
                } else {
                    readyfs_uci_asm_accept_data();
                    if (!wait_accept_advance(state)) return 0u;
                }
                continue;
            }
            if (status_is_quiet_idle(st)) return 1u;
        }
    }
    return 0u;
}

static unsigned char abort_and_recover(void) {
    unsigned char st;

    /* Request ABORT once. Then service pending queues/control until quiet. */
    st = readyfs_uci_asm_status();
    if ((st & UCI_STAT_ABORT) == 0u) readyfs_uci_asm_abort();
    return sync_interface();
}

static void record_wait_failure(ReadyFsUciTransfer *xfer) {
    unsigned char st;

    if (xfer == 0) return;
    st = readyfs_uci_asm_status();
    xfer->last_status = st;
    if ((st & UCI_STAT_ERROR) != 0u) xfer->flags |= RF_UCI_ERROR;
    else xfer->flags |= RF_UCI_TIMEOUT;
}

unsigned char readyfs_uci_detect(void) {
    static const unsigned int bases[] = { 0xDF1Cu, 0xDE1Cu, 0xDFFCu };
    unsigned char i;

    if (uci_base_addr != 0u) {
        if (probe_base(uci_base_addr)) return 1u;
        uci_base_addr = 0u;
    }
    for (i = 0u; i < sizeof(bases) / sizeof(bases[0]); ++i) {
        if (probe_base(bases[i])) return 1u;
    }
    return 0u;
}

unsigned int readyfs_uci_base(void) {
    return readyfs_uci_detect() ? uci_base_addr : 0u;
}

unsigned char readyfs_uci_id(void) {
    return readyfs_uci_detect() ? readyfs_uci_asm_id() : 0u;
}

unsigned char readyfs_uci_softiec_bus(void) {
    return readyfs_uci_detect() ? readyfs_uci_asm_softiec_bus() : 0xFFu;
}

unsigned char readyfs_uci_recovery_probe(void) {
    unsigned char pass;
    unsigned int tries;
    unsigned char st;

    if (!readyfs_uci_detect()) return 0u;
    if (!sync_interface() && !abort_and_recover()) return 0u;

    /* UltimateDOS IDENTIFY is read-only. Deliberately interrupt it only after
     * PUSH has visibly left reusable quiet idle; abort_and_recover owns the
     * one asynchronous ABORT request, queue service, DATA_ACC, and final
     * quiet-idle wait. Poll counts are failure bounds, never MHz pacing. */
    readyfs_uci_asm_write_cmd(1u);
    readyfs_uci_asm_write_cmd(1u);
    readyfs_uci_asm_push_cmd();
    for (pass = 0u; pass < UCI_WAIT_PASSES; ++pass) {
        for (tries = 0u; tries < UCI_WAIT_RESPONSE; ++tries) {
            st = readyfs_uci_asm_status();
            if (!status_is_quiet_idle(st)) return abort_and_recover();
        }
    }
    (void)abort_and_recover();
    return 0u;
}

unsigned char readyfs_uci_command(const unsigned char *cmd,
                                  unsigned int cmd_len,
                                  ReadyFsUciTransfer *xfer) {
    unsigned int i;
    unsigned int drain_tries;
    unsigned char st;
    unsigned char state;

    if (xfer != 0) {
        xfer->data_len = 0u;
        xfer->stat_len = 0u;
        xfer->data_seen = 0u;
        xfer->stat_seen = 0u;
        xfer->block_count = 0u;
        xfer->flags = 0u;
        xfer->last_status = 0u;
    }
    if (!readyfs_uci_detect() || cmd == 0 || cmd_len == 0u || cmd_len > 896u) {
        return 0u;
    }
    if (!sync_interface() && !abort_and_recover()) {
        if (xfer != 0) xfer->flags |= RF_UCI_TIMEOUT;
        return 0u;
    }
    for (i = 0u; i < cmd_len; ++i) readyfs_uci_asm_write_cmd(cmd[i]);
    readyfs_uci_asm_push_cmd();

    /* PUSH_CMD is asynchronous. Immediate IDLE means not yet observed, not
     * completion; only LAST/MORE begins response processing. */
    if (!wait_response_state()) {
        record_wait_failure(xfer);
        (void)abort_and_recover();
        return 0u;
    }
    for (;;) {
        st = readyfs_uci_asm_status();
        if (xfer != 0) xfer->last_status = st;
        if ((st & UCI_STAT_ERROR) != 0u) {
            if (xfer != 0) xfer->flags |= RF_UCI_ERROR;
            (void)abort_and_recover();
            return 0u;
        }
        state = (unsigned char)(st & UCI_STATE_MASK);
        if (state != UCI_STATE_LAST && state != UCI_STATE_MORE) {
            if (!wait_response_state()) {
                record_wait_failure(xfer);
                (void)abort_and_recover();
                return 0u;
            }
            continue;
        }
        /* Availability flags are authoritative. This bound only detects a
         * wedged flag and is comfortably above the 896+256-byte queues. */
        for (drain_tries = 0u; drain_tries < UCI_WAIT_RESPONSE; ++drain_tries) {
            st = readyfs_uci_asm_status();
            if (xfer != 0) xfer->last_status = st;
            if ((st & UCI_STAT_ERROR) != 0u) {
                if (xfer != 0) xfer->flags |= RF_UCI_ERROR;
                (void)abort_and_recover();
                return 0u;
            }
            if ((st & UCI_STAT_DATA) != 0u) {
                if (xfer != 0) ++xfer->data_seen;
                if (xfer != 0 && xfer->data != 0 &&
                    xfer->data_len < xfer->data_cap) {
                    xfer->data[xfer->data_len++] = readyfs_uci_asm_read_data();
                } else {
                    (void)readyfs_uci_asm_read_data();
                    if (xfer != 0) xfer->flags |= RF_UCI_TRUNC_DATA;
                }
                continue;
            }
            if ((st & UCI_STAT_STAT) != 0u) {
                if (xfer != 0) ++xfer->stat_seen;
                if (xfer != 0 && xfer->stat != 0 &&
                    xfer->stat_len < xfer->stat_cap) {
                    xfer->stat[xfer->stat_len++] = readyfs_uci_asm_read_stat();
                } else {
                    (void)readyfs_uci_asm_read_stat();
                    if (xfer != 0) xfer->flags |= RF_UCI_TRUNC_STAT;
                }
                continue;
            }
            break;
        }
        if (drain_tries == UCI_WAIT_RESPONSE) {
            if (xfer != 0) xfer->flags |= RF_UCI_TIMEOUT;
            (void)abort_and_recover();
            return 0u;
        }
        if (xfer != 0 && xfer->on_block != 0) {
            xfer->on_block(xfer->data, xfer->data_len,
                           xfer->stat, xfer->stat_len);
            ++xfer->block_count;
            /* Streaming consumers preserve block boundaries. The transport
             * still drains every later block even when the consumer stops
             * displaying or recording entries. */
            xfer->data_len = 0u;
            xfer->stat_len = 0u;
        }
        if (state == UCI_STATE_LAST) {
            readyfs_uci_asm_accept_data();
            if (!wait_idle()) {
                record_wait_failure(xfer);
                (void)abort_and_recover();
                return 0u;
            }
            return 1u;
        }
        /* DATA_ACC remains asynchronous. Observe the documented MORE -> BUSY
         * transition in a bounded tight helper so 64 MHz cannot skip over it
         * during C call/CPU-port mapping overhead. This does not accept an
         * unchanged MORE sample as a new block. */
        if (!readyfs_uci_asm_accept_more_transition(state) ||
            !wait_response_state()) {
            record_wait_failure(xfer);
            (void)abort_and_recover();
            return 0u;
        }
    }
}
