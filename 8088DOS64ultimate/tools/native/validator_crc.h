#ifndef DOS64_VALIDATOR_CRC_H
#define DOS64_VALIDATOR_CRC_H
#include "crc32.h"
/* Target-only optional validator adapter; default CFG/release code is unchanged.
 * Exclusive mapped RAM/table/metadata ownership; not callable inside another
 * update. Init/reset changes shared scratch; streaming caller restores its own
 * private rawCRC on each update. c32_error distinguishes legitimate CRC0. */
unsigned long d64_fast_crc(const unsigned char *p,unsigned int n);
#endif
