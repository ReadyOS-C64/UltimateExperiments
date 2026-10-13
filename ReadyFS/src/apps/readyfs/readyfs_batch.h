#ifndef READYFS_BATCH_H
#define READYFS_BATCH_H

#define RF_BATCH_ABI 0x5242u

#define RF_BATCH_INIT   1u
#define RF_BATCH_NEXT   2u
#define RF_BATCH_ACK    3u
#define RF_BATCH_REPORT 4u
#define RF_BATCH_EDITOR 5u
#define RF_BATCH_ALIAS 6u

#define RF_BATCH_DONE    0u
#define RF_BATCH_COMMAND 1u

typedef struct {
    unsigned char operation;
    unsigned char action;
    unsigned char argc;
    unsigned char rc;
    unsigned char finish;
    unsigned char reu_available;
    char **args;
    char *buffer;
    unsigned int capacity;
    unsigned int size;
    unsigned char *scroll_head;
    unsigned char *scroll_used;
} ReadyFsBatchCall;

unsigned int readyfs_batch_abi(void);
unsigned char readyfs_batch_dispatch(ReadyFsBatchCall *call);

#endif
