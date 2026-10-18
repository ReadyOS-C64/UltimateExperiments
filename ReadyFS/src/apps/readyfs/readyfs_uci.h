#ifndef READYFS_UCI_H
#define READYFS_UCI_H

#define RF_UCI_ID_MASK  0x7Fu
#define RF_UCI_ID_MATCH 0x49u

#define RF_UCI_TRUNC_DATA 0x01u
#define RF_UCI_TRUNC_STAT 0x02u
#define RF_UCI_TIMEOUT    0x04u
#define RF_UCI_ERROR      0x08u

typedef void (*ReadyFsUciBlockHandler)(const unsigned char *data,
                                       unsigned int data_len,
                                       const unsigned char *stat,
                                       unsigned int stat_len);

typedef struct {
    unsigned char *data;
    unsigned int data_cap;
    unsigned int data_len;
    unsigned char *stat;
    unsigned int stat_cap;
    unsigned int stat_len;
    unsigned int data_seen;
    unsigned int stat_seen;
    unsigned int block_count;
    ReadyFsUciBlockHandler on_block;
    unsigned char flags;
    unsigned char last_status;
} ReadyFsUciTransfer;

unsigned char readyfs_uci_detect(void);
unsigned int readyfs_uci_base(void);
unsigned char readyfs_uci_id(void);
unsigned char readyfs_uci_softiec_bus(void);
unsigned char readyfs_uci_recovery_probe(void);
unsigned char readyfs_uci_command(const unsigned char *cmd,
                                  unsigned int cmd_len,
                                  ReadyFsUciTransfer *xfer);

/* This is ReadyFS's sole UCI transaction gateway. It owns quiet-idle sync,
 * asynchronous PUSH/ABORT handling, complete data and status queue draining,
 * DATA_ACC transitions, and the final quiet-idle wait. Callers must not add
 * timing delays or interpret target status as transport state. */

/* Read-only hardware diagnostic: begin an UltimateDOS IDENTIFY transaction,
 * wait until asynchronous PUSH has visibly left quiet idle, request ABORT at
 * most once, then service the same bounded recovery path to quiet idle. */

void __fastcall__ readyfs_uci_asm_set_base(unsigned int base);
unsigned char __fastcall__ readyfs_uci_asm_write_cmd(unsigned char value);
unsigned char readyfs_uci_asm_id(void);
unsigned char readyfs_uci_asm_status(void);
unsigned char readyfs_uci_asm_read_data(void);
unsigned char readyfs_uci_asm_read_stat(void);
void readyfs_uci_asm_push_cmd(void);
void readyfs_uci_asm_accept_data(void);
unsigned char __fastcall__ readyfs_uci_asm_accept_more_transition(
    unsigned char old_state);
void readyfs_uci_asm_abort(void);
void readyfs_uci_asm_clear_error(void);
unsigned char readyfs_uci_asm_softiec_bus(void);

#endif
