#ifndef READYFS_CONTENT_H
#define READYFS_CONTENT_H

#include "readyfs_utility.h"

#define RF_CONTENT_ABI 0x5243u

unsigned int readyfs_content_abi(void);
unsigned char readyfs_content_dispatch(ReadyFsUtilityCall *call);
unsigned char readyfs_content_format(void *call);
unsigned char readyfs_content_parse_count(const char *text,
                                          unsigned char *value);
unsigned char readyfs_utility_test(void *call);

#endif
