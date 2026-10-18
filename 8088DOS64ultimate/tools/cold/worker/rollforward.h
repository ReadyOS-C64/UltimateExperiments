#ifndef DOS64_COLD_ROLLFORWARD_H
#define DOS64_COLD_ROLLFORWARD_H
#include "bulk_reu.h"
#define RF_COMPLETE_SAVED_UPDATE 1u
/* Fresh loaded/zeroed private phase, only after actual JG pending DONE.
 * Same resident transport, bank35, D0, shared cc65 stack CD00..CFFF.
 * One explicit typed action; Cancel never grants boot. Observations only.
 * begin0 does not acquire/drain another active owner. FAILED+cleanup0 means
 * owned transport is quiet, not that startup/resume is permitted. Root must
 * retire all worker frames, reinstall/verify RCV and run its NONE path anew. */
extern br_u8 rf_state_observed,rf_error_observed,rf_cleanup_observed;
br_u8 __fastcall__ rf_begin(br_u8 action);
void rf_poll(void),rf_cancel(void),rf_clock_fail(void);
br_u8 rf_state(void),rf_error(void),rf_cleanup(void);
#endif
