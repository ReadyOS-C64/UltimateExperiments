#ifndef DOS64_NATIVE_CRC32_H
#define DOS64_NATIVE_CRC32_H
extern unsigned long c32_crc;
extern unsigned int c32_address,c32_length;
extern unsigned char c32_error;
/* Caller owns RAM/I/O, native stacks and exclusive metadata/source/table access.
 * Tables require page-aligned1KiB writableRAM disjoint from softwarestack.
 * A/X/Y clobbered. Native P except N/Z preserved. Return1 success/0 failure. */
unsigned char c32_init(void); /* Generates tables; initial CRC=FFFFFFFF. */
unsigned char c32_reset(void);
/* Feed0..32768 sourcebytes at0200..CFFF, end<=D000. Address/count preserved.
 * Reject overlap with mutable metadata atomically. Zero count after init is
 * a no-op. Error1 uninitialized,2 range/overlap. Caller keeps source immutable. */
unsigned char c32_update(void);
/* Final XOR, exactlyonce after all updates; reset for a new checksum. */
unsigned char c32_finish(void);
#endif
