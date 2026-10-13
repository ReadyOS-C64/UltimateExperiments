#ifndef READYFS_DRIVER_H
#define READYFS_DRIVER_H

#define RF_DRIVER_ABI 0x5244u

#define RF_DRIVER_UNKNOWN  0u
#define RF_DRIVER_LEGACY   1u
#define RF_DRIVER_SD2IEC   2u
#define RF_DRIVER_CMD      3u
#define RF_DRIVER_PI1541   4u
#define RF_DRIVER_ULTIMATE 5u
#define RF_DRIVER_SOFTIEC  6u

#define RF_DRIVER_PARTITIONS 0x01u
#define RF_DRIVER_FOLDERS    0x02u
#define RF_DRIVER_IMAGES     0x04u

typedef struct {
    const char *status;
    unsigned char kind;
    unsigned char flags;
} ReadyFsDriverCall;

unsigned int readyfs_driver_abi(void);
unsigned char readyfs_driver_classify(ReadyFsDriverCall *call);
unsigned char readyfs_driver_allows_operation(unsigned char flags,
                                              unsigned char operation);
#ifndef __CC65__
const char *readyfs_driver_name(unsigned char kind);
#endif

#endif
