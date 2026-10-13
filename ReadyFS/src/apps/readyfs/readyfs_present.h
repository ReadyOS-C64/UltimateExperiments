#ifndef READYFS_PRESENT_H
#define READYFS_PRESENT_H
#include "readyfs_utility.h"
#define RF_PRESENT_ABI 0x5250u
#define RF_COMMAND_HELP_ABI 0x5245u
#define RF_COMMAND_HELP_CACHE_OFF 0x8A00u
#define RF_PRESENT_HELP 0u
#define RF_PRESENT_DIR 1u
#define RF_PRESENT_HOST 2u
#define RF_PRESENT_FREE 3u
#define RF_PRESENT_CD 4u
#define RF_PRESENT_STAGE_NAME 5u
#define RF_PRESENT_UCI_ERROR 6u
#define RF_PRESENT_DATA_TEXT 7u
#define RF_PRESENT_MEDIA 8u
#define RF_PRESENT_COPY 9u
#define RF_PRESENT_PLAN 10u
#define RF_PRESENT_BATCH 11u
#define RF_PRESENT_STAT 12u
#define RF_PRESENT_BATCH_FAILURE 13u
unsigned char readyfs_transfer_plan(ReadyFsUtilityCall *call);
unsigned char readyfs_transfer_present(ReadyFsUtilityCall *call);
#define RF_MEDIA_SHOW 0u
#define RF_MEDIA_REMEMBER 1u
#define RF_MEDIA_FORGET 2u
#define RF_MEDIA_DRIVES 3u
void readyfs_media_reset(void);
unsigned char readyfs_media(ReadyFsUtilityCall *call);
#define RF_PRESENT_CACHE_OFF 0x7A00u
typedef struct { char name[17]; unsigned int size; unsigned char type; unsigned char access; } ReadyFsDirectoryEntry;
unsigned int readyfs_present_abi(void);
unsigned int readyfs_command_help_abi(void);
void readyfs_command_help(ReadyFsUtilityCall *call);
unsigned char readyfs_present(ReadyFsUtilityCall *call);
#endif
