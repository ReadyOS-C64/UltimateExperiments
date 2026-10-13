#ifndef READYFS_HELP_H
#define READYFS_HELP_H

#define RF_HELP_ABI 0x4846u

#include "readyfs_cmdpath.h"

typedef struct {
    unsigned char operation;
    void *call;
} ReadyFsHelpNestedCall;

typedef struct {
    unsigned char argc;
    char **args;
    char *output;
    char *followup;
    ReadyFsCmdPathCall path;
    ReadyFsHelpNestedCall nested;
} ReadyFsNativeUiCall;

unsigned int readyfs_help_abi(void);
void readyfs_help_show(void);
unsigned char readyfs_help_native(ReadyFsNativeUiCall *call);

#endif
