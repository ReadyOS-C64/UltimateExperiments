#ifndef READYFS_NATIVEPLAN_H
#define READYFS_NATIVEPLAN_H

#include "readyfs_cmdpath.h"
#include "readyfs_match.h"
#include "readyfs_recursive.h"

#define RF_NATIVEPLAN_ABI 0x4E50u
#define RF_NATIVEPLAN_PREPARE 1u
#define RF_NATIVEPLAN_ADD     2u
#define RF_NATIVEPLAN_REPORT  3u
#define RF_NATIVE_TYPE_FIRST  0x10u
#define RF_NATIVE_TYPE_COUNT  3u

typedef struct {
    unsigned char operation;
    unsigned char phase;
    unsigned char device;
    unsigned char flags;
    unsigned char file_type;
    unsigned char argc;
    unsigned char display;
    unsigned char mode;
    unsigned char dry_run;
    char **args;
    ReadyFsPath *source_path;
    char *source;
    char *pattern;
    char *stem;
    ReadyFsRecursiveCall *recursive;
    unsigned int entries;
    unsigned int selected;
    ReadyFsCmdPathCall path;
    ReadyFsMatchCall match;
    struct {
        unsigned char operation;
        void *call;
    } nested;
} ReadyFsNativePlanCall;

unsigned char readyfs_backend_native_plan(ReadyFsNativePlanCall *call);

#endif
