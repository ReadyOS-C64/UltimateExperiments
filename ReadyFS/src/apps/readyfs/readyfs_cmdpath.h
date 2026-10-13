#ifndef READYFS_CMDPATH_H
#define READYFS_CMDPATH_H

#define RF_CMDPATH_ABI 0x5244u

#define RF_CMDPATH_OPEN_FILE  1u
#define RF_CMDPATH_DIRECTORY  2u
#define RF_CMDPATH_SCRATCH    3u
#define RF_CMDPATH_MKDIR      4u
#define RF_CMDPATH_RMDIR      5u
#define RF_CMDPATH_RENAME     6u
#define RF_CMDPATH_MOUNT      7u
#define RF_CMDPATH_UNMOUNT    8u
#define RF_CMDPATH_NATIVE_DIR 9u
#define RF_CMDPATH_FORMAT    10u

#define RF_CMDPATH_OK                 0u
#define RF_CMDPATH_BAD_PATH           1u
#define RF_CMDPATH_UNSUPPORTED        2u
#define RF_CMDPATH_COMPONENT_TOO_LONG 3u
#define RF_CMDPATH_NATIVE_TOO_LONG    4u
#define RF_CMDPATH_OUTPUT_TOO_SMALL   5u
#define RF_CMDPATH_CROSS_LOCATION     6u
#define RF_CMDPATH_IMAGE_REQUIRED     7u
#define RF_CMDPATH_IMAGE_STATEFUL     8u
#define RF_CMDPATH_PATTERN_REQUIRED   9u

#define RF_CMDPATH_COMPONENT_MAX 16u
#define RF_CMDPATH_DIRECTORY_MAX 234u
#define RF_CMDPATH_SD2IEC_BACK 0x5Fu

typedef struct {
    unsigned char operation;
    unsigned char result;
    unsigned char device;
    unsigned char partition;
    unsigned char image_depth;
    const char *source;
    const char *destination;
    char *output;
    unsigned int output_capacity;
    char *followup;
    unsigned int followup_capacity;
} ReadyFsCmdPathCall;

unsigned int readyfs_cmdpath_abi(void);
unsigned char readyfs_cmdpath_selftest(void);
unsigned char readyfs_cmdpath_dispatch(ReadyFsCmdPathCall *call);
#ifndef __CC65__
const char *readyfs_cmdpath_error(unsigned char result);
#endif

#endif
