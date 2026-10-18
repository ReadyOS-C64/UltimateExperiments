#ifndef DOS64_SETUP_UI_RUN_H
#define DOS64_SETUP_UI_RUN_H
#include "bulk_reu.h"
#define SU_IDLE 0u
#define SU_BUSY 1u
#define SU_DONE 2u
#define SU_FAILED 3u
#define SU_INPUT 1u
#define SU_SELECT 0x10u
#define SU_CAPSULE 0x20u
#define SU_SOURCE 0x30u
/* UI CODE/RO/UIBSS only. Caller holds authentic current UI ticket throughout,
 * initialized HIGH bootstrap/platform/startup-close, sole cooperative engine.
 * Captures source-IO owner/capacity from private UI session; never clears faults.
 * Begin once per fresh UI residency; timeout1..7fff captured before selection.
 * DONE requires private SS_DONE, checked capsule and five private source jobs.
 * Error retains first native module cause; high nibble identifies module.
 * Source failure attempts one bounded same-engine source0 CLOSE, never reset.
 * FAILED may remain uncertain: check su_closed_quiet before navigation/reload.
 * No overlaid caller frame or pointer may survive phase replacement. */
extern br_u16 su_timeout;
br_u8 su_begin(void);
void su_poll(void);
br_u8 su_state(void),su_error(void),su_closed_quiet(void);
#endif
