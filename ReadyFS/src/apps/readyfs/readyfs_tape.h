#ifndef READYFS_TAPE_H
#define READYFS_TAPE_H

#include "readyfs_path.h"

#define RF_TAPE_ABI 0x5254u

#define RF_TAPE_SIGNATURE_INIT  1u
#define RF_TAPE_SIGNATURE_ADD   2u
#define RF_TAPE_SIGNATURE_EQUAL 3u
#define RF_TAPE_OPTION_PRESENT  4u
#define RF_TAPE_OPTION_VALUE    5u
#define RF_TAPE_OPEN_NAME       6u
#define RF_TAPE_PATH_PREPARE    7u
#define RF_TAPE_FILE_TYPE       8u
#define RF_TAPE_SAME_WORD       9u
#define RF_TAPE_SPOOL_INIT     10u
#define RF_TAPE_SPOOL_STORE    11u
#define RF_TAPE_SPOOL_FETCH    12u
#define RF_TAPE_SPLIT_ARGS     13u
#define RF_TAPE_DESIGNATOR     14u

#define RF_TAPE_PATH_OK          0u
#define RF_TAPE_PATH_UNSUPPORTED 1u
#define RF_TAPE_PATH_REQUIRED    2u
#define RF_TAPE_PATH_CMD         3u
#define RF_TAPE_PATH_IMAGE       4u
#define RF_TAPE_PATH_LEAF        5u

typedef struct {
    unsigned int bytes_lo;
    unsigned int bytes_hi;
    unsigned int crc;
} ReadyFsSignature;

typedef struct {
    unsigned int bytes_lo;
    unsigned char bytes_bank;
    unsigned int replay_lo;
    unsigned char replay_bank;
} ReadyFsTapeSpoolState;

typedef struct {
    unsigned char operation;
    ReadyFsSignature *signature;
    const ReadyFsSignature *other;
    const unsigned char *data;
    unsigned int length;
    ReadyFsTapeSpoolState *spool;
    unsigned char result;
    unsigned char argc;
    char **args;
    const char *text;
    const char *text2;
    char *output;
    const char *found;
    ReadyFsPath *path;
    unsigned char value;
    unsigned char value2;
} ReadyFsTapeCall;

unsigned int readyfs_tape_abi(void);
unsigned char readyfs_tape_dispatch(ReadyFsTapeCall *call);

#endif
