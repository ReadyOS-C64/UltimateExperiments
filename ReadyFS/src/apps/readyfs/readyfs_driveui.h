#ifndef READYFS_DRIVEUI_H
#define READYFS_DRIVEUI_H

#include "readyfs_cmdpath.h"
#include "readyfs_backend.h"

#define RF_DRIVEUI_ABI 0x4452u

#define RF_DRIVEUI_BEGIN    1u
#define RF_DRIVEUI_COMPLETE 2u
#define RF_DRIVEUI_QUERY    3u
#define RF_DRIVEUI_COMMAND_BEGIN    5u
#define RF_DRIVEUI_COMMAND_COMPLETE 6u

typedef struct {
    unsigned char operation;
    void *call;
} ReadyFsDriveNestedCall;

typedef struct {
    unsigned char operation;
    unsigned char argc;
    unsigned char pending;
    unsigned char device;
    unsigned char io_ok;
    unsigned char kind;
    unsigned char flags;
    unsigned char native_operation;
    unsigned char force;
    unsigned char handled;
    char **args;
    char *status;
    const char *source;
    const char *destination;
    char *output;
    unsigned int output_capacity;
    char *followup;
    unsigned int followup_capacity;
    ReadyFsCmdPathCall path;
    ReadyFsBackendCall *backend;
    ReadyFsActionState *state;
    ReadyFsDriveNestedCall nested;
} ReadyFsDriveUiCall;

unsigned int readyfs_driveui_abi(void);
unsigned char readyfs_driveui_reset(void);
unsigned char readyfs_driveui_dispatch(ReadyFsDriveUiCall *call);

#endif
