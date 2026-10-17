#ifndef DOS64_SETUP_SOURCE_LOAD_H
#define DOS64_SETUP_SOURCE_LOAD_H
#include "bulk_reu.h"
#define SL_IDLE 0u
#define SL_BUSY 1u
#define SL_DONE 2u
#define SL_FAILED 3u
#define SL_INPUT 1u
#define SL_FILE 2u
#define SL_DMA 3u
#define SL_COMPARE 4u
#define SL_CANCEL 5u
#define SL_CLOCK 6u
#define SL_TIMEOUT 7u
#define SL_RELEASE 8u
/* UI-only begin/poll/cancel, caller holds current UI ticket for entire job.
 * kinds0..2 are private selected DOS paths,3 START.TPL,4 START.REL in home.
 * Exactly360K,360K,360K,18432,64 bytes; sources readonly. No NF producer runs.
 * Only complete twice-read, byte-compared, EOF/known-CLOSE grants receipt.
 * Failed/uncertain jobs cannot rearm. FILES cleanup stays explicit to caller.
 * Immutable filesystem/source REU until consumer done; receipts not locks. */
extern br_u8 sl_kind;
extern br_u16 sl_timeout;
struct sl_observation_t {br_u8 state,error,phase,leaf,transport,cleanup;};
extern struct sl_observation_t sl_result;
/* Bootstrap once with35 banking BEFORE so_prepare captures initial UI. Copies
 * serialized HIGH_CODE, verifies every byte, then permits resident getters.
 * No call to HIGH_CODE before success, no loader frame across replacement. */
br_u8 sl_install(void);
br_u8 sl_begin(void);
void sl_poll(void),sl_cancel(void);
/* HIGH_CODE resident facts remain available after retiring UI. Inputs/output
 * are observations; private ledger controls admission and retained identities. */
br_u8 sl_state(void),sl_error(void);
struct sl_receipt_t {br_u16 generation;br_u32 identity,bytes,crc;};
extern br_u16 sl_generation;
extern br_u32 sl_identity;
extern struct sl_receipt_t sl_receipt;
br_u8 sl_fact(void);
#endif
