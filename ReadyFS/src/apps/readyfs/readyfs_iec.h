#ifndef READYFS_IEC_H
#define READYFS_IEC_H

#define RF_IEC_PLAN_ABI 0x4950u
#define RF_IEC_ABI 0x4943u
#define RF_IEC_COMMAND_CAP 120u
#define RF_IEC_TEXT 0u
#define RF_IEC_PARTITION 1u
#define RF_IEC_ADDRESS 2u
#define RF_IEC_RESTART 3u
#define RF_IEC_PARTITIONS 4u
#define RF_IEC_SD_ONLY 0x01u
#define RF_IEC_INVALIDATE 0x02u
#define RF_IEC_SAVE 0x04u
#define RF_IEC_RAW 0x08u

/* All storage is owned by the resident caller, including binary command bytes.
 * The policy and I/O overlays are entered sequentially, never nested. */
typedef struct {
    char **args;
    unsigned char argc;
    unsigned char device;
    unsigned char operation;
    unsigned char flags;
    unsigned char expected;
    unsigned char length;
    unsigned char new_device;
    unsigned char *command;
    unsigned char *reply;
    unsigned char *status;
} ReadyFsIecCall;

unsigned int readyfs_iec_plan_abi(void);
unsigned char readyfs_iec_plan(ReadyFsIecCall *call);
unsigned int readyfs_iec_abi(void);
unsigned char readyfs_iec_execute(ReadyFsIecCall *call);

#endif
