#ifndef READYFS_FILES_H
#define READYFS_FILES_H
#include "readyfs_stream.h"
#define RF_FILES_PLAN_ABI 0x4650u
#define RF_FILES_ABI 0x464Eu
#define RF_FILES_FIND 1u
#define RF_FILES_STATUS 2u
#define RF_FILES_SCRATCH 3u
#define RF_FILES_RENAME 4u
#define RF_FILES_OPEN_READ 5u
#define RF_FILES_OPEN_WRITE 6u
#define RF_FILES_CLOSE 7u
#define RF_FILES_MKDIR 8u
#define RF_FILES_RMDIR 9u
/* Policy-only operation returns CBM file type (always >=16), no I/O dispatch. */
#define RF_FILES_UDOS_TYPE 16u
#define RF_LOOKUP_MISSING 0u
#define RF_LOOKUP_FOUND 1u
#define RF_LOOKUP_ERROR 2u
/* Resident-owned arguments; synchronous leaf service, never nested overlays.
 * FIND only proves MISSING after the normal complete-directory terminator. */
typedef struct {
    ReadyFsStream *stream;
    ReadyFsStream *other;
    const char *directory;
    unsigned char *reply; /* at least80 bytes, retained by resident caller */
    char *request; /* separate120-byte resident command workspace */
    unsigned char *status;
    unsigned char operation;
    unsigned char dos;
} ReadyFsFilesCall;
unsigned int readyfs_files_abi(void);
unsigned int readyfs_files_plan_abi(void);
unsigned char readyfs_files(ReadyFsFilesCall *call);
unsigned char readyfs_files_plan(ReadyFsFilesCall *call);
unsigned char readyfs_files_prepare(ReadyFsStreamCall *call);
#endif
