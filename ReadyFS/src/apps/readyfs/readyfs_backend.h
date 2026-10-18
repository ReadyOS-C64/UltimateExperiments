#ifndef READYFS_BACKEND_H
#define READYFS_BACKEND_H

#include "readyfs_exec.h"
#include "readyfs_path.h"

#define RF_BACKEND_ABI 0x5242u

#define RF_BACKEND_CALL_BUILD 1u
#define RF_BACKEND_CALL_SELFTEST 2u
#define RF_BACKEND_CALL_CAPABILITIES 3u
#define RF_BACKEND_CALL_BEGIN    4u
#define RF_BACKEND_CALL_COMPLETE 5u
#define RF_BACKEND_CALL_NATIVE_PLAN 6u

#define RF_PIPELINE_SCRATCH_BYTES 259u

#define RF_CAP_READ       0x0001u
#define RF_CAP_WRITE      0x0002u
#define RF_CAP_DELETE     0x0004u
#define RF_CAP_RENAME     0x0008u
#define RF_CAP_MKDIR      0x0010u
#define RF_CAP_RECURSE    0x0020u
#define RF_CAP_IMAGES     0x0040u
#define RF_CAP_MOUNT      0x0080u
#define RF_CAP_FREE       0x0100u
#define RF_CAP_SEQUENTIAL 0x0200u

#define RF_SIZE_NONE   0u
#define RF_SIZE_BLOCKS 1u
#define RF_SIZE_BYTES  2u

typedef struct {
    unsigned int flags;
    unsigned int path_limit;
    unsigned int leaf_limit;
    unsigned char endpoint;
    unsigned char unit;
    unsigned char partition;
    unsigned char size_units;
    unsigned char provisional;
} ReadyFsBackendCapabilities;

typedef struct {
    unsigned char action;
    ReadyFsPath source;
    ReadyFsPath destination;
    unsigned char has_source;
    unsigned char has_destination;
    unsigned char force;
    char *source_text;
    unsigned int source_capacity;
    char *destination_text;
    unsigned int destination_capacity;
} ReadyFsBackendRequest;

typedef struct {
    unsigned char operation;
    unsigned char action;
    unsigned char force;
    const char *source_root;
    const char *destination_root;
    const char *stem;
    ReadyFsBackendRequest *request;
    ReadyFsBackendCapabilities *capabilities;
    ReadyFsActionState *state;
} ReadyFsBackendCall;

unsigned int readyfs_backend_abi(void);
unsigned char readyfs_backend_selftest(void);
unsigned char readyfs_backend_build(ReadyFsBackendCall *call);
unsigned char readyfs_backend_capabilities(
    const char *path, ReadyFsBackendCapabilities *capabilities);
unsigned char readyfs_backend_dispatch(ReadyFsBackendCall *call);

#endif
