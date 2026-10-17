#ifndef DOS64_COORDINATOR_INTERNAL_H
#define DOS64_COORDINATOR_INTERNAL_H
#include "bulk_reu.h"
/* INTERNAL friend record: trusted root/FAT/PUB code only, not request/input or
 * observation authority. Capture writes source facts; worker writes C/B only
 * after privateSI_DONE refresh+exactcounts+NFconsumed. PUB writes A afterRAWdone.
 * Maskbits C1,B2,A4. Outputs are size,CRC pairs C/B/A. Exact183B cc65 layout. */
struct rc_record_t {char home[128];br_u16 generation;br_u32 identity,source_crc[5],output[6];br_u8 flags,source_mask,output_mask,valid,started;};
#define RC_C_PAIR 0u
#define RC_B_PAIR 2u
#define RC_A_PAIR 4u
#define RC_C_MASK 1u
#define RC_B_MASK 2u
#define RC_A_MASK 4u
#define RC_START_MASK 8u
#define RC_CFG_MASK 16u
#pragma bss-name(push,"HIGHBSS")
extern struct rc_record_t rc_retained;
#pragma bss-name(pop)
/* Entire worker call runs under authentic FAT ticket. This friend receipt is
 * retained in nonoverlaid BSS. No injected inputs; no navigation on failure. */
struct fw_internal_t {br_u8 state,error,leaf,cleanup,flags,derived_a;br_u16 ticket;br_u8 guard[3],text,slash,source_opened;};
#pragma bss-name(push,"BSS")
extern struct fw_internal_t fw_internal;
#pragma bss-name(pop)
br_u8 fw_run(void); /*1 C/B verified+derivedA ready,0failed; no publication*/
#endif
