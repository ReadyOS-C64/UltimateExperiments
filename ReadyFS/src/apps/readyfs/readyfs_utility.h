#ifndef READYFS_UTILITY_H
#define READYFS_UTILITY_H

#include "readyfs_commands.h"

#define RF_UTILITY_ABI 0x5255u
#define RF_UTILITY_PREVIEW 1u
#define RF_UTILITY_HISTORY 2u
#define RF_UTILITY_PRINT_U32 3u
#define RF_UTILITY_PRINT_U16 4u
#define RF_UTILITY_FORMAT_U16 5u
#define RF_UTILITY_DRIVES 6u
#define RF_UTILITY_SOFT_CD 7u
#define RF_UTILITY_CAPABILITIES 8u
#define RF_UTILITY_CONTENT_INIT 9u
#define RF_UTILITY_CONTENT_ADD 10u
#define RF_UTILITY_CONTENT_REPORT 11u
#define RF_UTILITY_FORMAT_MEDIA 12u
#define RF_CONTENT_TYPE 0u
#define RF_CONTENT_HEAD 1u
#define RF_CONTENT_TAIL 2u
#define RF_CONTENT_CRC32 3u
#define RF_CONTENT_TEST 4u

typedef struct {
    unsigned char operation;
    unsigned char argc;
    char **args;
    char *buffer;
    unsigned int capacity;
    unsigned int value_high;
    unsigned int value_low; /* RF_UTILITY_PREVIEW: decoded RF_COMMAND_* ID. */
    char *workspace;
} ReadyFsUtilityCall;

unsigned int readyfs_utility_abi(void);
unsigned char readyfs_utility_dispatch(ReadyFsUtilityCall *call);

#endif
