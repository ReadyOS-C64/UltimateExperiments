#ifndef READYFS_SCRIPT_H
#define READYFS_SCRIPT_H
#include "readyfs_batch.h"

#define RF_SCRIPT_ABI 0x5253u
#define RF_SCRIPT_VARS 16u
#define RF_SCRIPT_NAME 16u
#define RF_SCRIPT_VALUE 127u
#define RF_SCRIPT_RECORD_BYTES 146u
#define RF_SCRIPT_DEPTH 8u
#define RF_SCRIPT_STEPS 10000u

/* Dedicated fifth high REU bank; the tape spool stops below this bank. */
#define RF_SCRIPT_ENV_CACHE 0x0000u
#define RF_SCRIPT_EXPAND_CACHE 0x1000u
#define RF_SCRIPT_FLOW_CACHE 0x2000u
#define RF_SCRIPT_CONFIG_CACHE 0x3000u
#define RF_SCRIPT_VARS_OFF 0x4000u
#define RF_SCRIPT_STAGE_OFF 0x5000u
#define RF_SCRIPT_MERGE_OFF 0x6000u
#define RF_SCRIPT_ARGS_OFF 0x7000u
#define RF_SCRIPT_ARGS_BYTES 0x0A00u
#define RF_SCRIPT_TABLE_BYTES (RF_SCRIPT_VARS * RF_SCRIPT_RECORD_BYTES)

#define RF_ENV_INIT 20u
#define RF_ENV_COMMAND 21u
#define RF_ENV_EXPORT 22u
#define RF_ENV_STAGE 23u
#define RF_ENV_MERGE 24u
#define RF_ENV_COMMIT 25u
#define RF_ENV_EXPAND 26u
#define RF_ENV_ARGUMENTS 27u
#define RF_BATCH_READ 28u
#define RF_BATCH_EVAL 29u
#define RF_BATCH_FLOW 30u
#define RF_CONFIG_APPLY 32u
#define RF_CONFIG_ROLLBACK 33u
#define RF_CONFIG_LOAD 34u
#define RF_CONFIG_READ 35u
#define RF_CONFIG_EOF 36u
#define RF_CONFIG_CLOSE 37u
#define RF_CONFIG_EXPORT 38u
#define RF_CONFIG_HELP 39u
#define RF_BATCH_SKIP 2u
#define RF_BATCH_RAW 3u
#define RF_BATCH_EXISTS 4u
#define RF_BATCH_ERROR 5u
#define RF_BATCH_HELP 6u

/* Explicit byte record layout is identical on cc65 and host compilers. */
typedef struct {
    char name[RF_SCRIPT_NAME + 1u];
    char value[RF_SCRIPT_VALUE + 1u];
    unsigned char persistent;
} ReadyFsVariable;

typedef struct {
    unsigned char magic, policy, have_rc, last_rc, stopped, depth;
    unsigned int size, offset, lines, steps;
    unsigned int returns[RF_SCRIPT_DEPTH];
} ReadyFsBatchState;

unsigned int readyfs_environment_abi(void);
unsigned char readyfs_environment(ReadyFsBatchCall *call);
unsigned int readyfs_expand_abi(void);
unsigned char readyfs_expand(ReadyFsBatchCall *call);
unsigned char readyfs_config_io(ReadyFsBatchCall *call);
unsigned char readyfs_overlay_resume_config(void);
unsigned int readyfs_config_abi(void);
unsigned char readyfs_config(ReadyFsBatchCall *call);
unsigned int readyfs_flow_abi(void);
unsigned char readyfs_flow(ReadyFsBatchCall *call);
#ifdef __CC65__
unsigned char __fastcall__ readyfs_same_word(const char *left, const char *right);
#else
unsigned char readyfs_same_word(const char *left, const char *right);
#endif
#endif
