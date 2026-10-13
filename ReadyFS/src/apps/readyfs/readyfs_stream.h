#ifndef READYFS_STREAM_H
#define READYFS_STREAM_H
#include "readyfs_path.h"

#define RF_STREAM_ABI 0x5253u

/* Descriptors and canonical storage remain resident while cached policy swaps. */
typedef struct {
    ReadyFsPath path;
    char canonical[RF_PATH_MAX + 1u];
    const char *text;
    char *native_name;
    unsigned char device;
    unsigned char target;
    unsigned char lfn;
    unsigned char type;
    unsigned char open;
} ReadyFsStream;

typedef struct {
    ReadyFsStream *stream;
    unsigned char *status;
} ReadyFsStreamCall;

unsigned int readyfs_stream_abi(void);
unsigned char readyfs_stream_prepare(ReadyFsStreamCall *call);
#endif
