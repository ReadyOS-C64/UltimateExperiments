#ifndef READYFS_RECURSIVE_H
#define READYFS_RECURSIVE_H

#include "readyfs_backend.h"

#define RF_RECURSIVE_ABI 0x5258u

#define RF_RECURSIVE_CALL_INIT  1u
#define RF_RECURSIVE_CALL_ADD   2u
#define RF_RECURSIVE_CALL_START 3u
#define RF_RECURSIVE_CALL_NEXT  4u
#define RF_RECURSIVE_CALL_ACK   5u
#define RF_RECURSIVE_CALL_IMPORT_TREE 6u

/* Returned in flags for NEXT/DONE. Reuse the existing ABI byte: enlarging a
 * resident/overlay call record needlessly makes cc65 layout more fragile. */
#define RF_RECURSIVE_STOPPED 0x80u

typedef struct {
    unsigned char operation;
    unsigned char mode;
    unsigned char stop_on_error;
    unsigned char kind;
    unsigned char flags;
    unsigned char succeeded;
    unsigned char action;
    const char *source_root;
    const char *destination_root;
    char *stem;
    unsigned int stem_capacity;
    char *source_text;
    unsigned int source_capacity;
    char *destination_text;
    unsigned int destination_capacity;
    unsigned int attempted;
    unsigned int completed;
    unsigned int failures;
} ReadyFsRecursiveCall;

unsigned int readyfs_recursive_abi(void);
unsigned char readyfs_recursive_dispatch(ReadyFsRecursiveCall *call);

#endif
