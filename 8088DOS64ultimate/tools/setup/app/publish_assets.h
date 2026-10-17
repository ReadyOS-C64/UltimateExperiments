#ifndef DOS64_PUBLISH_ASSETS_H
#define DOS64_PUBLISH_ASSETS_H
#include "bulk_reu.h"
#define PB_SOURCE 0x2e0000UL
#define PB_START 0x3f8000UL
#define PB_CFG 0x3fd000UL
#define PB_DESCRIPTOR 0x3fec00UL
#define PB_A_BYTES 0u
#define PB_A_CRC 1u
#define PB_B_BYTES 2u
#define PB_B_CRC 3u
#define PB_C_BYTES 4u
#define PB_TEMPLATE_BYTES 5u
#define PB_INPUT 1u
#define PB_PHASE 2u
#define PB_FACT 3u
#define PB_DMA 4u
#define PB_CLOCK 5u
#define PB_CANCEL 6u
#define PB_TEMPLATE 7u
#define PB_CONFIG 8u
#define PB_CRC 9u
struct pb_result_t {br_u8 state,error,detail,reserved;br_u32 cfg_crc,start_crc,start_bytes;};
extern struct pb_result_t pb_result; /* observations only */
/* Mandatory integration callback. Return1 only for caller-private verified
 * receipts from THIS capsule generation/wholewireCRC; value may legitimately0
 * for CRC. A/B require complete360KiB write/close/reopen/fullCRC/EOF/finalCLOSE;
 * C requires equivalent proof and exact selectedprofile size. Template requires
 * actual INFO/exactcount/EOF/knownclosed source before staging at PB_SOURCE.
 * No host constant, descriptor self-length or mutable leaf-result authority.
 * Unit fixture models this contract; production resident ledger is separate. */
br_u8 pb_verified_fact(br_u8 kind,br_u16 generation,br_u32 wire_crc,br_u32 *value);
/* PUB-only code/RO/BSS. Caller verifies private PUBticket BEFORE invoking any
 * overlaid symbol; owns IRQ/D=0/bank35/stacks, immutable source+descriptor and
 * cooperative engine/REU/CRC workspace. Both contexts knownclosed, no active
 * rawwriter. One-shot per fresh zero-initialized PUB entry, no reset on failure.
 * Service actual clock/RunStop between256B transfers and at final fence. Never
 * accepts partial outputs. Return1 means native REU assets ready, NOT files
 * persisted/published. ROOT rawwriter must verify actual full external files.
 * No pointer/stack frame survives phase replacement. */
br_u8 pb_build(void),pb_state(void),pb_error(void),pb_ready(void);
/* Complete576B CFG CRC is fixed transport residue2144DF1C. Bind configuration
 * identity with pb_cfg_identity (CRC0..571/storedbodyCRC), never fullfileCRC alone.
 * Both may be legitimate0; require private pb_ready separately. */
br_u32 pb_cfg_identity(void),pb_cfg_crc(void),pb_start_crc(void),pb_start_bytes(void);
void pb_cancel(void);
#endif
