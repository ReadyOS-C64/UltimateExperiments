#ifndef READYFS_UDOS_FILES_H
#define READYFS_UDOS_FILES_H
#include "readyfs_stream.h"
#include "readyfs_files.h"
#define RF_UDOS_PREPARE_ABI 0x5550u
#define RF_UDOS_LOOKUP_ABI 0x554Cu
#define RF_UDOS_EXECUTE_ABI 0x5545u
#define RF_UDOS_NAME_ABI 0x554Eu
#define RF_UDOS_NAME_INPUT 1u
#define RF_UDOS_NAME_OUTPUT 2u
#define RF_UDOS_NAME_NEW 3u
#define RF_UDOS_NAME_RENAME 4u
#define RF_UDOS_NAME_DISTINCT 5u
#define RF_UDOS_PARENT 1u
#define RF_UDOS_FIND 2u
#define RF_UDOS_READ 3u
#define RF_UDOS_NEW 4u
#define RF_UDOS_CLOSE 5u
#define RF_UDOS_RENAME 6u
#define RF_UDOS_VALIDATE 7u
#define RF_UDOS_CHANGE 8u
#define RF_UDOS_DISTINCT 9u
#define RF_UDOS_HOST_LOOKUP 3u
#define RF_UDOS_CBM 0x80u
/* Cold synchronous leaf: no nested overlay calls and no returned overlay
 * pointers. open_targets is resident state: an uncertain CLOSE keeps its bit
 * set, preventing a metadata probe from replacing a live file handle. */
typedef struct {
    ReadyFsStream *stream;
    ReadyFsStream *other;
    const char *path;
    const char *source_access;
    char *access; /* resident, at least 80 bytes */
    char *name; /* resident 17-byte decoded CBM name */
    char *wire; /* resident 40-byte typed wire name */
    unsigned char selector;
    unsigned char policy;
    unsigned char *status;
    unsigned char *open_targets;
    unsigned char operation;
    unsigned char target;
    unsigned char type;
} ReadyFsUdosFilesCall;
unsigned int readyfs_udos_prepare_abi(void);
unsigned int readyfs_udos_lookup_abi(void);
unsigned int readyfs_udos_execute_abi(void);
unsigned int readyfs_udos_name_abi(void);
unsigned char readyfs_udos_prepare(ReadyFsUdosFilesCall *call);
unsigned char readyfs_udos_lookup(ReadyFsUdosFilesCall *call);
unsigned char readyfs_udos_execute(ReadyFsUdosFilesCall *call);
unsigned char readyfs_udos_name(ReadyFsUdosFilesCall *call);
#endif
