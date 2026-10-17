#ifndef DOS64_COORDINATOR_CAPTURE_H
#define DOS64_COORDINATOR_CAPTURE_H
#include "bulk_reu.h"
/* UI-only, once, with private SU_DONE and the still-active UI ticket. Copies
 * facts before UI retirement. No output durability is inferred from a source. */
extern br_u16 rc_expected_ticket;
extern const char * const rc_home;
extern br_u16 rc_generation;
extern br_u32 rc_identity;
extern br_u8 rc_flags,rc_source_mask;
br_u8 rc_capture(void);
/* HIGH, safe after UI retirement. Observations never authorize a phase. */
br_u8 rc_source_ready(void);
#endif
