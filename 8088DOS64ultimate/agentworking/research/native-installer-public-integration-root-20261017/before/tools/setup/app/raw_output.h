#ifndef DOS64_RAW_OUTPUT_H
#define DOS64_RAW_OUTPUT_H
#include "bulk_reu.h"
#define RW_IDLE 0u
#define RW_BUSY 1u
#define RW_DONE 2u
#define RW_FAILED 3u
#define RW_INPUT 1u
#define RW_DMA 2u
#define RW_FILE 3u
#define RW_CRC 4u
#define RW_COMPARE 5u
#define RW_CANCEL 6u
#define RW_CLOCK 7u
#define RW_TIMEOUT 8u
#define RW_BUDGET 9u
struct rw_request_t {
 br_u8 owner;br_u32 capacity;br_u16 timeout;
 br_u32 source,bytes,crc;char root[128],path[128];
};
struct rw_result_t {
 br_u8 state,error,phase,rejected,leaf,transport,cleanup_required,reserved;
 br_u32 written,verified,crc;
};
extern struct rw_request_t rw_request;
extern struct rw_result_t rw_result; /* observations; private ledger controls */
extern const br_u16 rw_abi_sizes[2];
/* PUB_CODE/PUB_RO/PUBBSS only. Resident caller verifies publisher ticket BEFORE
 * dispatch, retains it for the whole job, and returns before phase replacement.
 * Begin independently checks private current publisher, capsule home/capacity,
 * actual SI_DONE and closed contexts. Borrowed NF sector must have no consumer.
 * Immutable source in200000..259FFF or3F8000..3FEFFF; readonly originals elsewhere.
 * Only fresh selected-home/A.IMG,DOS64.CFG,START.PRG. CREATE_NEW never replaces.
 * All filebytes/sourceCRC/poison/readback/EOF/finalknownCLOSE required for DONE.
 * Actual CIAclock and RunStop are serviced cooperatively; no fixed-delay pacing.
 * A failed clock drains at most256 further polls, then leaves cleanup uncertain.
 * Failure may leave a partial file/open handle for outer bounded cleanup. Never
 * reset the engine or reuse FAILED. This does not claim power-loss durability. */
/* PUB caller binds the actual private PB body identity before CFG begin.
 * Presence is separate, so body identity0 is valid. Only privateIDLE accepts;
 * rearm clears the binding. Mandatory for DOS64.CFG, forbidden for other leaves. */
br_u8 rw_expect_cfg(br_u32 identity);
br_u8 rw_begin(void);
void rw_poll(void),rw_cancel(void);
br_u8 rw_state(void),rw_closed_quiet(void),rw_rearm(void);
#endif
