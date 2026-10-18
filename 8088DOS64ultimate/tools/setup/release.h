#ifndef DOS64_START_RELEASE_H
#define DOS64_START_RELEASE_H
#define D64_RELEASE_BYTES 64u
extern unsigned char d64_release_input[64], d64_release_output[64];
extern unsigned char d64_release_error;
/* Checks descriptor CRC, ABI and address ranges; preserves committed output on
 * failure. Caller MUST independently verify staged whole PRG CRC and disabled
 * template bytes before using offsets or patching. No DMA or file operations. */
unsigned char d64_release_validate(void);
#endif
